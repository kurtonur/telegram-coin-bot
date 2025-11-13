import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.utils import get_candles
import pandas as pd

def test_get_candles():
    """get_candles fonksiyonunu test et"""
    
    print("=" * 50)
    print("🧪 get_candles Test Başlıyor...")
    print("=" * 50)
    
    # Test 1: Default parametrelerle (BTCUSDT, 15min, 200)
    print("\n📊 Test 1: Default parametreler (BTCUSDT, 15min, 200)")
    df1 = get_candles()
    if df1 is not None:
        print(f"✅ Başarılı! {len(df1)} mum verisi çekildi")
        print(f"   Kolonlar: {list(df1.columns)}")
        print(f"   İlk 5 satır:")
        print(df1.head())
        print(f"   Son 5 satır:")
        print(df1.tail())
        print(f"   Veri tipleri:")
        print(df1.dtypes)
    else:
        print("❌ Hata: Veri çekilemedi")
    
    # Test 2: Farklı symbol
    print("\n📊 Test 2: ETHUSDT için veri çekme")
    df2 = get_candles(symbol="ETHUSDT", granularity="15min", limit=50)
    if df2 is not None:
        print(f"✅ Başarılı! {len(df2)} mum verisi çekildi")
        print(f"   İlk satır:")
        print(df2.head(1))
    else:
        print("❌ Hata: Veri çekilemedi")
    
    # Test 3: Farklı granularity (1h)
    print("\n📊 Test 3: 1 saatlik mumlar (1h)")
    df3 = get_candles(symbol="BTCUSDT", granularity="1h", limit=24)
    if df3 is not None:
        print(f"✅ Başarılı! {len(df3)} mum verisi çekildi")
        print(f"   İlk satır:")
        print(df3.head(1))
    else:
        print("❌ Hata: Veri çekilemedi")
    
    # Test 4: Küçük limit
    print("\n📊 Test 4: Küçük limit (10 mum)")
    df4 = get_candles(symbol="BTCUSDT", granularity="15min", limit=10)
    if df4 is not None:
        print(f"✅ Başarılı! {len(df4)} mum verisi çekildi")
        print(f"   Tüm veriler:")
        print(df4)
    else:
        print("❌ Hata: Veri çekilemedi")
    
    # Test 5: Geçersiz symbol (hata durumu)
    print("\n📊 Test 5: Geçersiz symbol (hata testi)")
    df5 = get_candles(symbol="INVALIDCOIN", granularity="15min", limit=10)
    if df5 is None:
        print("✅ Beklenen davranış: Geçersiz symbol için None döndü")
    else:
        print(f"⚠️ Beklenmeyen: Veri döndü: {len(df5)} satır")
    
    # Test 6: DataFrame yapısını kontrol et
    print("\n📊 Test 6: DataFrame yapısı kontrolü")
    if df1 is not None:
        print(f"   Kolon sayısı: {len(df1.columns)}")
        print(f"   Beklenen kolonlar: timestamp, open, high, low, close, volume, quote_volume, quote_volume_repeat")
        expected_cols = ["open", "high", "low", "close", "volume", "quote_volume", "quote_volume_repeat"]
        missing_cols = [col for col in expected_cols if col not in df1.columns]
        if missing_cols:
            print(f"   ⚠️ Eksik kolonlar: {missing_cols}")
        else:
            print("   ✅ Tüm beklenen kolonlar mevcut")
        
        # Veri tiplerini kontrol et
        print(f"   Veri tipleri:")
        for col in df1.columns:
            print(f"      {col}: {df1[col].dtype}")
        
        # Null değer kontrolü
        null_counts = df1.isnull().sum()
        if null_counts.sum() > 0:
            print(f"   ⚠️ Null değerler var:")
            print(null_counts[null_counts > 0])
        else:
            print("   ✅ Null değer yok")
    
    print("\n" + "=" * 50)
    print("✅ Testler tamamlandı!")
    print("=" * 50)

if __name__ == "__main__":
    test_get_candles()

