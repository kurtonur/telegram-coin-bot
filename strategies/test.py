import asyncio
import requests
import pandas as pd
import pandas_ta as ta
import numpy as np
import mplfinance as mpf
from datetime import datetime
from lib.sms.sms import send_message  # sizin mevcut fonksiyonunuz
import logging
import os
from lib.utils import get_candles, get_tp_and_sl, get_chart

strategy_name = os.path.splitext(os.path.basename(__file__))[0]
strategy_name = strategy_name.replace("-", " ").capitalize()

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# 🪙 Takip edilecek coinler
COINS = [
    "BTCUSDT",
    "ETHUSDT",
    "DOGEUSDT",
    "SOLUSDT",
    "WIFUSDT",
    "PEPEUSDT",
    "SHIBUSDT",
]

# Zamanlama ve TP/SL ayarları
PERIOD_SECONDS = 15 * 60  # 15 dakika
TP_PERCENT = 0.5  # %0.5
SL_PERCENT = 0.3  # %0.3


# 📊 Sinyal hesaplama (RSI, EMA, MACD, ADX)
def get_signal(df):
    if df is None or len(df) < 100:
        return "⚠️ Yeterli veri yok"

    # --- Göstergelerin hesaplanması ---
    df["rsi"] = ta.rsi(df["close"], length=14)
    df["ema50"] = ta.ema(df["close"], length=50)
    df["ema200"] = ta.ema(df["close"], length=200)

    macd = ta.macd(df["close"])
    if macd is not None:
        for col in macd.columns:
            df[col] = macd[col]

    adx = ta.adx(df["high"], df["low"], df["close"])
    if adx is not None and "ADX_14" in adx.columns:
        df["adx"] = adx["ADX_14"]
    else:
        df["adx"] = np.nan

    # --- Güncel değerlerin alınması ---
    rsi_val = df["rsi"].iloc[-1]
    ema50 = df["ema50"].iloc[-1]
    ema200 = df["ema200"].iloc[-1]
    macd_val = df["MACD_12_26_9"].iloc[-1] if "MACD_12_26_9" in df.columns else None
    macd_signal = df["MACDs_12_26_9"].iloc[-1] if "MACDs_12_26_9" in df.columns else None
    adx_val = df["adx"].iloc[-1]

    # --- Ana sinyal hesaplama ---
    signal = "⚪ NÖTR"

    # Trend filtre: güçlü trend ADX>25
    trend_strong = adx_val is not None and adx_val > 25

    # MACD momentum yönü
    macd_bullish = macd_val is not None and macd_signal is not None and macd_val > macd_signal
    macd_bearish = macd_val is not None and macd_signal is not None and macd_val < macd_signal

    if rsi_val > 70 and ema50 < ema200 and macd_bearish and trend_strong:
        signal = "🔴 AŞIRI ALIM (RSI>70, MACD<sig, ADX>25) - SHORT"
    elif rsi_val < 30 and ema50 > ema200 and macd_bullish and trend_strong:
        signal = "🟢 AŞIRI SATIM (RSI<30, MACD>sig, ADX>25) - LONG"
    elif macd_bullish and ema50 > ema200 and trend_strong:
        signal = "🟢 MACD POZİTİF TREND (EMA Up, ADX>25)"
    elif macd_bearish and ema50 < ema200 and trend_strong:
        signal = "🔴 MACD NEGATİF TREND (EMA Down, ADX>25)"
    else:
        signal = "⚪ Belirsiz / Zayıf trend"

    return signal

# 🔄 Tek coin işleyici
async def process_coin(coin, last_signals):
    df = get_candles(symbol=coin, granularity="15min", limit=200)
    if df is None or len(df) == 0:
        logging.warning(f"⚠️ {coin} için veri alınamadı.")
        return

    signal = get_signal(df=df)
    tp, sl = get_tp_and_sl(df=df, signal=signal, tp_percent=TP_PERCENT, sl_percent=SL_PERCENT)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Mesaj içeriği
    full_msg = (
        f"📊 {coin} Analiz Raporu\n"
        f"━━━━━━━━━━━━━━━━━\n\n"
        f"📋 Strateji: {strategy_name}\n\n"
        f"💰 Güncel fiyat: {df['close'].iloc[-1]:.5f}\n"
        f"📊 Sinyal: {signal}"
    )
    if tp or sl:
        full_msg += f"\n🎯 TP: {tp} | 🛑 SL: {sl}"
    full_msg += f"\n\n⏰ {now} - GMT-6"
    logging.info(f"\n\n{full_msg}\n")
    
    # 🔍 Sadece gerçek sinyal (LONG veya SHORT) olduğunda mesaj gönder
    if ("LONG" in signal or "SHORT" in signal) and full_msg != last_signals.get(coin):
        chart_path = await get_chart(df=df, strategy_name=strategy_name, granularity="15min", tp=tp, sl=sl, symbol=coin)
        await send_message(text=full_msg, chat_types=["signal"], chart_path=chart_path)
        logging.info(f"\n🚀 SİNYAL GÖNDERİLDİ: {coin} | {signal}\n")
        last_signals[coin] = full_msg

    # ❌ Sinyal yoksa sadece log'a yaz
    else:
        logging.info(f"ℹ️ {coin}: Sinyal Yok → {signal}")
        await send_message(text=full_msg, chat_types=["log"])
    print("-" * 100)

# 🚀 Ana döngü
async def main():
    last_signals = {coin: None for coin in COINS}
    while True:
        for coin in COINS:
            await process_coin(coin, last_signals)
        logging.info(f"\n\n💤 Tüm coinler kontrol edildi. {PERIOD_SECONDS//60} dakika bekleniyor...")
        await asyncio.sleep(PERIOD_SECONDS)

# 🔁 Çalıştır
if __name__ == "__main__":
    asyncio.run(main())