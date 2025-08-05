# 🚀 Crypto Analysis Bot - Segnali AI Automatici

**Bot Telegram avanzato per analisi cripto con intelligenza artificiale**, **segnali automatici LONG/SHORT** e **livelli di trading precisi**. Progettato per fornire analisi tecniche professionali e segnali ad alta confidence.

## ⚡ Caratteristiche Principali

### 🤖 **INTELLIGENZA ARTIFICIALE AVANZATA**
- **Sistema AI Multi-Indicatori:** Analisi combinata di RSI, MACD, Bollinger Bands, EMA, Stochastic, Williams %R, CCI, MFI, ATR
- **Confidence Scoring:** Segnali con confidence 65-100% basati su analisi tecnica approfondita
- **Momentum Analysis:** Rilevamento forza del trend (FORTE/MODERATO/DEBOLE)
- **Volume Analysis:** Analisi volume spike e money flow per conferme

### 🎯 **SEGNALI AUTOMATICI INTELLIGENTI**
- **LONG/SHORT Automatici:** Notifiche istantanee quando AI rileva opportunità ad alta probabilità
- **Anti-Spam System:** Cooldown di 2 ore per crypto per evitare notifiche eccessive
- **Solo Alta Qualità:** Segnali inviati solo con confidence ≥ 65%
- **Momentum Classification:** STRONG_LONG, LONG, SHORT, STRONG_SHORT

### 💰 **LIVELLI DI TRADING PRECISI**
- **Market Entry:** Prezzo per ordini a mercato immediati
- **Limit Entry:** Prezzo ottimizzato con spread intelligente (0.1%-2% basato su volatilità)
- **Take Profit:** Target basato su resistenze/supporti reali o volatilità
- **Stop Loss:** Protezione con buffer di sicurezza sotto supporti chiave
- **Precisione Dinamica:** 1-6 decimali basati sul valore del token

### 📊 **ANALISI MANUALE DETTAGLIATA**
- **Comando `/analyze`:** Analisi completa su richiesta per qualsiasi crypto supportata
- **Indicatori Tecnici:** RSI, MACD, Bollinger Bands, Volume ratio, EMA trends
- **Risk/Reward Ratio:** Calcolo potenziale profitto/perdita
- **Interpretazione AI:** Analisi in italiano dei pattern rilevati

## 🎯 Comandi Disponibili

### 🔧 **Comandi Base**
- `/start` - Avvia il bot e mostra panoramica completa
- `/help` - Guida dettagliata con tutte le funzioni
- `/status` - Stato del monitoraggio e statistiche

### 📈 **Analisi Cripto**
- `/analyze BTC` - Analisi dettagliata Bitcoin con tutti gli indicatori
- `/analyze ETH` - Analisi completa Ethereum
- `/analyze <CRYPTO>` - Analisi per qualsiasi crypto supportata

**Esempio output `/analyze`:**
```
� ANALISI DETTAGLIATA BTC/USDT

💰 PREZZO CORRENTE: $43,250.50
📈 Variazione 24h: +2.45%
📊 Volume 24h: $1,234,567,890

🚀 SEGNALE: STRONG LONG
⚡ Confidence: 87.3%
📊 Momentum: FORTE

💎 LIVELLI DI TRADING:
📊 Market Entry: $43,250.50
🎯 Limit Entry: $43,100.25
🚀 Take Profit: $44,850.00
🛡️ Stop Loss: $42,100.75

� POTENZIALE:
✅ Target: +3.7%
❌ Risk: -2.7%
📊 R/R Ratio: 1.4:1

🔍 INDICATORI TECNICI:
• RSI: 45.2
• MACD: 0.0245 / 0.0189
• BB Position: 65%
• Volume Ratio: 1.8x

📋 ANALISI:
• RSI Neutrale - Mercato bilanciato
• MACD Bullish - Momentum positivo
• Volume Alto - Interesse crescente
```

## 💎 Crypto Monitorate (72 Verificate)

Il bot monitora automaticamente **72 cryptocurrency** verificate e funzionanti su Bybit:

### 🏆 **Top Cryptocurrencies**
BTC, ETH, BNB, XRP, ADA, SOL, DOT, DOGE, AVAX, LINK, UNI, LTC, ALGO, VET, ICP, FIL, TRX, ETC, XLM

### 🔄 **DeFi & Layer 2**
AAVE, MKR, COMP, SUSHI, SNX, CRV, YFI, UMA, ZRX, LRC, FET, GRT, OP, ARB, NEAR, FLOW, ROSE, ONE, HBAR, EGLD, XTZ, KSM, ATOM

### 🎮 **Gaming & NFT**
CHZ, ENJ, MANA, SAND, AXS, SLP, GALA, IMX, GMT, APE

### 🐕 **Meme Coins**
SHIB, PEPE, FLOKI, WIF, BONK, MEME, DEGEN, POPCAT, NEIRO, MOG, BRETT, WEN, PNUT, GOAT

### 💫 **Altri Token Popolari**
LDO, FXS, SPELL, BOBA, LUNA

## 🛠️ Installazione e Setup

### 📋 **Prerequisiti**
- Python 3.8+
- Account Telegram e Bot Token
- API Key Bybit (per dati crypto)
- API Key CryptoPanic (per news)

### 🚀 **Setup Rapido**

1. **Clone il repository:**
```bash
git clone https://github.com/yourusername/crypto-analyst.git
cd crypto-analyst
```

2. **Installa dipendenze:**
```bash
pip install -r requirements.txt
```

3. **Configura environment variables:**
```bash
# .env file
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET_KEY=your_bybit_secret_key
CRYPTOPANIC_API_KEY=your_cryptopanic_api_key
```

4. **Avvia il bot:**
```bash
python crypto_bot.py
```

### 🔧 **Configurazione Avanzata**

Il bot è configurato per:
- **Monitoring Interval:** 2 minuti per segnali automatici
- **Confidence Threshold:** ≥65% per notifiche
- **Anti-Spam Cooldown:** 2 ore per crypto
- **Exchange:** Bybit per dati real-time
- **News Source:** CryptoPanic per aggiornamenti

## 📈 Come Funziona

### 🔄 **Monitoring Automatico**
1. **Scan Continuo:** Bot monitora 72 crypto ogni 2 minuti
2. **Analisi AI:** Calcola confidence basata su 9+ indicatori tecnici
3. **Filtro Qualità:** Solo segnali ≥65% confidence vengono inviati
4. **Notifica Instant:** Messaggio Telegram con tutti i dettagli

### 🎯 **Algoritmo di Segnalazione**

**STRONG_LONG (80-100% confidence):**
- RSI < 30 + MACD bullish + Volume spike + EMA trend up
- Bollinger Bands oversold + Stochastic < 20

**LONG (65-79% confidence):**
- RSI < 40 + MACD positive + Volume normale + EMA trend up
- 2+ indicatori bullish concordanti

**SHORT/STRONG_SHORT:**
- Logica opposta per segnali ribassisti
- RSI > 60/70 + MACD bearish + indicatori concordanti

### 📊 **Calcolo Livelli di Trading**

**Market Entry:** Prezzo attuale real-time da Bybit

**Limit Entry:** Prezzo ottimizzato con spread intelligente:
- Crypto >$1000: 0.1-0.3% spread
- Crypto $10-1000: 0.3-0.8% spread  
- Crypto <$10: 0.8-2% spread

**Take Profit:** Basato su:
- Resistenze tecniche (Bollinger Upper, EMA200)
- ATR x2-3 per volatilità
- Target 2-8% basato su momentum

**Stop Loss:** Basato su:
- Supporti tecnici (Bollinger Lower, EMA50) 
- ATR x1.5-2 per protezione
- Risk 1-4% massimo

## 🤖 Tecnologie Utilizzate

### 📚 **Librerie Principali**
- **python-telegram-bot** - Integrazione Telegram
- **ccxt** - Connessione exchange Bybit
- **pandas-ta** - Indicatori tecnici avanzati
- **numpy/pandas** - Analisi dati numerici
- **asyncio** - Operazioni asincrone

### 🔗 **API Integrate**
- **Bybit API** - Dati crypto real-time, OHLCV, volume
- **CryptoPanic API** - News cripto aggiornate
- **Telegram Bot API** - Messaging e comandi

### 📊 **Indicatori Tecnici**
- **RSI** (Relative Strength Index) - Momentum
- **MACD** (Moving Average Convergence Divergence) - Trend
- **Bollinger Bands** - Volatilità e mean reversion
- **EMA** (Exponential Moving Average) - Trend direction
- **Stochastic** - Overbought/oversold
- **Williams %R** - Momentum oscillator
- **CCI** (Commodity Channel Index) - Trend strength
- **MFI** (Money Flow Index) - Volume-price relationship
- **ATR** (Average True Range) - Volatilità

## 🚨 Disclaimer Importante

⚠️ **QUESTO BOT È SOLO PER SCOPI EDUCATIVI E INFORMATIVI**

- **Non è consulenza finanziaria:** I segnali sono basati su analisi tecnica automatizzata
- **Rischi elevati:** Il trading crypto comporta rischi significativi di perdite
- **Responsabilità dell'utente:** Tutte le decisioni di trading sono a tua responsabilità
- **Nessuna garanzia:** Non garantiamo profitti o accuratezza dei segnali
- **Test consigliato:** Inizia con importi piccoli per testare l'efficacia

**Investi solo quello che puoi permetterti di perdere.**

## 📧 Supporto e Contributi

- **Issues:** [GitHub Issues](https://github.com/yourusername/crypto-analyst/issues)
- **Contributi:** Pull requests benvenute!
- **Documentazione:** Wiki disponibile per setup avanzati

## 📜 Licenza

MIT License - Vedi [LICENSE](LICENSE) per dettagli completi.

---

**🚀 Sviluppato con ❤️ per la community crypto italiana**

