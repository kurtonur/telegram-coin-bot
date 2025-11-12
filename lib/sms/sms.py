import asyncio
import sys
import os
from pathlib import Path
sys.path.append('..')

from telegram import Bot, InputFile
from dotenv import load_dotenv

# .env dosyasını yükle (proje root'undan)
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Environment variables'dan al
ENV = os.getenv("ENV")

if ENV == "pro":
    SIGNAL_CHAT_ID = os.getenv("CHAT_ID")
    SIGNAL_LOG_CHAT_ID = os.getenv("SIGNAL_LOG_CHAT_ID")
else:
    TEST_ENV_KEY = "SIGNAL_TEST_CHAT_ID"
    SIGNAL_CHAT_ID = os.getenv(TEST_ENV_KEY)
    SIGNAL_LOG_CHAT_ID = os.getenv(TEST_ENV_KEY)


BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN or not SIGNAL_CHAT_ID or not SIGNAL_LOG_CHAT_ID:
    raise ValueError("❌ BOT_TOKEN, SIGNAL_CHAT_ID ve SIGNAL_LOG_CHAT_ID .env dosyasında tanımlanmalı!")

bot = Bot(token=BOT_TOKEN)

# Available chat IDs dictionary
CHAT_IDS = {
    "signal": SIGNAL_CHAT_ID,
    "log": SIGNAL_LOG_CHAT_ID,
}

async def send_message(text, chat_types=None, chart_path=None):
    """
    Telegram mesaj gönderme fonksiyonu
    
    Args:
        text: Gönderilecek mesaj
        chat_types: Liste veya string. Örnek: ["signal", "log"] veya "signal" 
                   None ise sadece log chat'e gönderilir
        chart_path: Opsiyonel grafik dosyası yolu
    """
    # Default: sadece log chat'e gönder
    if chat_types is None:
        chat_types = ["log"]
    
    # String ise liste yap
    if isinstance(chat_types, str):
        chat_types = [chat_types]
    
    # Her chat'e gönder
    for chat_type in chat_types:
        chat_id = CHAT_IDS.get(chat_type)
        
        if not chat_id:
            print(f"⚠️ Geçersiz chat type: {chat_type}")
            continue
            
        try:
            if chart_path:
                with open(chart_path, "rb") as f:
                    await bot.send_document(chat_id, document=InputFile(f), caption=text)
            else:
                await bot.send_message(chat_id, text=text)
            
            print(f"✅ Mesaj gönderildi: {chat_type} ({chat_id})")
        except Exception as e:
            print(f"❌ Mesaj gönderilemedi ({chat_type}): {e}")

async def test_text_message(chat_types=["log"]):
    """Basit metin mesajı testi - tek chat'e gönderir"""
    print(f"📤 Test mesajı gönderiliyor ({chat_types})...")
    test_msg = f"🧪 TEST MESAJI\n\nEnvironment: {ENV}\nBu bir test mesajıdır. SMS fonksiyonu çalışıyor! ✅"
    await send_message(test_msg, chat_types=chat_types)
    print("✅ Test mesajı başarıyla gönderildi!")

async def test_multi_chat_message(chat_types=["signal", "log"]):
    """Multi chat mesaj testi - tüm chatlere gönderir"""
    print("📤 Multi-chat test mesajı gönderiliyor...")
    test_msg = f"🧪 MULTI-CHAT TEST\n\nEnvironment: {ENV}\nBu mesaj tüm chatlere gönderildi! ✅"
    
    # Hem signal hem log chat'e gönder
    await send_message(test_msg, chat_types=chat_types)
    print("✅ Multi-chat test mesajı başarıyla gönderildi!")

async def test_message_with_chart(chat_types=["log"]):
    """Grafik ile mesaj testi - multi chat"""
    print("📤 Grafik ile test mesajı gönderiliyor...")
    
    # Örnek bir chart_path belirt (eğer varsa)
    # Eğer chart dosyası yoksa bu test atlanır
    chart_path = "lib/sms/test_chart.png"
    
    try:
        test_msg = (
            "🧪 GRAFIK TESTİ\n\n"
            f"Environment: {ENV}\n"
            "💰 BTCUSDT test grafiği\n"
            "📊 Bu bir test gönderisidir"
        )
        # Tüm chatlere grafik gönder
        await send_message(test_msg, chat_types=chat_types, chart_path=chart_path)
        print("✅ Grafik ile test mesajı başarıyla gönderildi!")
    except FileNotFoundError:
        print("⚠️ Grafik dosyası bulunamadı, sadece metin mesajı gönderiliyor...")
        await send_message(test_msg, chat_types=chat_types)
    except Exception as e:
        print(f"❌ Hata: {e}")

