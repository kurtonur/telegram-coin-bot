import os
import sys
import time
import importlib.util
from pathlib import Path
import msvcrt  # Windows için built-in
from dotenv import load_dotenv

def clear_screen():
    """Ekranı temizle"""
    os.system('cls' if os.name == 'nt' else 'clear')

def get_strategies():
    """strategies klasöründeki tüm Python dosyalarını listele"""
    strategies_dir = Path(__file__).parent / "strategies"
    if not strategies_dir.exists():
        return []
    
    strategies = []
    for file in strategies_dir.glob("*.py"):
        if file.name != "__init__.py":
            strategies.append({
                "name": file.stem,
                "path": file
            })
    
    return sorted(strategies, key=lambda x: x["name"])

def get_env_mode():
    """ENV değişkenini oku ve mod bilgisini döndür"""
    load_dotenv()
    env = os.getenv("ENV", "dev").strip().lower()
    if env == "pro":
        return "🟢 PRODUCTION", "pro"
    else:
        return "🔴 DEVELOPER", "dev"

def display_menu(strategies, selected_index):
    """Menüyü ekrana yazdır"""
    clear_screen()
    env_display, env_mode = get_env_mode()
    print("=" * 60)
    print("  📊 STRATEGY SELECTOR - Strateji Seçici")
    print("=" * 60)
    print(f"  Mode: {env_display}")
    print("=" * 60)
    print()
    print("  ⬆️⬇️  Ok tuşları ile seçin, Enter ile onaylayın")
    print("  ESC ile çıkış")
    print()
    print("-" * 60)
    
    if not strategies:
        print("  ⚠️  Hiç strateji bulunamadı!")
        print("  strategies/ klasörüne .py dosyaları ekleyin.")
        return
    
    for i, strategy in enumerate(strategies):
        marker = "👉" if i == selected_index else "  "
        print(f"{marker} {i + 1}. {strategy['name'].replace('-', ' ').capitalize()}")
    
    print("-" * 60)
    print()
    print(f"  Seçili: {strategies[selected_index]['name'] if strategies else 'Yok'}")

def get_key():
    """Klavye tuşunu oku (Windows için)"""
    if os.name == 'nt':
        # Windows için
        if msvcrt.kbhit():
            key = msvcrt.getch()
            # Arrow keys: 224 (special key) + 72 (up), 80 (down)
            if key == b'\xe0' or key == b'\x00':  # Special key prefix
                key = msvcrt.getch()
                if key == b'H':  # Up arrow
                    return 'up'
                elif key == b'P':  # Down arrow
                    return 'down'
            elif key == b'\r' or key == b'\n':  # Enter
                return 'enter'
            elif key == b'\x1b':  # ESC
                return 'esc'
    else:
        # Linux/Mac için
        try:
            import termios, tty
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                ch = sys.stdin.read(1)
                if ch == '\x1b':  # ESC sequence
                    ch += sys.stdin.read(2)
                    if ch == '\x1b[A':
                        return 'up'
                    elif ch == '\x1b[B':
                        return 'down'
                elif ch == '\r' or ch == '\n':
                    return 'enter'
                elif ch == '\x1b':
                    return 'esc'
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except ImportError:
            # Fallback: basit input
            return None
    return None

def run_strategy(strategy_path):
    """Seçilen stratejiyi çalıştır"""
    clear_screen()
    print("=" * 60)
    print(f"  🚀 Strateji çalıştırılıyor: {strategy_path.stem.replace("-", " ").capitalize()}")
    print("=" * 60)
    print()
    
    try:
        # Strateji modülünü dinamik olarak yükle
        spec = importlib.util.spec_from_file_location(strategy_path.stem, strategy_path)
        module = importlib.util.module_from_spec(spec)
        
        # Modülü çalıştır
        spec.loader.exec_module(module)
        
        # Eğer modülde main() fonksiyonu varsa çalıştır
        if hasattr(module, 'main'):
            import asyncio
            if asyncio.iscoroutinefunction(module.main):
                asyncio.run(module.main())
            else:
                module.main()
        else:
            print(f"⚠️  {strategy_path.stem} modülünde 'main()' fonksiyonu bulunamadı.")
            print("   Modül doğrudan çalıştırıldı.")
            
    except Exception as e:
        print(f"❌ Strateji çalıştırılırken hata oluştu: {e}")
        import traceback
        traceback.print_exc()
        print()
        input("Devam etmek için Enter'a basın...")

def main():
    """Ana menü döngüsü"""
    strategies = get_strategies()
    
    if not strategies:
        print("=" * 60)
        print("  ⚠️  Hiç strateji bulunamadı!")
        print("  strategies/ klasörüne .py dosyaları ekleyin.")
        print("=" * 60)
        input("\nDevam etmek için Enter'a basın...")
        return
    
    selected_index = 0
    
    while True:
        display_menu(strategies, selected_index)
        
        # Tuş okuma döngüsü - daha responsive olması için
        key = None
        while key is None:
            key = get_key()
            if key:
                break
            time.sleep(0.01)  # CPU spinning'i önlemek için küçük bekleme
        
        if key == 'up':
            selected_index = (selected_index - 1) % len(strategies)
        elif key == 'down':
            selected_index = (selected_index + 1) % len(strategies)
        elif key == 'enter':
            selected_strategy = strategies[selected_index]
            run_strategy(selected_strategy['path'])
            # Strateji bittikten sonra menüye dön
            input("\nMenüye dönmek için Enter'a basın...")
        elif key == 'esc':
            clear_screen()
            print("=" * 60)
            print("  👋 Çıkılıyor...")
            print("=" * 60)
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear_screen()
        print("=" * 60)
        print("  👋 Çıkılıyor...")
        print("=" * 60)

