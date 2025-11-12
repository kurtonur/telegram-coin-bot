import asyncio
import requests
import pandas as pd
import pandas_ta as ta
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta
import logging
import os
from dotenv import load_dotenv
from lib.sms.sms import send_message

# .env dosyasını yükle
load_dotenv()

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Takip listesi (sizin belirttiğiniz coinler)
COINS = ["BTCUSDT", "ETHUSDT", "DOGEUSDT", "SOLUSDT", "WIFUSDT",
         "PEPEUSDT", "SHIBUSDT", "AVAXUSDT", "SUIUSDT", "LTCUSDT", "XRPUSDT"]

# Zamanlama ve TP/SL ayarları
PERIOD_SECONDS = 15 * 60  # 15 dakika
TP_PERCENT = 1.0  # %1.0
SL_PERCENT = 0.6  # %0.6
VOLUME_WINDOW = 10  # hacim ortalaması için mum sayısı
VOLUME_THRESHOLD_PCT = 15  # %15 üzerinde olmalı
ADX_MIN = 20  # ADX eşik
MIN_DATA_LEN = 60  # gerekli minimum mum sayısı (EMA200 için >200 ideal ama 60 ile çalışıyoruz)

# Spam önleme: aynı coin için en az bu kadar süre bekle (dakika)
MIN_RESEND_MINUTES = 30

# --------------------------
# Yardımcı fonksiyonlar
# --------------------------
def get_candles(symbol="BTCUSDT", limit=300):
    """
    Bitget spot 15m mumları çek (limit up to maybe 300)
    """
    logging.info(f"📊 {symbol} için veri çekiliyor...")
    url = f"https://api.bitget.com/api/v2/spot/market/candles?symbol={symbol}&granularity=15min&limit={limit}"
    try:
        resp = requests.get(url, timeout=15)
        data = resp.json()
        if "data" in data and isinstance(data["data"], list) and len(data["data"]) > 0:
            # Data format may be list of lists (timestamp,open,high,low,close,volume,...)
            # Ensure we convert correctly.
            df = pd.DataFrame(data["data"])
            # If API returns more than 6 columns, take first 6 expected columns
            # Normalize to: timestamp, open, high, low, close, volume
            if df.shape[1] >= 6:
                df = df.iloc[:, :6]
                df.columns = ["timestamp", "open", "high", "low", "close", "volume"]
            else:
                return None

            # convert types reliably
            df = df.dropna()
            df["open"] = pd.to_numeric(df["open"], errors="coerce")
            df["high"] = pd.to_numeric(df["high"], errors="coerce")
            df["low"] = pd.to_numeric(df["low"], errors="coerce")
            df["close"] = pd.to_numeric(df["close"], errors="coerce")
            df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

            # timestamps from API might be in ms or seconds or strings — try to coerce
            try:
                df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="ms")
            except Exception:
                try:
                    df["timestamp"] = pd.to_datetime(pd.to_numeric(df["timestamp"]), unit="s")
                except Exception:
                    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")

            df.set_index("timestamp", inplace=True)
            df = df.sort_index()
            logging.info(f"✅ {symbol} için {len(df)} mum verisi başarıyla çekildi")
            return df
        else:
            logging.warning(f"⚠️ {symbol} için veri bulunamadı")
            return None
    except Exception as e:
        logging.error(f"❌ {symbol} veri çekmede hata: {e}")
        return None

def safe_ta_macd(close_series):
    """MACD dönen DataFrame kontrolü"""
    try:
        macd = ta.macd(close_series)
        # Beklenen kolonlar: MACD_12_26_9, MACDh_12_26_9, MACDs_12_26_9
        if macd is None or macd.shape[1] < 3:
            return None
        return macd
    except Exception:
        return None

def safe_ta_adx(high, low, close):
    try:
        adx = ta.adx(high, low, close)
        if adx is None or "ADX_14" not in adx.columns:
            return None
        return adx
    except Exception:
        return None

def calculate_signal(df):
    """
    Tüm filtreleri uygular. Eğer güçlü LONG veya SHORT varsa (tüm koşullar sağlanır)
    döndürür: ("LONG" veya "SHORT", detay_dict)
    Aksi halde None döner.
    """
    if df is None or len(df) < MIN_DATA_LEN:
        logging.debug(f"⚠️ Yetersiz veri: {len(df) if df is not None else 0} mum (minimum {MIN_DATA_LEN} gerekli)")
        return None, None

    # Indikatörler
    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"]

    rsi = ta.rsi(close, length=14)
    ema50 = ta.ema(close, length=50)
    ema200 = ta.ema(close, length=200)
    macd_df = safe_ta_macd(close)
    adx_df = safe_ta_adx(high, low, close)

    # Son değerler (güvenli çekim)
    try:
        rsi_last = float(rsi.iloc[-1]) if not rsi.isna().iloc[-1] else None
    except Exception:
        rsi_last = None

    try:
        ema50_last = float(ema50.iloc[-1]) if not ema50.isna().iloc[-1] else None
        ema200_last = float(ema200.iloc[-1]) if not ema200.isna().iloc[-1] else None
    except Exception:
        ema50_last = ema200_last = None

    # MACD cross kontrolü
    macd_cross = None
    if macd_df is not None:
        try:
            macd_line = macd_df.iloc[:, 0]  # MACD line
            macd_signal = macd_df.iloc[:, 2]  # signal line
            macd_last = float(macd_line.iloc[-1])
            macd_signal_last = float(macd_signal.iloc[-1])
            macd_prev = float(macd_line.iloc[-2])
            macd_signal_prev = float(macd_signal.iloc[-2])
            # Bullish cross: prev MACD <= prev SIGNAL and last MACD > last SIGNAL
            if (macd_prev <= macd_signal_prev) and (macd_last > macd_signal_last):
                macd_cross = "bull"
            # Bearish cross:
            elif (macd_prev >= macd_signal_prev) and (macd_last < macd_signal_last):
                macd_cross = "bear"
        except Exception:
            macd_cross = None

    # ADX
    adx_last = None
    if adx_df is not None:
        try:
            adx_last = float(adx_df["ADX_14"].iloc[-1])
        except Exception:
            adx_last = None

    # Volume check
    # vol_avg = None
    # vol_last = None
    # try:
    #     vol_avg = float(vol.rolling(VOLUME_WINDOW).mean().iloc[-2])  # ölçü: önceki mumlar ortalaması
    #     vol_last = float(vol.iloc[-1])
    # except Exception:
    #     vol_avg = vol_last = None

    # vol_pct = None
    # if vol_avg and vol_last:
    #     try:
    #         vol_pct = (vol_last - vol_avg) / vol_avg * 100.0
    #     except Exception:
    #         vol_pct = None
    
    # Volume check disabled - set to None
    vol_avg = None
    vol_last = None
    vol_pct = None

    # Koşullar:
    # LONG:
    #  - EMA50 > EMA200
    #  - RSI < 40
    #  - MACD bullish cross
    #  - ADX > ADX_MIN
    #  - vol_pct >= VOLUME_THRESHOLD_PCT
    long_ok = False
    short_ok = False

    if (ema50_last is not None and ema200_last is not None and
        rsi_last is not None and macd_cross is not None and adx_last is not None):  # vol_pct check commented out
        if ema50_last > ema200_last and rsi_last < 40 and macd_cross == "bull" and adx_last > ADX_MIN:  # and vol_pct >= VOLUME_THRESHOLD_PCT:
            long_ok = True
        if ema50_last < ema200_last and rsi_last > 60 and macd_cross == "bear" and adx_last > ADX_MIN:  # and vol_pct >= VOLUME_THRESHOLD_PCT:
            short_ok = True

    # Detaylar raporu
    details = {
        "rsi": rsi_last,
        "ema50": ema50_last,
        "ema200": ema200_last,
        "macd_cross": macd_cross,
        "adx": adx_last,
        "vol_last": vol_last,
        "vol_avg": vol_avg,
        "vol_pct": vol_pct
    }

    if long_ok:
        logging.info(f"🟢 LONG sinyali tespit edildi!")
        return "LONG", details
    if short_ok:
        logging.info(f"🔴 SHORT sinyali tespit edildi!")
        return "SHORT", details
    
    logging.debug(f"⏸️  Sinyal yok (EMA50/200, RSI, MACD, ADX veya hacim koşulları sağlanmadı)")
    return None, details

def calculate_tp_sl_values(price, side):
    if side == "LONG":
        tp = price * (1 + TP_PERCENT/100.0)
        sl = price * (1 - SL_PERCENT/100.0)
    elif side == "SHORT":
        tp = price * (1 - TP_PERCENT/100.0)
        sl = price * (1 + SL_PERCENT/100.0)
    else:
        return None, None
    return round(tp, 4), round(sl, 4)

def plot_chart(df, tp=None, sl=None, symbol="COIN"):
    logging.info(f"📊 {symbol} için grafik çiziliyor...")
    path = f"{symbol}_15m_chart.png"
    add_lines = []
    if tp is not None:
        add_lines.append(mpf.make_addplot([tp]*len(df), linestyle="--"))
    if sl is not None:
        add_lines.append(mpf.make_addplot([sl]*len(df), linestyle="--"))
    mpf.plot(df, type='candle', style='charles', volume=True, addplot=add_lines, savefig=path)
    logging.info(f"✅ {symbol} grafiği oluşturuldu: {path}")
    return path

# send_message fonksiyonu artık lib.sms.sms modülünden import ediliyor

# --------------------------
# Ana döngü
# --------------------------


strategy_name = os.path.splitext(os.path.basename(__file__))[0]
strategy_name = strategy_name.replace("-", " ").capitalize()

async def main():
    logging.info("=" * 60)
    logging.info("🚀 Crypto Sinyal Bot başlatılıyor...")
    logging.info(f"📋 Strateji: {strategy_name}")
    logging.info(f"📋 Takip edilen coinler: {', '.join(COINS)}")
    logging.info(f"⏱️  Kontrol periyodu: {PERIOD_SECONDS//60} dakika")
    logging.info(f"🎯 TP: %{TP_PERCENT} | 🛑 SL: %{SL_PERCENT}")
    logging.info("=" * 60)
    
    # Bot başlangıç mesajı gönder
    startup_message = (
        f"🚀 *BOT BAŞLATILDI* 🚀\n\n"
        f"📋 Strateji: {strategy_name}\n\n"
        f"⏰ Başlangıç zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - GMT-6 \n\n"
        f"📋 Takip edilen coinler:\n{', '.join(COINS)}\n\n"
        f"⏱️ Kontrol periyodu: {PERIOD_SECONDS//60} dakika\n"
        f"🎯 Take Profit: %{TP_PERCENT}\n"
        f"🛑 Stop Loss: %{SL_PERCENT}\n"
        f"📊 Min ADX: {ADX_MIN}\n"
        f"📈 Hacim eşiği: %{VOLUME_THRESHOLD_PCT}\n\n"
        f"✅ Bot aktif ve sinyal arayışında!"
    )
    
    try:
        await send_message(startup_message, chat_types=["signal","log"])
        logging.info("✅ Başlangıç mesajı Telegram'a gönderildi!")
    except Exception as e:
        logging.error(f"❌ Başlangıç mesajı gönderilemedi: {e}")
    
    last_sent_text = {coin: None for coin in COINS}
    last_sent_time = {coin: datetime.min for coin in COINS}

    while True:
        logging.info(f"\n\n🔄 Yeni kontrol döngüsü başlıyor... ({datetime.now().strftime('%H:%M:%S')})\n\n")
        
        for coin in COINS:
            try:
                logging.info(f"\n\n--- {coin} kontrol ediliyor ---")
                df = get_candles(coin, limit=300)
                if df is None or df.empty:
                    logging.warning(f"⏭️  {coin} atlanıyor (veri yok)")
                    continue

                price = float(df["close"].iloc[-1])
                logging.info(f"💰 {coin} güncel fiyat: {price}")
                
                side, details = calculate_signal(df)
                
                # Her coin için detaylı bilgi göster
                if details:
                    trend_text = ""
                    if details.get("ema50") is not None and details.get("ema200") is not None:
                        if details["ema50"] > details["ema200"]:
                            trend_text = "📈 Yükseliş trendi (EMA50>EMA200)"
                        else:
                            trend_text = "📉 Düşüş trendi (EMA50<EMA200)"
                    
                    vol_pct_str = f"{details['vol_pct']:.1f}%" if details.get("vol_pct") is not None else "N/A"
                    adx_str = f"{details['adx']:.1f}" if details.get("adx") is not None else "N/A"
                    rsi_str = f"{details['rsi']:.1f}" if details.get("rsi") is not None else "N/A"
                    macd_str = details.get("macd_cross", "N/A")
                    
                    logging.info(f"📊 Trend: {trend_text}")
                    logging.info(f"📈 RSI: {rsi_str} | MACD Cross: {macd_str} | ADX: {adx_str}")
                    logging.info(f"📊 Hacim artışı: {vol_pct_str} (Eşik: %{VOLUME_THRESHOLD_PCT})")
                    
                    # Koşulların durumu
                    if side is None:
                        reasons = []
                        if details.get("ema50") and details.get("ema200"):
                            if details["ema50"] > details["ema200"]:
                                if not (details.get("rsi") and details["rsi"] < 40):
                                    reasons.append(f"RSI yeterince düşük değil ({rsi_str}, <40 olmalı)")
                                if macd_str != "bull":
                                    reasons.append(f"MACD bullish cross yok ({macd_str})")
                            else:
                                if not (details.get("rsi") and details["rsi"] > 60):
                                    reasons.append(f"RSI yeterince yüksek değil ({rsi_str}, >60 olmalı)")
                                if macd_str != "bear":
                                    reasons.append(f"MACD bearish cross yok ({macd_str})")
                        
                        if details.get("adx") and details["adx"] <= ADX_MIN:
                            reasons.append(f"ADX yetersiz ({adx_str}, >{ADX_MIN} olmalı)")
                        
                        if details.get("vol_pct") and details["vol_pct"] < VOLUME_THRESHOLD_PCT:
                            reasons.append(f"Hacim artışı yetersiz ({vol_pct_str}, >%{VOLUME_THRESHOLD_PCT} olmalı)")
                        
                        if reasons:
                            logging.info(f"⏸️  Sinyal YOK - Eksik koşullar:")
                            for reason in reasons:
                                logging.info(f"   ❌ {reason}")
                            
                            # Diagnostic mesajını Telegram'a gönder
                            diagnostic_message = (
                                f"📊 {coin} Analiz Raporu\n"
                                f"━━━━━━━━━━━━━━━━━\n\n"
                                f"📋 Strateji: {strategy_name}\n\n"
                                f"💰 Güncel fiyat: {price}\n"
                                f"📊 Trend: {trend_text}\n"
                                f"📈 RSI: {rsi_str} | MACD Cross: {macd_str} | ADX: {adx_str}\n"
                                f"📊 Hacim artışı: {vol_pct_str} (Eşik: %{VOLUME_THRESHOLD_PCT})\n\n"
                                f"⏸️ Sinyal YOK - Eksik koşullar:\n"
                            )
                            for reason in reasons:
                                diagnostic_message += f"   ❌ {reason}\n"
                            diagnostic_message += f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - GMT-6"
                            
                            # Log chat'e gönder
                            await send_message(diagnostic_message, chat_types=["log"])
                        else:
                            logging.info(f"⏸️  {coin} için sinyal yok")
                        continue
                else:
                    logging.info(f"⏸️  {coin} için detay bilgisi alınamadı")
                    continue

                # Sinyal tespit edildi!
                logging.info(f"{'🟢' if side == 'LONG' else '🔴'} ═══ {side} SİNYALİ TESPİT EDİLDİ! ═══")
                logging.info(f"✅ Tüm koşullar sağlandı:")
                logging.info(f"   ✓ Trend: {trend_text}")
                logging.info(f"   ✓ RSI: {rsi_str} {'(<40 ✓)' if side == 'LONG' else '(>60 ✓)'}")
                logging.info(f"   ✓ MACD Cross: {macd_str} ✓")
                logging.info(f"   ✓ ADX: {adx_str} (>{ADX_MIN} ✓)")
                logging.info(f"   ✓ Hacim artışı: {vol_pct_str} (>%{VOLUME_THRESHOLD_PCT} ✓)")
                
                tp, sl = calculate_tp_sl_values(price, side)
                logging.info(f"🎯 TP: {tp} | 🛑 SL: {sl}")

                # Mesajı oluştur
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                emoji = "🟢" if side == "LONG" else "🔴"
                trend_text_msg = ""
                if details.get("ema50") is not None and details.get("ema200") is not None:
                    if details["ema50"] > details["ema200"]:
                        trend_text_msg = "Yükseliş (EMA50>EMA200)"
                    else:
                        trend_text_msg = "Düşüş (EMA50<EMA200)"
                vol_pct_str = f"{details['vol_pct']:.1f}%" if details.get("vol_pct") is not None else "N/A"
                adx_str = f"{details['adx']:.1f}" if details.get("adx") is not None else "N/A"
                rsi_str = f"{details['rsi']:.1f}" if details.get("rsi") is not None else "N/A"
                macd_str = details.get("macd_cross", "N/A")

                message = (
                    f"📊 {coin} Analiz Raporu\n"
                    f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📋 Strateji: {strategy_name}\n\n"
                    f"💰 Güncel fiyat: {price}\n"
                    f"✳️ Sinyal: {emoji} {side}\n"
                    f"📊 Trend: {trend_text_msg}\n"
                    f"📈 RSI: {rsi_str} | MACD: {macd_str} | ADX: {adx_str} | Hacim artışı: {vol_pct_str}\n"
                    f"🎯 TP: {tp} | 🛑 SL: {sl}\n\n"
                    f"⏰ {now} - GMT-6"
                )

                # Spam kontrolü: aynı mesajı tekrar göndermeme ve minimum bekleme süresi
                resend_allowed = (last_sent_text[coin] != message) and (datetime.now() - last_sent_time[coin] > timedelta(minutes=MIN_RESEND_MINUTES))

                if resend_allowed:
                    logging.info(f"📤 {coin} için Telegram mesajı gönderiliyor...")
                    chart_path = plot_chart(df, tp=tp, sl=sl, symbol=coin)
                    await send_message(message, chat_types=["signal","log"], chart_path=chart_path)
                    last_sent_text[coin] = message
                    last_sent_time[coin] = datetime.now()
                    logging.info(f"✅ {coin} mesajı başarıyla gönderildi!")
                else:
                    time_since_last = (datetime.now() - last_sent_time[coin]).total_seconds() / 60
                    logging.warning(f"⏳ {coin} için spam koruması aktif (son mesajdan {time_since_last:.1f} dk geçti, minimum {MIN_RESEND_MINUTES} dk gerekli)")

            except Exception as e:
                logging.error(f"❌ {coin} işlem hatası: {e}")

        logging.info(f"\n\n💤 Tüm coinler kontrol edildi. {PERIOD_SECONDS//60} dakika bekleniyor...")
        try:
            await send_message(f"💤 Tüm coinler kontrol edildi. {PERIOD_SECONDS//60} dakika bekleniyor...", chat_types=["log"])
            logging.info("✅ Tüm mesajlar Telegram'a gönderildi! \n\n")
        except Exception as e:
            logging.error(f"❌ Tüm mesajlar Telegram'a gönderilemedi: {e} \n\n")
        await asyncio.sleep(PERIOD_SECONDS)

if __name__ == "__main__":
    asyncio.run(main())
