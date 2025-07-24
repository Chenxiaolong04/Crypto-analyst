@echo off
echo 🤖 Avvio Bot Telegram Analisi Crypto
echo ====================================

REM Controlla se esiste file .env
if not exist .env (
    echo ❌ ERRORE: File .env non trovato!
    echo.
    echo 📋 Per configurare il bot:
    echo 1. Copia .env.example in .env
    echo 2. Modifica .env con il tuo token Telegram
    echo 3. Ottieni token da @BotFather su Telegram
    echo.
    pause
    exit /b 1
)

REM Avvia il bot
echo ✅ File .env trovato, avvio bot...
echo.
.venv\Scripts\python.exe crypto_bot.py
pause
