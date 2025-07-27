"""
File principale per eseguire il bot su Replit
"""

import os
import logging
import re
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Carica variabili d'ambiente
load_dotenv()

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def validate_telegram_token(token):
    """Valida il formato del token Telegram"""
    if not token:
        return False, "Token mancante nel file .env"
    
    # Formato token Telegram: XXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
    pattern = r'^\d{8,10}:[A-Za-z0-9_-]{35}$'
    if not re.match(pattern, token):
        return False, "Formato token non valido. Dovrebbe essere: XXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
    
    return True, "Token valido"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start"""
    await update.message.reply_text(
        "🚀 Benvenuto nel Bot di Analisi Crypto!\n\n"
        "Comandi disponibili:\n"
        "• /btc - Analisi Bitcoin\n"
        "• /crypto <simbolo> - Analisi criptovaluta\n"
        "• /help - Mostra questo messaggio"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /help"""
    await update.message.reply_text(
        "📊 Bot Analisi Crypto\n\n"
        "Comandi:\n"
        "• /start - Messaggio di benvenuto\n"
        "• /btc - Analisi completa Bitcoin\n"
        "• /crypto BTC - Analisi per simbolo\n"
        "• /help - Mostra questo messaggio\n\n"
        "Esempio: /crypto ETH"
    )

def main():
    """Funzione principale"""
    # Ottieni token da variabili d'ambiente
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    # Valida token
    is_valid, message = validate_telegram_token(token)
    if not is_valid:
        logger.error(f"❌ Errore token: {message}")
        print(f"❌ ERRORE: {message}")
        print("\n🔧 Soluzioni:")
        print("1. Verifica che il file .env contenga TELEGRAM_BOT_TOKEN")
        print("2. Ottieni un nuovo token da @BotFather su Telegram")
        print("3. Assicurati che il formato sia: XXXXXXXXX:XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")
        return
    
    logger.info("✅ Token Telegram valido")
    print("✅ Token validato con successo")
    
    try:
        # Crea applicazione
        application = Application.builder().token(token).build()
        
        # Aggiungi handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        
        # Avvia bot
        logger.info("🤖 Bot avviato...")
        print("🤖 Bot avviato! Premi Ctrl+C per fermare")
        application.run_polling()
        
    except Exception as e:
        logger.error(f"❌ Errore nell'avvio del bot: {e}")
        print(f"❌ Errore: {e}")
        print("\n🔧 Possibili soluzioni:")
        print("1. Verifica la connessione internet")
        print("2. Controlla che il token sia attivo su @BotFather")
        print("3. Riavvia il bot")

if __name__ == '__main__':
    main()
