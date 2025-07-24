"""
File principale per eseguire il bot su Replit
"""

import os
from dotenv import load_dotenv

# Carica variabili d'ambiente
load_dotenv()

# Importa e avvia il bot
from crypto_bot import main

if __name__ == "__main__":
    main()
