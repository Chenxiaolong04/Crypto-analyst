"""
Script di test per verificare che tutte le librerie funzionino correttamente
"""

def test_imports():
    """Test delle importazioni"""
    try:
        print("🔍 Testando importazioni...")
        
        import pandas as pd
        print("✅ pandas importato con successo")
        
        import numpy as np
        print("✅ numpy importato con successo")
        
        import matplotlib.pyplot as plt
        print("✅ matplotlib importato con successo")
        
        import requests
        print("✅ requests importato con successo")
        
        import ccxt
        print("✅ ccxt importato con successo")
        
        # import pandas_ta as ta
        # print("✅ pandas_ta importato con successo")
        print("✅ Indicatori tecnici (implementazione custom)")
        
        from telegram import Update
        from telegram.ext import Application
        print("✅ python-telegram-bot importato con successo")
        
        from dotenv import load_dotenv
        print("✅ python-dotenv importato con successo")
        
        print("\n🎉 Tutti i pacchetti sono installati correttamente!")
        return True
        
    except ImportError as e:
        print(f"❌ Errore importazione: {e}")
        return False

def test_basic_functionality():
    """Test funzionalità di base"""
    try:
        print("\n🔍 Testando funzionalità di base...")
        
        # Test pandas e numpy
        import pandas as pd
        import numpy as np
        df = pd.DataFrame({
            'close': np.random.rand(100) * 100 + 50,
            'volume': np.random.rand(100) * 1000000
        })
        print("✅ DataFrame pandas creato")
        
        # Test indicatori tecnici custom
        from crypto_bot import calculate_rsi, calculate_macd
        rsi = calculate_rsi(df['close'], 14)
        macd_data = calculate_macd(df['close'])
        print("✅ Indicatori tecnici calcolati")
        
        # Test matplotlib
        import matplotlib.pyplot as plt
        plt.figure(figsize=(8, 6))
        plt.plot(df['close'][:20])
        plt.title('Test Grafico')
        plt.close()
        print("✅ Grafico matplotlib creato")
        
        # Test CCXT (senza connessione)
        import ccxt
        exchange = ccxt.binance({
            'apiKey': '',
            'secret': '',
            'timeout': 30000,
            'enableRateLimit': True,
        })
        print("✅ Exchange CCXT inizializzato")
        
        print("\n🎉 Test funzionalità completato con successo!")
        return True
        
    except Exception as e:
        print(f"❌ Errore test funzionalità: {e}")
        return False

def main():
    """Funzione principale di test"""
    print("🤖 Test Bot Telegram Analisi Crypto")
    print("=" * 50)
    
    # Test importazioni
    if not test_imports():
        print("\n❌ Test falliti - controllare le installazioni")
        return
    
    # Test funzionalità
    if not test_basic_functionality():
        print("\n❌ Test funzionalità falliti")
        return
    
    print("\n" + "=" * 50)
    print("✅ TUTTI I TEST COMPLETATI CON SUCCESSO!")
    print("\n📋 Prossimi passi:")
    print("1. Ottenere token Telegram da @BotFather")
    print("2. (Opzionale) Ottenere token CryptoPanic")
    print("3. Creare file .env con i token")
    print("4. Eseguire crypto_bot.py")
    print("\n🚀 Il bot è pronto per l'uso!")

if __name__ == "__main__":
    main()
