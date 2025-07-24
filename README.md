# 🤖 Bot Telegram Analisi Crypto

Bot Telegram completo per l'analisi tecnica delle criptovalute con prezzi real-time, indicatori tecnici, news e grafici professionali.

## 🚀 Funzionalità

### 📊 Analisi Completa
- **Prezzo real-time** con variazioni 24h da Binance
- **Indicatori tecnici**: RSI (14), MACD, analisi volumi
- **Grafici candlestick** con overlay degli indicatori
- **Suggerimenti tecnici** automatici basati su analisi

### 📰 News Integration
- **Ultime 3 notizie** per ogni crypto con link cliccabili
- Integrazione **CryptoPanic API** (con fallback se no API key)
- News sempre aggiornate e pertinenti

### 🎯 Comandi Disponibili
- `/start` - Messaggio di benvenuto e istruzioni
- `/btc` - Analisi completa Bitcoin
- `/crypto <simbolo>` - Analisi per qualsiasi crypto (ETH, ADA, SOL, etc.)

## 🛠️ Setup e Installazione

### 1. Clona il Repository
```bash
git clone <repository-url>
cd TradingBot
```

### 2. Installa Dipendenze
```bash
pip install -r requirements.txt
```

### 3. Configurazione API Keys

#### Telegram Bot Token (OBBLIGATORIO)
1. Vai su [@BotFather](https://t.me/BotFather) su Telegram
2. Crea nuovo bot: `/newbot`
3. Scegli nome e username per il bot
4. Copia il token ricevuto

#### CryptoPanic API (OPZIONALE)
1. Registrati su [CryptoPanic Developers](https://cryptopanic.com/developers/api/)
2. Ottieni il tuo API token gratuito
3. Senza questo token, il bot userà news di fallback

### 4. Configura Variabili d'Ambiente

Crea file `.env` dalla copia di `.env.example`:
```bash
cp .env.example .env
```

Modifica il file `.env`:
```env
TELEGRAM_BOT_TOKEN=il_tuo_token_telegram_qui
CRYPTOPANIC_TOKEN=il_tuo_token_cryptopanic_qui
```

### 5. Esegui il Bot
```bash
python crypto_bot.py
# oppure
python main.py
```

## 🌐 Deploy su Replit (Hosting Gratuito)

### 1. Importa Progetto
1. Vai su [Replit.com](https://replit.com)
2. Crea nuovo Repl → "Import from GitHub"
3. Incolla URL del repository

### 2. Configura Secrets
Nel pannello Replit:
1. Vai su "Secrets" (🔒)
2. Aggiungi:
   - `TELEGRAM_BOT_TOKEN`: il tuo token
   - `CRYPTOPANIC_TOKEN`: il tuo token (opzionale)

### 3. Run
Clicca "Run" - il bot si avvierà automaticamente!

### 4. Keep Alive
Per mantenere il bot sempre attivo su Replit:
- Usa servizi come [UptimeRobot](https://uptimerobot.com/)
- Aggiungi il tuo Repl URL per ping automatico

## 📊 Esempio di Output

```
📊 Analisi BTCUSDT (Binance)

💰 Prezzo attuale: $43,250.50
🟢 Variazione 24h: +2.4%
📈 Volume 24h: $18,400,000,000

📋 Indicatori Tecnici:
• RSI (14): 62.1 → 🟡 Neutro
• MACD: 0.000342
• MACD Signal: 0.000298
• Volume Ratio: 1.2x

💡 Analisi Tecnica:
🟡 RSI in zona neutra | 📈 MACD sopra signal line - trend rialzista

📰 Notizie Recenti:
• [Bitcoin supera i $43k in rally improvviso](https://coindesk.com/article1)
• [ETF Bitcoin: aggiornamenti SEC](https://cointelegraph.com/news2)
• [Analisi tecnica BTC - supporti chiave](https://cryptopanic.com/news3)

📈 Grafico tecnico allegato
⏰ Aggiornato: 14:32:15
```

## 🏗️ Architettura Tecnica

### Componenti Principali
- **Bot Framework**: `python-telegram-bot` per gestione comandi
- **Market Data**: `ccxt` per dati Binance real-time
- **Technical Analysis**: `pandas-ta` per indicatori (RSI, MACD)
- **Charts**: `matplotlib` per grafici candlestick
- **News**: CryptoPanic API con fallback

### Flusso di Esecuzione
1. **Comando utente** → `/crypto BTC`
2. **Fetch dati** → Binance API (prezzo, volume, OHLCV)
3. **Calcolo indicatori** → RSI, MACD su DataFrame pandas
4. **Generazione grafico** → Candlestick + indicatori overlay
5. **Fetch news** → CryptoPanic API per ultime notizie
6. **Response** → Messaggio formattato + grafico allegato

### Gestione Errori
- **API rate limiting** con retry automatico
- **Fallback news** se CryptoPanic non disponibile
- **Simboli non validi** con messaggi informativi
- **Grafici semplificati** in caso di errori tecnici

## 📝 Customizzazione

### Aggiungere Nuovi Indicatori
Modifica `calculate_technical_indicators()`:
```python
# Esempio: aggiungi Bollinger Bands
bb = ta.bbands(df['close'])
return {
    'rsi': rsi,
    'bb_upper': bb['BBU_20_2.0'].iloc[-1],
    'bb_lower': bb['BBL_20_2.0'].iloc[-1]
}
```

### Modificare Timeframe
Cambia parametri in `get_crypto_data()`:
```python
# Per candele da 4 ore invece di 1 ora
ohlcv = self.exchange.fetch_ohlcv(symbol, '4h', limit=100)
```

### Aggiungere Altri Exchange
```python
# Esempio: aggiungi Coinbase
self.exchange_coinbase = ccxt.coinbase({
    'apiKey': '',
    'secret': '',
    'enableRateLimit': True,
})
```

## ⚠️ Disclaimer

Questo bot fornisce **solo informazioni educative** e analisi tecniche. 
**Non costituisce consulenza finanziaria**. 
Le crypto sono strumenti ad alto rischio - investi responsabilmente.

## 🤝 Contributi

Contributi benvenuti! Apri issue o pull request per:
- Nuovi indicatori tecnici
- Miglioramenti grafici
- Ottimizzazioni performance
- Bug fixes

## 📄 Licenza

MIT License - vedi file LICENSE per dettagli.

---

**Sviluppato per trading education e analisi tecnica** 📊🚀
