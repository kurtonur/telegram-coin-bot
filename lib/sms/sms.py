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
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

if not BOT_TOKEN or not CHAT_ID:
    raise ValueError("❌ BOT_TOKEN ve CHAT_ID .env dosyasında tanımlanmalı!")

bot = Bot(token=BOT_TOKEN)

async def send_message(text, chart_path=None):
    """Telegram mesaj gönderme fonksiyonu"""
    if chart_path:
        with open(chart_path, "rb") as f:
            await bot.send_document(chat_id=CHAT_ID, document=InputFile(f), caption=text)
    else:
        await bot.send_message(chat_id=CHAT_ID, text=text)

async def test_text_message():
    """Basit metin mesajı testi"""
    print("📤 Test mesajı gönderiliyor...")
    test_msg = "🧪 TEST MESAJI\n\nBu bir test mesajıdır. SMS fonksiyonu çalışıyor! ✅"
    await send_message(test_msg)
    print("✅ Test mesajı başarıyla gönderildi!")

async def test_message_with_chart():
    """Grafik ile mesaj testi"""
    print("📤 Grafik ile test mesajı gönderiliyor...")
    
    # Örnek bir chart_path belirt (eğer varsa)
    # Eğer chart dosyası yoksa bu test atlanır
    chart_path = "lib/sms/test_chart.png"
    
    try:
        test_msg = (
            "🧪 GRAFIK TESTİ\n\n"
            "💰 BTCUSDT test grafiği\n"
            "📊 Bu bir test gönderisidir"
        )
        await send_message(test_msg, chart_path=chart_path)
        print("✅ Grafik ile test mesajı başarıyla gönderildi!")
    except FileNotFoundError:
        print("⚠️ Grafik dosyası bulunamadı, sadece metin mesajı gönderiliyor...")
        await send_message(test_msg)
    except Exception as e:
        print(f"❌ Hata: {e}")

