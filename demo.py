"""
Demo del Bot Telegram per Analisi Crypto
Questo script mostra come testare le funzionalità del bot senza Telegram
"""

import asyncio
from crypto_bot import CryptoAnalysisBot

async def demo():
    """Demo delle funzionalità principali"""
    print("🤖 Demo Bot Telegram Analisi Crypto")
    print("=" * 50)
    
    # Crea istanza bot (senza token per demo)
    bot = CryptoAnalysisBot("demo_token")
    
    try:
        print("📊 Test recupero dati Bitcoin...")
        crypto_data = await bot.get_crypto_data('BTC')
        print(f"✅ Prezzo BTC: ${crypto_data['price']:,.2f}")
        print(f"✅ Variazione 24h: {crypto_data['change_24h']:.2f}%")
        
        print("\n🔍 Test calcolo indicatori tecnici...")
        indicators = bot.calculate_technical_indicators(crypto_data['df'])
        print(f"✅ RSI: {indicators['rsi']}")
        print(f"✅ MACD: {indicators['macd']:.6f}")
        
        print("\n📰 Test recupero news...")
        news = await bot.get_crypto_news('BTC')
        print(f"✅ Trovate {len(news)} notizie")
        for i, article in enumerate(news[:2], 1):
            print(f"   {i}. {article['title'][:50]}...")
        
        print("\n📈 Test generazione grafico...")
        chart_buffer = bot.create_chart(crypto_data['df'], 'BTCUSDT', indicators)
        print(f"✅ Grafico generato ({len(chart_buffer.getvalue())} bytes)")
        
        print("\n💬 Test formattazione messaggio...")
        suggestions = bot.generate_technical_suggestions(indicators, crypto_data)
        message = bot.format_message(crypto_data, indicators, news, suggestions)
        print("✅ Messaggio formattato:")
        print("-" * 30)
        print(message[:300] + "...")
        
    except Exception as e:
        print(f"❌ Errore durante demo: {e}")
        print("💡 Verifica la connessione internet e riprova")
    
    print("\n" + "=" * 50)
    print("✅ Demo completata!")
    print("🚀 Il bot è pronto per l'uso con Telegram!")

def main():
    """Funzione principale"""
    asyncio.run(demo())

if __name__ == "__main__":
    main()
