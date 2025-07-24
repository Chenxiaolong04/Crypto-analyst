# 🚀 Guida Setup Bot Telegram Crypto

## ⚡ Quick Start

### 1. Ottenere Token Telegram (OBBLIGATORIO)
1. Vai su [@BotFather](https://t.me/BotFather) su Telegram
2. Scrivi `/newbot`
3. Scegli un nome per il bot (es. "Il mio Bot Crypto")
4. Scegli un username (deve finire con "bot", es. "mio_crypto_bot")
5. **Copia il token ricevuto** (tipo: `1234567890:ABC...`)

### 2. Configurare Token
1. Copia il file `.env.example` in `.env`
2. Modifica `.env` inserendo il tuo token:
```env
TELEGRAM_BOT_TOKEN=il_tuo_token_qui
```

### 3. Avviare il Bot
```bash
python crypto_bot.py
```

## 🔧 Setup Completo

### Token CryptoPanic (Opzionale per News)
1. Vai su [CryptoPanic Developers](https://cryptopanic.com/developers/api/)
2. Registrati gratuitamente
3. Ottieni il token API
4. Aggiungi nel file `.env`:
```env
CRYPTOPANIC_TOKEN=il_tuo_token_cryptopanic
```

### Comandi Bot
- `/start` - Messaggio di benvenuto
- `/btc` - Analisi Bitcoin
- `/crypto BTC` - Analisi Bitcoin 
- `/crypto ETH` - Analisi Ethereum
- `/crypto <simbolo>` - Analisi qualsiasi crypto

## 🌐 Deploy su Replit

### 1. Importa su Replit
1. Vai su [Replit.com](https://replit.com)
2. "Create Repl" → "Import from GitHub"
3. Incolla URL del tuo repository

### 2. Configura Secrets
Nel pannello Replit:
1. Clicca "Secrets" (🔒)
2. Aggiungi:
   - Key: `TELEGRAM_BOT_TOKEN`, Value: il tuo token
   - Key: `CRYPTOPANIC_TOKEN`, Value: il tuo token (opzionale)

### 3. Run
Clicca "Run" - il bot si avvierà automaticamente!

### 4. Keep Always On
- Usa [UptimeRobot](https://uptimerobot.com/) gratuito
- Monitora l'URL del tuo Repl ogni 5 minuti
- Il bot resterà sempre attivo

## 🛠️ Troubleshooting

### Bot non risponde
- Verifica token Telegram nel file `.env`
- Controlla che il bot sia avviato senza errori
- Testa con `/start`

### Errori API
- Binance API ha limiti di rate - aspetta qualche secondo
- Se CryptoPanic non funziona, il bot usa news di fallback

### Grafici non si generano
- Verifica installazione matplotlib
- Su alcuni sistemi: `pip install pillow`

## 📊 Personalizzazione

### Modificare Timeframe
Nel file `crypto_bot.py`, linea ~90:
```python
# Cambia '1h' per timeframe diverso
ohlcv = self.exchange.fetch_ohlcv(symbol, '4h', limit=100)
```

### Aggiungere Indicatori
Aggiungi nuove funzioni in `crypto_bot.py`:
```python
def calculate_bollinger_bands(prices, window=20):
    sma = prices.rolling(window).mean()
    std = prices.rolling(window).std()
    upper = sma + (std * 2)
    lower = sma - (std * 2)
    return upper, lower
```

### Altri Exchange
Per usare altri exchange, modifica:
```python
self.exchange = ccxt.coinbase()  # o kraken(), binance(), etc.
```

## 🔐 Sicurezza

- **NON** condividere mai il token Telegram
- Usa variabili d'ambiente (file `.env`)
- Su Replit, usa sempre "Secrets", mai codice hardcoded

## 📈 Funzionalità Incluse

✅ Prezzi real-time da Binance  
✅ RSI, MACD, analisi volumi  
✅ Grafici candlestick professionali  
✅ News automatiche (CryptoPanic + fallback)  
✅ Suggerimenti tecnici intelligenti  
✅ Supporto tutte le crypto principali  
✅ Ottimizzato per hosting gratuito  
✅ Messaggi formattati e leggibili  

## 🆘 Supporto

Se hai problemi:
1. Controlla la console per errori
2. Verifica i token nel file `.env`
3. Testa le funzioni con `python test_setup.py`

**Il bot è pronto! Buon trading! 🚀📊**
