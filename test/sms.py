import asyncio
import sys
from pathlib import Path

# Proje root'unu sys.path'e ekle
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from lib.sms.sms import test_text_message, test_message_with_chart

async def main():
    """Ana test fonksiyonu"""
    print("=" * 50)
    print("🧪 SMS/Telegram Mesaj Testi Başlatılıyor...")
    print("=" * 50)
    print()
    
    # Test 1: Basit metin mesajı
    await test_message_with_chart()
    print()
    
    # Test 2: Grafik ile mesaj (opsiyonel)
    # await test_message_with_chart()
    
    print()
    print("=" * 50)
    print("✅ Tüm testler tamamlandı!")
    print("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())