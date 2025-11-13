# 📊 Telegram Coin Bot - Kripto Para Sinyal Botu

Bu proje, Bitget API'sini kullanarak kripto para piyasalarını analiz eden ve Telegram üzerinden trading sinyalleri gönderen otomatik bir bot sistemidir. Bot, teknik analiz indikatörlerini kullanarak LONG ve SHORT sinyalleri üretir ve kullanıcılara Telegram üzerinden bildirim gönderir.

## 🎯 Proje Özellikleri

- **Multi-Strategy Support**: Farklı trading stratejilerini kolayca seçip çalıştırabilme
- **Real-time Analysis**: Bitget API'den gerçek zamanlı mum verileri çekme
- **Technical Indicators**: RSI, EMA, MACD, ADX gibi teknik analiz indikatörleri
- **Telegram Integration**: Sinyalleri Telegram üzerinden gönderme
- **Chart Generation**: Otomatik grafik oluşturma (TP/SL çizgileri ile)
- **Spam Protection**: Aynı sinyalin tekrar gönderilmesini önleme
- **Environment Modes**: Development ve Production modları

## 📁 Proje Yapısı

```
telegram-coin-bot/
├── main.py                 # Ana menü ve strateji seçici
├── lib/
│   ├── utils.py            # API fonksiyonları, TP/SL hesaplama, grafik oluşturma
│   └── sms/
│       └── sms.py          # Telegram bot entegrasyonu
├── strategies/
│   ├── no-risk.py          # Hacim filtresi ile strateji
│   ├── no-risk-2.py        # Hacim filtresi olmadan strateji
│   └── test.py             # Test stratejisi
├── test/
│   ├── candle.py           # Mum verisi testleri
│   └── sms.py              # Telegram mesaj testleri
├── temp/                   # Geçici dosyalar (grafikler)
├── pyproject.toml          # Proje konfigürasyonu
└── requirements.txt        # Python bağımlılıkları
```

## 🚀 Kurulum

### Gereksinimler

- Python 3.12 veya üzeri
- Telegram Bot Token
- Bitget API erişimi (public API, authentication gerekmez)

### Adımlar

1. **Repository'yi klonlayın:**

```bash
git clone <repository-url>
cd telegram-coin-bot
```

2. **Bağımlılıkları yükleyin:**

```bash
bun install
# veya
pip install -r requirements.txt
```

3. **Environment değişkenlerini ayarlayın:**
   `.env` dosyası oluşturun ve aşağıdaki değişkenleri ekleyin:

```env
# Telegram Bot Ayarları
BOT_TOKEN=your_telegram_bot_token

# Environment Mode (dev veya pro)
ENV=dev

# Telegram Chat ID'leri
# Development modunda:
SIGNAL_TEST_CHAT_ID=your_test_chat_id

# Production modunda:
SIGNAL_CHAT_ID=your_signal_chat_id
SIGNAL_LOG_CHAT_ID=your_log_chat_id
```

4. **Botu başlatın:**

```bash
python main.py
```

## 📖 Kullanım

### Ana Menü

`main.py` çalıştırıldığında, kullanıcıya interaktif bir menü sunulur:

- ⬆️⬇️ **Ok tuşları**: Stratejiler arasında gezinme
- **Enter**: Seçili stratejiyi çalıştırma
- **ESC**: Çıkış

### Stratejiler

#### 1. No-Risk Stratejisi (`no-risk.py`)

**Özellikler:**

- **EMA Filtresi**: EMA50 > EMA200 (LONG için), EMA50 < EMA200 (SHORT için)
- **RSI Filtresi**: RSI < 40 (LONG), RSI > 60 (SHORT)
- **MACD Cross**: Bullish/Bearish cross tespiti
- **ADX Filtresi**: Minimum ADX > 20 (güçlü trend)
- **Hacim Filtresi**: Son mum hacmi, son 10 mum ortalamasının %15 üzerinde olmalı
- **TP/SL**: %1.0 Take Profit, %0.6 Stop Loss
- **Kontrol Periyodu**: 15 dakika
- **Spam Koruması**: Aynı coin için 30 dakika minimum bekleme

**Takip Edilen Coinler:**

- BTCUSDT, ETHUSDT, DOGEUSDT, SOLUSDT, WIFUSDT, PEPEUSDT, SHIBUSDT, AVAXUSDT, SUIUSDT, LTCUSDT, XRPUSDT

#### 2. No-Risk-2 Stratejisi (`no-risk-2.py`)

No-Risk stratejisinin hacim filtresi olmadan versiyonu. Diğer tüm özellikler aynıdır.

#### 3. Test Stratejisi (`test.py`)

Daha basit bir test stratejisi:

- **TP/SL**: %0.5 Take Profit, %0.3 Stop Loss
- Daha az coin takibi (7 coin)
- Basitleştirilmiş sinyal mantığı

## 🔧 Modüller

### `lib/utils.py`

**Fonksiyonlar:**

- `get_candles(symbol, granularity, limit)`: Bitget API'den mum verileri çeker

  - **Parametreler:**
    - `symbol`: Coin sembolü (örn: "BTCUSDT")
    - `granularity`: Zaman dilimi ("1min", "15min", "1h", "1day", vb.)
    - `limit`: Çekilecek mum sayısı (max 200)
  - **Döndürür:** pandas DataFrame (timestamp, open, high, low, close, volume, quote_volume, quote_volume_repeat)

- `get_tp_and_sl(df, signal, tp_percent, sl_percent)`: Take Profit ve Stop Loss seviyelerini hesaplar

  - **Parametreler:**
    - `df`: Mum verisi DataFrame'i
    - `signal`: "LONG" veya "SHORT"
    - `tp_percent`: TP yüzdesi (örn: 1.0 = %1)
    - `sl_percent`: SL yüzdesi (örn: 0.6 = %0.6)
  - **Döndürür:** (tp, sl) tuple

- `get_chart(df, strategy_name, granularity, tp, sl, symbol)`: Grafik oluşturur
  - **Parametreler:**
    - `df`: Mum verisi DataFrame'i
    - `strategy_name`: Strateji adı
    - `granularity`: Zaman dilimi
    - `tp`: Take Profit seviyesi (opsiyonel)
    - `sl`: Stop Loss seviyesi (opsiyonel)
    - `symbol`: Coin sembolü
  - **Döndürür:** Grafik dosyası yolu (PNG)

### `lib/sms/sms.py`

**Fonksiyonlar:**

- `send_message(text, chat_types, chart_path)`: Telegram'a mesaj gönderir

  - **Parametreler:**
    - `text`: Gönderilecek mesaj metni
    - `chat_types`: Chat tipi listesi (["signal"], ["log"], ["signal", "log"])
    - `chart_path`: Grafik dosyası yolu (opsiyonel)
  - **Döndürür:** None (async)

- `test_text_message(chat_types)`: Test mesajı gönderir
- `test_multi_chat_message(chat_types)`: Multi-chat test mesajı gönderir
- `test_message_with_chart(chat_types)`: Grafik ile test mesajı gönderir

## 📊 Teknik Analiz İndikatörleri

### RSI (Relative Strength Index)

- **Period**: 14
- **LONG Koşulu**: RSI < 40
- **SHORT Koşulu**: RSI > 60

### EMA (Exponential Moving Average)

- **EMA50**: 50 periyotluk EMA
- **EMA200**: 200 periyotluk EMA
- **LONG Koşulu**: EMA50 > EMA200
- **SHORT Koşulu**: EMA50 < EMA200

### MACD (Moving Average Convergence Divergence)

- **Parametreler**: 12, 26, 9
- **LONG Koşulu**: Bullish cross (MACD line signal line'ı yukarı keser)
- **SHORT Koşulu**: Bearish cross (MACD line signal line'ı aşağı keser)

### ADX (Average Directional Index)

- **Period**: 14
- **Minimum Eşik**: 20
- **Amaç**: Güçlü trend tespiti

### Volume Analysis

- **Window**: Son 10 mum
- **Eşik**: %15 artış (no-risk.py'de aktif, no-risk-2.py'de devre dışı)

## 🔐 Environment Modları

### Development Mode (`ENV=dev`)

- Test chat ID kullanılır
- Hem signal hem log mesajları aynı chat'e gider
- Debugging için daha fazla log

### Production Mode (`ENV=pro`)

- Production chat ID'leri kullanılır
- Signal ve log mesajları ayrı chat'lere gider
- Daha az log, sadece önemli mesajlar

## 🧪 Test

### Mum Verisi Testi

```bash
python test/candle.py
```

### Telegram Mesaj Testi

```bash
python test/sms.py
```

## 📝 Yeni Strateji Ekleme

1. `strategies/` klasörüne yeni bir `.py` dosyası oluşturun
2. Dosyada `main()` fonksiyonu tanımlayın (async veya sync)
3. Strateji adını dosya adından otomatik alınır
4. `main.py` çalıştırıldığında yeni strateji menüde görünecektir

**Örnek Strateji Şablonu:**

```python
import asyncio
from lib.utils import get_candles, get_tp_and_sl, get_chart
from lib.sms.sms import send_message
import os

strategy_name = os.path.splitext(os.path.basename(__file__))[0]

async def main():
    # Strateji kodunuz buraya
    pass

if __name__ == "__main__":
    asyncio.run(main())
```

## ⚙️ Konfigürasyon

### Strateji Parametreleri

Her strateji dosyasında aşağıdaki parametreler ayarlanabilir:

- `COINS`: Takip edilecek coin listesi
- `PERIOD_SECONDS`: Kontrol periyodu (saniye)
- `TP_PERCENT`: Take Profit yüzdesi
- `SL_PERCENT`: Stop Loss yüzdesi
- `ADX_MIN`: Minimum ADX eşiği
- `VOLUME_THRESHOLD_PCT`: Hacim artış eşiği
- `MIN_RESEND_MINUTES`: Spam koruma bekleme süresi

## 🐛 Sorun Giderme

### Telegram Mesajları Gönderilmiyor

- `.env` dosyasında `BOT_TOKEN` doğru mu kontrol edin
- Chat ID'lerin doğru olduğundan emin olun
- Bot'un chat'e erişim izni olduğunu kontrol edin

### API Hataları

- İnternet bağlantınızı kontrol edin
- Bitget API'nin erişilebilir olduğunu doğrulayın
- Rate limit aşılmamış olmalı

### Grafik Oluşturulmuyor

- `temp/` klasörünün yazılabilir olduğundan emin olun
- `mplfinance` kütüphanesinin yüklü olduğunu kontrol edin

## 📦 Bağımlılıklar

- `requests`: HTTP istekleri için
- `pandas`: Veri işleme için
- `pandas-ta`: Teknik analiz indikatörleri için
- `numpy`: Sayısal hesaplamalar için
- `mplfinance`: Grafik oluşturma için
- `python-telegram-bot`: Telegram bot API'si için
- `python-dotenv`: Environment değişkenleri için

## 📄 Lisans

Bu proje kişisel kullanım içindir.

## ⚠️ Uyarı

Bu bot sadece eğitim ve araştırma amaçlıdır. Trading yapmadan önce:

- Kendi risk analizinizi yapın
- Demo hesaplarda test edin
- Sadece kaybetmeyi göze alabileceğiniz parayla trade yapın
- Finansal danışmanlık alın

## 🤝 Katkıda Bulunma

1. Fork yapın
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit yapın (`git commit -m 'Add amazing feature'`)
4. Push yapın (`git push origin feature/amazing-feature`)
5. Pull Request açın

## 📞 İletişim

Sorularınız için issue açabilirsiniz.

---

**Not**: Bu bot otomatik trading yapmaz, sadece sinyal üretir. Tüm trading kararları kullanıcıya aittir.
