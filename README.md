# 🤖 Bot Telegram Analisi Crypto Avanzato

Bot Telegram completo per l'analisi tecnica avanzata delle criptovalute con **predizioni AI**, **segnali MACD**, **supporti/resistenze automatici** e molto altro.

## 🚀 Funzionalità Avanzate

### 🤖 Intelligenza Artificiale
- **Predizioni AI** con livello di confidenza per decisioni long/short
- **Sistema di scoring** multi-indicatore per raccomandazioni accurate
- **Analisi del rischio** automatica (High/Medium/Low)

### 📈 Analisi MACD Professionale
- **Segnali crossover** MACD in tempo reale
- **Rilevamento divergenze** bullish/bearish automatico
- **Analisi momentum** e forza del segnale
- **Strategie di trading** personalizzate

### 🎯 Supporti e Resistenze
- **Identificazione automatica** dei livelli chiave
- **Tracciamento grafico** con linee colorate
- **Calcolo distanza** dal prezzo attuale
- **Alert di prossimità** ai livelli critici

### 📊 Analisi Tecnica Completa
- **Prezzo real-time** con variazioni 24h da Bybit
- **Indicatori tecnici avanzati**: RSI, MACD, analisi volumi
- **Grafici candlestick professionali** con segnali sovrapposti
- **Suggerimenti intelligenti** basati su AI

### 📰 News Integration
- **Ultime 3 notizie** per ogni crypto con link cliccabili
- Integrazione **CryptoPanic API** (con fallback se no API key)
- News sempre aggiornate e pertinenti

### 🎯 Comandi Disponibili
- `/start` - Messaggio di benvenuto e istruzioni complete
- `/btc` - Analisi completa Bitcoin con AI
- `/crypto <simbolo>` - Analisi completa per qualsiasi crypto
- `/signals <simbolo>` - **NUOVO**: Segnali MACD avanzati con strategie
- `/ai <simbolo>` - **NUOVO**: Predizione AI dettagliata

## 🛠️ Setup e Installazione

### 1. Clona il Repository
```bash
git clone <repository-url>
cd Crypto-analyst
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

## 📊 Esempi di Output

### 🤖 Analisi Completa (`/crypto BTC`)

```
📊 Analisi Avanzata BTCUSDT (Bybit)

💰 Prezzo attuale: $43,250.50
🟢 Variazione 24h: +2.4%
📈 Volume 24h: $18,400,000,000

🤖 PREDIZIONE AI:
🟢 BUY **STRONG LONG**
� Confidenza: 87% | Rischio: HIGH

�📋 Indicatori Tecnici:
• RSI (14): 65.2 → 🟡 Neutro
• MACD: 0.002150
• MACD Signal: 0.001980
• Volume Ratio: 1.8x

📈 Segnali MACD:
• Ultimo Crossover: 🟢 BULLISH
• Divergenza: 🟢 BULLISH
• Momentum: ⬆️ INCREASING

🎯 Livelli Chiave:
• Resistenze: $44,100.00, $45,200.00, $46,800.00
• Supporti: $42,500.00, $41,200.00, $40,000.00

🧠 Segnali AI:
• MACD crossover bullish
• Divergenza bullish MACD
• Volume elevato

💡 Analisi Tecnica:
📈 MACD crossover bullish - segnale di acquisto confermato | 
🎯 Vicino alla resistenza $44,100.00 - attenzione | 
📊 Volume elevato - movimento confermato | 
🤖 AI ad alta confidenza: 🟢 BUY

📰 Notizie Recenti:
• [Bitcoin Surges Above $43K as Institutional Interest Grows](https://example.com)
• [Major Exchange Adds BTC Trading Pairs](https://example.com)
• [Crypto Market Shows Strong Recovery Signs](https://example.com)

📈 Grafico con S/R e segnali MACD allegato
⏰ Aggiornato: 14:32:15
```

### ⚡ Segnali MACD (`/signals ETH`)

```
📊 Segnali MACD Avanzati - ETHUSDT

💰 Prezzo attuale: $2,680.75

🎯 SEGNALI MACD:
• Ultimo Crossover: 🔴 BEARISH
• Divergenza: ➡️ NONE
• Momentum: ⬇️ DECREASING
• Forza Segnale: 0.008540

🤖 PREDIZIONE AI:
🔴 SELL **SHORT**
• Confidenza: 72%
• Livello Rischio: MEDIUM

📈 STRATEGIA CONSIGLIATA:
🔴 ENTRY SHORT: Segnale di vendita confermato
📊 Stop Loss: Sopra resistenza più vicina
🎯 Take Profit: Verso supporto più vicino

🎯 LIVELLI CHIAVE:
🔴 Resistenze: $2,720.00, $2,800.00, $2,950.00
🟢 Supporti: $2,620.00, $2,550.00, $2,480.00

⏰ Analisi: 14:35:42
⚠️ Sempre usa stop loss e gestisci il rischio
```

### 🧠 Predizione AI (`/ai SOL`)

```
🤖 Analisi AI Dettagliata - SOLUSDT

💰 Prezzo: $98.45
📊 Variazione 24h: -1.2%

🧠 PREDIZIONE AI:
⚪ HOLD **HOLD**

📊 METRICHE:
• Confidenza: 45%
• Score: 0/10
• Rischio: LOW

🔍 SEGNALI IDENTIFICATI:
1. RSI neutrale (stabile)
2. Volume basso
3. Trend ribassista
4. Vicino al supporto (97.20)

🤷 SITUAZIONE INCERTA - ATTENDERE

⏰ 14:38:27
⚠️ Questa è solo un'analisi AI, non consulenza finanziaria
```

## 📈 Grafici Professionali

Il bot genera automaticamente grafici con:
- **Candlestick colorati** (verde/rosso)
- **Supporti** (linee verdi tratteggiate)
- **Resistenze** (linee rosse tratteggiate)
- **Segnali MACD** (frecce up/down sui crossover)
- **RSI con zone** (ipercomprato/ipervenduto)
- **MACD istogramma colorato**
- **Predizione AI** visualizzata nell'angolo

## 🎯 Caratteristiche Tecniche Avanzate

### 🧠 Sistema AI
- **Multi-indicator scoring** (RSI 20%, MACD 30%, S/R 25%, Volume 15%, Trend 10%)
- **Confidence scoring** da 0-100%
- **Risk assessment** automatico
- **Signal prioritization** intelligente

### 📊 Analisi MACD
- **Crossover detection** con precisione al millisecondo
- **Divergence analysis** prezzo vs indicatore
- **Momentum calculation** basato su istogramma
- **Signal strength** quantificata

### 🎯 Supporti/Resistenze
- **Peak detection** con finestra mobile
- **Level grouping** automatico (soglia 1%)
- **Proximity alerts** (entro 2% dal prezzo)
- **Historical strength** valutazione

## ⚠️ Disclaimer

**Questo bot fornisce solo informazioni educative e di analisi tecnica. Non costituisce consulenza finanziaria. Il trading di criptovalute comporta rischi significativi. Usa sempre stop loss, gestisci il rischio e non investire mai più di quanto puoi permetterti di perdere.**
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
