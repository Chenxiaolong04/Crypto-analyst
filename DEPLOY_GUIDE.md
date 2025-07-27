# 🚀 Deploy del Bot Crypto su Render.com (GRATUITO)

## Preparazione Repository

1. **Assicurati che tutti i file siano su GitHub:**
   - `crypto_bot.py` - Il bot principale
   - `requirements.txt` - Dipendenze Python
   - `Procfile` - Comando di avvio per Render
   - `runtime.txt` - Versione Python
   - `.env` - Variabili d'ambiente (NON includere nel repository!)

## Deploy su Render.com

### Passo 1: Crea Account su Render
1. Vai su [render.com](https://render.com)
2. Registrati gratuitamente con GitHub
3. Autorizza Render ad accedere ai tuoi repository

### Passo 2: Crea un Web Service
1. Clicca su "New" > "Web Service"
2. Connetti il repository GitHub `Crypto-analyst`
3. Configura:
   - **Name:** `crypto-analysis-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python crypto_bot.py`

### Passo 3: Configura Variabili d'Ambiente
Nella sezione "Environment Variables" aggiungi:

```
TELEGRAM_BOT_TOKEN = 8271715130:AAH7SU2jXtyLm2s7-h6ywtaYQaZoj0mUGis
CRYPTOPANIC_TOKEN = il_tuo_token_cryptopanic_qui (opzionale)
DEBUG_MODE = false
LOG_LEVEL = INFO
```

⚠️ **IMPORTANTE:** NON includere mai il file `.env` nel repository GitHub!

### Passo 4: Deploy
1. Clicca "Create Web Service"
2. Render inizierà automaticamente il build e deploy
3. Il processo richiede 5-10 minuti

## ✅ Vantaggi del Deploy su Render

- **Gratuito:** 750 ore/mese gratis (sufficienti per uso continuo)
- **24/7 Uptime:** Il bot resta sempre attivo
- **Auto-restart:** Si riavvia automaticamente in caso di crash
- **HTTPS:** Sicurezza inclusa
- **Logs:** Monitoring e debug integrati

## 🔧 Alternative Gratuite

### 1. **Railway.app**
- 500 ore/mese gratis
- Deploy simile a Render
- Ottima per principianti

### 2. **Heroku** (limitato)
- Solo 550 ore/mese gratis
- Va in "sleep" dopo 30 min di inattività

### 3. **PythonAnywhere** 
- Always-on tasks a pagamento
- Console gratuita con limitazioni

## 📱 Test del Bot

Dopo il deploy:
1. Il bot sarà attivo 24/7
2. Testa con `/start` su Telegram
3. Prova `/btc` e `/crypto ETH`
4. Verifica i logs su Render per debug

## 🔄 Aggiornamenti

Per aggiornare il bot:
1. Fai push delle modifiche su GitHub
2. Render rileverà automaticamente i cambiamenti
3. Farà un nuovo deploy automaticamente

## 🆘 Troubleshooting

- **Bot non risponde:** Controlla i logs su Render
- **Errori API:** Verifica le variabili d'ambiente
- **Deploy fallito:** Controlla `requirements.txt` e `Procfile`

## 💰 Costi

- **Render Free:** 750 ore/mese (più che sufficienti)
- **Dopo le ore gratuite:** $7/mese per unlimited
- **Alternative:** Tutte le piattaforme offrono piani gratuiti adeguati

Il bot sarà accessibile 24/7 senza bisogno di tenere acceso il tuo computer! 🎉
