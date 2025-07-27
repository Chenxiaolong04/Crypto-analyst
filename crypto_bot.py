"""
Bot Telegram per Analisi Crypto Dettagliata
Funzionalità: prezzi real-time, indicatori tecnici, news, grafici
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
import pandas as pd
from dotenv import load_dotenv

# Carica variabili d'ambiente dal file .env
load_dotenv()
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import io
import requests
import ccxt
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
import warnings
warnings.filterwarnings('ignore')

# Configurazione logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Funzioni per indicatori tecnici
def calculate_rsi(prices, window=14):
    """Calcola RSI (Relative Strength Index)"""
    try:
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    except:
        return pd.Series([50] * len(prices), index=prices.index)

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Calcola MACD (Moving Average Convergence Divergence)"""
    try:
        exp1 = prices.ewm(span=fast).mean()
        exp2 = prices.ewm(span=slow).mean()
        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal).mean()
        macd_histogram = macd - macd_signal
        
        return {
            'MACD': macd,
            'Signal': macd_signal,
            'Histogram': macd_histogram
        }
    except:
        return {
            'MACD': pd.Series([0] * len(prices), index=prices.index),
            'Signal': pd.Series([0] * len(prices), index=prices.index),
            'Histogram': pd.Series([0] * len(prices), index=prices.index)
        }

def calculate_sma(prices, window):
    """Calcola Simple Moving Average"""
    return prices.rolling(window=window).mean()

class CryptoAnalysisBot:
    def __init__(self, telegram_token: str, cryptopanic_token: str = None):
        self.telegram_token = telegram_token
        self.cryptopanic_token = cryptopanic_token
        
        # Inizializza exchange Binance
        self.exchange = ccxt.binance({
            'apiKey': '',  # Non necessario per dati pubblici
            'secret': '',
            'timeout': 30000,
            'enableRateLimit': True,
        })
    
    async def get_crypto_data(self, symbol: str) -> dict:
        """Recupera dati crypto da Binance"""
        try:
            # Assicurati che il simbolo sia in formato USDT
            if not symbol.endswith('USDT'):
                symbol = f"{symbol.upper()}USDT"
            
            # Ottieni ticker per prezzo e variazione 24h
            ticker = self.exchange.fetch_ticker(symbol)
            
            # Ottieni candlestick data per analisi tecnica (1 ora, ultimi 100 candles)
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=100)
            
            # Crea DataFrame per analisi tecnica
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return {
                'symbol': symbol,
                'price': ticker['last'],
                'change_24h': ticker['percentage'],
                'volume_24h': ticker['quoteVolume'],
                'high_24h': ticker['high'],
                'low_24h': ticker['low'],
                'df': df
            }
        except Exception as e:
            logger.error(f"Errore recupero dati crypto: {e}")
            raise
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> dict:
        """Calcola indicatori tecnici"""
        try:
            # RSI (14 periodi)
            rsi_series = calculate_rsi(df['close'], 14)
            rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50
            
            # MACD
            macd_data = calculate_macd(df['close'])
            macd = macd_data['MACD'].iloc[-1] if not pd.isna(macd_data['MACD'].iloc[-1]) else 0
            macd_signal = macd_data['Signal'].iloc[-1] if not pd.isna(macd_data['Signal'].iloc[-1]) else 0
            macd_histogram = macd_data['Histogram'].iloc[-1] if not pd.isna(macd_data['Histogram'].iloc[-1]) else 0
            
            # Volume medio
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            return {
                'rsi': round(rsi, 1),
                'macd': round(macd, 6),
                'macd_signal': round(macd_signal, 6),
                'macd_histogram': round(macd_histogram, 6),
                'volume_ratio': round(volume_ratio, 2)
            }
        except Exception as e:
            logger.error(f"Errore calcolo indicatori: {e}")
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0,
                'volume_ratio': 1.0
            }
    
    def generate_technical_suggestions(self, indicators: dict, price_data: dict) -> str:
        """Genera suggerimenti tecnici basati su indicatori"""
        suggestions = []
        
        # Analisi RSI
        rsi = indicators.get('rsi', 50)
        if rsi > 70:
            suggestions.append("🔴 RSI in zona di ipercomprato - possibile correzione")
        elif rsi < 30:
            suggestions.append("🟢 RSI in zona di ipervenduto - possibile rimbalzo")
        else:
            suggestions.append("🟡 RSI in zona neutra")
        
        # Analisi MACD
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        if macd > macd_signal:
            suggestions.append("📈 MACD sopra signal line - trend rialzista")
        else:
            suggestions.append("📉 MACD sotto signal line - trend ribassista")
        
        # Analisi Volume
        volume_ratio = indicators.get('volume_ratio', 1)
        if volume_ratio > 1.5:
            suggestions.append("📊 Volume elevato - movimento significativo")
        elif volume_ratio < 0.5:
            suggestions.append("📊 Volume basso - movimento poco convincente")
        
        return " | ".join(suggestions)
    
    async def get_crypto_news(self, symbol: str) -> list:
        """Recupera news da CryptoPanic API"""
        try:
            if not self.cryptopanic_token:
                # Fallback a news generiche se no API key
                return [
                    {
                        'title': 'CoinDesk - Latest Crypto News',
                        'url': 'https://www.coindesk.com/'
                    },
                    {
                        'title': 'CoinTelegraph - Crypto Updates', 
                        'url': 'https://cointelegraph.com/'
                    },
                    {
                        'title': 'CryptoPanic - Market News',
                        'url': 'https://cryptopanic.com/'
                    }
                ]
            
            # Rimuovi USDT dal simbolo per la ricerca news
            clean_symbol = symbol.replace('USDT', '').lower()
            
            url = f"https://cryptopanic.com/api/v1/posts/"
            params = {
                'auth_token': self.cryptopanic_token,
                'currencies': clean_symbol,
                'filter': 'hot',
                'public': 'true'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                news = []
                for article in data.get('results', [])[:3]:
                    news.append({
                        'title': article.get('title', 'No title'),
                        'url': article.get('url', 'https://cryptopanic.com/')
                    })
                return news
            else:
                raise Exception(f"API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Errore recupero news: {e}")
            # Fallback news
            return [
                {
                    'title': f'{symbol} Market Analysis - CoinDesk',
                    'url': 'https://www.coindesk.com/'
                },
                {
                    'title': f'{symbol} Price Prediction - CoinTelegraph',
                    'url': 'https://cointelegraph.com/'
                },
                {
                    'title': f'{symbol} Technical Analysis - TradingView',
                    'url': 'https://www.tradingview.com/'
                }
            ]
    
    def create_chart(self, df: pd.DataFrame, symbol: str, indicators: dict) -> io.BytesIO:
        """Genera grafico candlestick con indicatori"""
        try:
            # Setup del grafico
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), 
                                               gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # Prendi solo ultimi 50 candles per leggibilità
            df_chart = df.tail(50).copy()
            
            # Grafico Candlestick principale
            for idx, (timestamp, row) in enumerate(df_chart.iterrows()):
                color = 'green' if row['close'] > row['open'] else 'red'
                # Body della candela
                body_height = abs(row['close'] - row['open'])
                body_bottom = min(row['open'], row['close'])
                
                ax1.add_patch(Rectangle((idx-0.3, body_bottom), 0.6, body_height, 
                                      facecolor=color, alpha=0.8))
                
                # Ombre (high/low)
                ax1.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=1)
            
            ax1.set_title(f'{symbol} - Analisi Tecnica', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Prezzo (USDT)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            
            # RSI subplot
            rsi_data = calculate_rsi(df_chart['close'], 14)
            ax2.plot(range(len(rsi_data)), rsi_data, 'purple', linewidth=2)
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Ipercomprato')
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Ipervenduto')
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
            # MACD subplot
            macd_data = calculate_macd(df_chart['close'])
            ax3.plot(range(len(macd_data['MACD'])), macd_data['MACD'], 'blue', label='MACD', linewidth=2)
            ax3.plot(range(len(macd_data['Signal'])), macd_data['Signal'], 'red', label='Signal', linewidth=2)
            ax3.bar(range(len(macd_data['Histogram'])), macd_data['Histogram'], alpha=0.3, label='Histogram')
            ax3.set_ylabel('MACD', fontsize=12)
            ax3.set_xlabel('Tempo (ore)', fontsize=12)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Salva in buffer
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            logger.error(f"Errore creazione grafico: {e}")
            # Grafico semplificato in caso di errore
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(df.tail(50)['close'])
            ax.set_title(f'{symbol} - Prezzo')
            ax.set_ylabel('Prezzo (USDT)')
            ax.grid(True)
            
            buffer = io.BytesIO()
            plt.savefig(buffer, format='png', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer
    
    def format_message(self, crypto_data: dict, indicators: dict, news: list, suggestions: str) -> str:
        """Formatta il messaggio di risposta"""
        symbol = crypto_data['symbol']
        price = crypto_data['price']
        change_24h = crypto_data['change_24h']
        volume_24h = crypto_data['volume_24h']
        
        # Emoji per variazione
        change_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "🟡"
        change_sign = "+" if change_24h > 0 else ""
        
        message = f"""📊 **Analisi {symbol}** (Binance)

💰 **Prezzo attuale:** ${price:,.2f}
{change_emoji} **Variazione 24h:** {change_sign}{change_24h:.2f}%
📈 **Volume 24h:** ${volume_24h:,.0f}

📋 **Indicatori Tecnici:**
• RSI (14): {indicators.get('rsi', 'N/A')} {self._get_rsi_zone(indicators.get('rsi', 50))}
• MACD: {indicators.get('macd', 'N/A'):.6f}
• MACD Signal: {indicators.get('macd_signal', 'N/A'):.6f}
• Volume Ratio: {indicators.get('volume_ratio', 'N/A')}x

💡 **Analisi Tecnica:**
{suggestions}

📰 **Notizie Recenti:**"""

        # Aggiungi news
        for i, article in enumerate(news, 1):
            message += f"\n• [{article['title']}]({article['url']})"
        
        message += f"\n\n📈 **Grafico tecnico allegato**\n⏰ Aggiornato: {datetime.now().strftime('%H:%M:%S')}"
        
        return message
    
    def _get_rsi_zone(self, rsi: float) -> str:
        """Determina zona RSI"""
        if rsi > 70:
            return "→ 🔴 Ipercomprato"
        elif rsi < 30:
            return "→ 🟢 Ipervenduto"
        else:
            return "→ 🟡 Neutro"
    
    async def btc_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /btc per analisi Bitcoin"""
        await self.crypto_analysis('BTC', update, context)
    
    async def crypto_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /crypto <simbolo> per analisi crypto specifica"""
        if not context.args:
            await update.message.reply_text(
                "❌ Uso corretto: /crypto <simbolo>\nEsempio: /crypto ETH"
            )
            return
        
        symbol = context.args[0].upper()
        await self.crypto_analysis(symbol, update, context)
    
    async def crypto_analysis(self, symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Funzione principale per analisi crypto"""
        try:
            # Messaggio di attesa
            waiting_msg = await update.message.reply_text(f"🔄 Analizzando {symbol}...")
            
            # Recupera dati crypto
            crypto_data = await self.get_crypto_data(symbol)
            
            # Calcola indicatori tecnici
            indicators = self.calculate_technical_indicators(crypto_data['df'])
            
            # Genera suggerimenti
            suggestions = self.generate_technical_suggestions(indicators, crypto_data)
            
            # Recupera news
            news = await self.get_crypto_news(symbol)
            
            # Genera grafico
            chart_buffer = self.create_chart(crypto_data['df'], symbol, indicators)
            
            # Formatta messaggio
            message = self.format_message(crypto_data, indicators, news, suggestions)
            
            # Elimina messaggio di attesa
            await waiting_msg.delete()
            
            # Invia risposta con grafico
            await update.message.reply_photo(
                photo=InputFile(chart_buffer, filename=f"{symbol}_analysis.png"),
                caption=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Errore analisi {symbol}: {e}")
            await update.message.reply_text(
                f"❌ Errore nell'analisi di {symbol}. "
                f"Verifica che il simbolo sia corretto (es. BTC, ETH, ADA)"
            )
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /start"""
        message = """🤖 **Bot Analisi Crypto** 

Comandi disponibili:
• `/btc` - Analisi completa Bitcoin
• `/crypto <simbolo>` - Analisi crypto specifica

**Funzionalità:**
📊 Prezzo real-time e variazioni 24h
📈 Indicatori tecnici (RSI, MACD)
📰 Ultime notizie con link
📊 Grafici candlestick professionali
💡 Suggerimenti di trading

**Esempi:**
`/crypto ETH` - Analisi Ethereum
`/crypto ADA` - Analisi Cardano
`/crypto SOL` - Analisi Solana

⚠️ **Disclaimer:** Questo bot fornisce solo informazioni educative. Non costituisce consulenza finanziaria."""

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        await self.start_command(update, context)
    
    def run(self):
        """Avvia il bot"""
        # Crea applicazione con timeouts configurati
        application = Application.builder().token(self.telegram_token).build()
        
        # Aggiungi handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("btc", self.btc_command))
        application.add_handler(CommandHandler("crypto", self.crypto_command))
        
        # Avvia bot con gestione errori
        logger.info("🚀 Bot avviato!")
        try:
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True  # Scarta aggiornamenti pendenti per evitare conflitti
            )
        except Exception as e:
            logger.error(f"Errore durante l'esecuzione del bot: {e}")
            # Prova a riavviare dopo 5 secondi
            import time
            time.sleep(5)
            logger.info("Tentativo di riavvio del bot...")
            self.run()

def main():
    """Funzione principale"""
    # Leggi token da variabili d'ambiente
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    cryptopanic_token = os.getenv('CRYPTOPANIC_TOKEN')  # Opzionale
    
    if not telegram_token:
        print("❌ ERRORE: Imposta la variabile TELEGRAM_BOT_TOKEN")
        print("Come ottenere il token:")
        print("1. Vai su https://t.me/BotFather")
        print("2. Crea un nuovo bot con /newbot")
        print("3. Copia il token e impostalo come variabile d'ambiente")
        return
    
    # Crea e avvia bot
    bot = CryptoAnalysisBot(telegram_token, cryptopanic_token)
    bot.run()

if __name__ == "__main__":
    main()
