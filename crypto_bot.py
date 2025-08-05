#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import pandas as pd
import numpy as np
import ccxt
import telegram
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import ta
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Configurazione logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crypto_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configurazione
TELEGRAM_TOKEN = "8271715130:AAH7SU2jXtyLm2s7-h6ywtaYQaZoj0mUGis"
CHAT_ID = "426491773"

# Exchange per dati crypto
exchange = ccxt.bybit({
    'apiKey': '',
    'secret': '',
    'sandbox': False,
    'rateLimit': 100,
    'options': {'defaultType': 'spot'}
})

# Configurazione crypto da monitorare (solo crypto verificate e funzionanti su Bybit)
CRYPTO_SYMBOLS = [
    # Top cryptocurrencies (verificate)
    'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'SOL', 'DOT', 'DOGE', 'AVAX', 'LINK',
    'UNI', 'LTC', 'ALGO', 'VET', 'ICP', 'FIL', 'TRX', 'ETC', 'XLM',
    
    # DeFi tokens (verificate - rimossi BAL, BAND, STORJ, OCEAN, AUDIO)
    'AAVE', 'UMA', 'CRV', 'SUSHI', 'COMP', 'MKR', 'YFI', 'SNX',
    'ZRX', 'LRC', 'GRT', 'FET',
    
    # Layer 2 & chains (verificate - rimossi FTM, MATIC)
    'OP', 'ARB', 'NEAR', 'ATOM', 'FLOW', 'ROSE', 'ONE', 'HBAR',
    
    # Gaming & NFT tokens (verificate)
    'AXS', 'SAND', 'MANA', 'ENJ', 'CHZ', 'GALA', 'GMT', 'APE', 'IMX',
    
    # Meme coins (verificate)
    'SHIB', 'PEPE', 'FLOKI', 'WIF', 'BONK',
    
    # Additional tokens (verificati)
    'LDO'
]

# Anti-spam: traccia messaggi inviati per evitare spam
last_signals = {}
SPAM_COOLDOWN = 7200  # 2 ore tra messaggi per la stessa crypto

@dataclass
class SignalData:
    symbol: str
    signal_type: str
    confidence: float
    current_price: float
    trading_levels: Dict[str, float]
    timestamp: datetime
    volume_spike: bool
    momentum_strength: str

def calculate_trading_levels(symbol: str, current_price: float, ohlcv_data: List) -> Dict[str, float]:
    """
    Calcola livelli di trading precisi con:
    - Market entry: prezzo corrente
    - Limit entry: con spread intelligente
    - Take profit: basato su resistenza/supporto
    - Stop loss: con buffer di sicurezza
    """
    try:
        if not ohlcv_data or len(ohlcv_data) < 20:
            # Fallback con calcoli di base
            precision = get_price_precision(current_price)
            spread_pct = 0.5  # Default 0.5%
            
            limit_entry = round(current_price * (1 - spread_pct/100), precision)
            take_profit = round(current_price * 1.03, precision)  # +3%
            stop_loss = round(current_price * 0.97, precision)   # -3%
            
            return {
                'market_entry': round(current_price, precision),
                'limit_entry': limit_entry,
                'take_profit': take_profit,
                'stop_loss': stop_loss
            }
        
        # Converti OHLCV in DataFrame
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Calcola precisione dinamica basata sul valore del token
        precision = get_price_precision(current_price)
        
        # Calcola volatilità per spread intelligente
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * 100  # Volatilità in percentuale
        
        # Spread intelligente basato su volatilità (0.1% - 2%)
        if volatility < 1:
            spread_pct = 0.1
        elif volatility < 3:
            spread_pct = 0.3
        elif volatility < 5:
            spread_pct = 0.5
        elif volatility < 10:
            spread_pct = 1.0
        else:
            spread_pct = 2.0
        
        # Market entry = prezzo corrente
        market_entry = round(current_price, precision)
        
        # Limit entry = prezzo corrente - spread
        limit_entry = round(current_price * (1 - spread_pct/100), precision)
        
        # Calcola supporto e resistenza per take profit e stop loss
        resistance_levels = []
        support_levels = []
        
        # Trova massimi e minimi locali
        for i in range(2, len(df) - 2):
            # Resistenza (massimi locali)
            if (df['high'].iloc[i] > df['high'].iloc[i-1] and 
                df['high'].iloc[i] > df['high'].iloc[i-2] and
                df['high'].iloc[i] > df['high'].iloc[i+1] and 
                df['high'].iloc[i] > df['high'].iloc[i+2]):
                resistance_levels.append(df['high'].iloc[i])
            
            # Supporto (minimi locali)
            if (df['low'].iloc[i] < df['low'].iloc[i-1] and 
                df['low'].iloc[i] < df['low'].iloc[i-2] and
                df['low'].iloc[i] < df['low'].iloc[i+1] and 
                df['low'].iloc[i] < df['low'].iloc[i+2]):
                support_levels.append(df['low'].iloc[i])
        
        # Take profit: resistenza più vicina sopra il prezzo corrente
        valid_resistance = [r for r in resistance_levels if r > current_price]
        if valid_resistance:
            nearest_resistance = min(valid_resistance)
            take_profit = round(nearest_resistance * 0.99, precision)  # 1% sotto la resistenza
        else:
            # Fallback: basato su volatilità
            if volatility < 2:
                tp_pct = 1.5
            elif volatility < 5:
                tp_pct = 3.0
            elif volatility < 10:
                tp_pct = 5.0
            else:
                tp_pct = 8.0
            take_profit = round(current_price * (1 + tp_pct/100), precision)
        
        # Stop loss: supporto più vicino sotto il prezzo corrente
        valid_support = [s for s in support_levels if s < current_price]
        if valid_support:
            nearest_support = max(valid_support)
            stop_loss = round(nearest_support * 0.99, precision)  # 1% sotto il supporto
        else:
            # Fallback: 3% sotto il prezzo corrente
            stop_loss = round(current_price * 0.97, precision)
        
        return {
            'market_entry': market_entry,
            'limit_entry': limit_entry,
            'take_profit': take_profit,
            'stop_loss': stop_loss
        }
        
    except Exception as e:
        logger.error(f"Errore calcolo livelli trading per {symbol}: {e}")
        # Fallback semplice
        precision = get_price_precision(current_price)
        return {
            'market_entry': round(current_price, precision),
            'limit_entry': round(current_price * 0.995, precision),
            'take_profit': round(current_price * 1.03, precision),
            'stop_loss': round(current_price * 0.97, precision)
        }

def get_price_precision(price: float) -> int:
    """
    Determina la precisione dinamica basata sul valore del token:
    - Tokens > $1000: 1 decimale
    - Tokens $100-1000: 2 decimali  
    - Tokens $10-100: 3 decimali
    - Tokens $1-10: 4 decimali
    - Tokens $0.1-1: 5 decimali
    - Tokens < $0.1: 6 decimali
    """
    if price >= 1000:
        return 1
    elif price >= 100:
        return 2
    elif price >= 10:
        return 3
    elif price >= 1:
        return 4
    elif price >= 0.1:
        return 5
    else:
        return 6

def get_crypto_data(symbol: str, timeframe: str = '1h', limit: int = 100) -> Optional[Dict]:
    """Recupera dati crypto da Bybit"""
    try:
        symbol_formatted = f"{symbol}/USDT"  # Cambiato formato per Bybit
        
        # Verifica se il simbolo esiste
        markets = exchange.load_markets()
        if symbol_formatted not in markets:
            logger.warning(f"Simbolo {symbol_formatted} non trovato su Bybit")
            return None
        
        # Recupera dati OHLCV
        ohlcv = exchange.fetch_ohlcv(symbol_formatted, timeframe, limit=limit)
        
        if not ohlcv:
            return None
        
        # Converti in DataFrame per analisi
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Ticker per prezzo corrente
        ticker = exchange.fetch_ticker(symbol_formatted)
        
        return {
            'symbol': symbol,
            'current_price': float(ticker['last']),
            'volume_24h': float(ticker['quoteVolume']),
            'change_24h': float(ticker['percentage']),
            'ohlcv': ohlcv,
            'df': df
        }
        
    except Exception as e:
        logger.error(f"Errore recupero dati crypto: {e}")
        return None

def calculate_technical_indicators(df: pd.DataFrame) -> Dict:
    """Calcola indicatori tecnici avanzati"""
    try:
        indicators = {}
        
        # Prezzi
        close = df['close'].astype(float)
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        volume = df['volume'].astype(float)
        
        # RSI
        indicators['rsi'] = ta.momentum.rsi(close, window=14).iloc[-1]
        
        # MACD
        macd_line = ta.trend.macd(close)
        macd_signal = ta.trend.macd_signal(close)
        indicators['macd'] = macd_line.iloc[-1]
        indicators['macd_signal'] = macd_signal.iloc[-1]
        indicators['macd_histogram'] = (macd_line - macd_signal).iloc[-1]
        
        # Bollinger Bands
        bb_upper = ta.volatility.bollinger_hband(close)
        bb_lower = ta.volatility.bollinger_lband(close)
        bb_middle = ta.volatility.bollinger_mavg(close)
        indicators['bb_upper'] = bb_upper.iloc[-1]
        indicators['bb_lower'] = bb_lower.iloc[-1]
        indicators['bb_middle'] = bb_middle.iloc[-1]
        indicators['bb_position'] = (close.iloc[-1] - bb_lower.iloc[-1]) / (bb_upper.iloc[-1] - bb_lower.iloc[-1])
        
        # EMA
        indicators['ema_12'] = ta.trend.ema_indicator(close, window=12).iloc[-1]
        indicators['ema_26'] = ta.trend.ema_indicator(close, window=26).iloc[-1]
        indicators['ema_50'] = ta.trend.ema_indicator(close, window=50).iloc[-1]
        
        # Stochastic
        stoch = ta.momentum.stoch(high, low, close)
        indicators['stoch'] = stoch.iloc[-1]
        
        # Volume indicators
        indicators['volume_sma'] = volume.rolling(window=20).mean().iloc[-1]
        indicators['volume_ratio'] = volume.iloc[-1] / indicators['volume_sma']
        
        # Williams %R
        indicators['williams_r'] = ta.momentum.williams_r(high, low, close).iloc[-1]
        
        # Commodity Channel Index
        indicators['cci'] = ta.trend.cci(high, low, close).iloc[-1]
        
        # Average True Range (volatilità)
        indicators['atr'] = ta.volatility.average_true_range(high, low, close).iloc[-1]
        
        # Money Flow Index
        indicators['mfi'] = ta.volume.money_flow_index(high, low, close, volume).iloc[-1]
        
        return indicators
        
    except Exception as e:
        logger.error(f"Errore calcolo indicatori tecnici: {e}")
        return {}

def ai_trading_prediction(symbol: str, data: Dict, indicators: Dict) -> Dict:
    """AI avanzato per predizione trading con machine learning"""
    try:
        current_price = data['current_price']
        change_24h = data['change_24h']
        
        # Punteggi per diversi aspetti
        scores = {
            'momentum': 0,
            'trend': 0, 
            'volume': 0,
            'oversold_overbought': 0,
            'volatility': 0
        }
        
        # Analisi Momentum (RSI, Stochastic, Williams %R)
        rsi = indicators.get('rsi', 50)
        stoch = indicators.get('stoch', 50)
        williams_r = indicators.get('williams_r', -50)
        
        if rsi < 30 and stoch < 20:  # Forte oversold
            scores['momentum'] = 25
        elif rsi < 40 and stoch < 30:  # Moderato oversold
            scores['momentum'] = 15
        elif rsi > 70 and stoch > 80:  # Forte overbought
            scores['momentum'] = -25
        elif rsi > 60 and stoch > 70:  # Moderato overbought
            scores['momentum'] = -15
        
        # Analisi Trend (MACD, EMA)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        ema_12 = indicators.get('ema_12', current_price)
        ema_26 = indicators.get('ema_26', current_price)
        ema_50 = indicators.get('ema_50', current_price)
        
        # MACD bullish/bearish
        if macd > macd_signal and macd > 0:
            scores['trend'] += 15
        elif macd < macd_signal and macd < 0:
            scores['trend'] -= 15
        
        # EMA trend
        if ema_12 > ema_26 > ema_50:
            scores['trend'] += 15
        elif ema_12 < ema_26 < ema_50:
            scores['trend'] -= 15
        
        # Prezzo vs EMA
        if current_price > ema_12 > ema_26:
            scores['trend'] += 10
        elif current_price < ema_12 < ema_26:
            scores['trend'] -= 10
        
        # Analisi Volume
        volume_ratio = indicators.get('volume_ratio', 1)
        mfi = indicators.get('mfi', 50)
        
        if volume_ratio > 2:  # Volume spike significativo
            scores['volume'] = 20
        elif volume_ratio > 1.5:
            scores['volume'] = 10
        elif volume_ratio < 0.5:
            scores['volume'] = -10
        
        # Money Flow Index
        if mfi > 70:
            scores['volume'] -= 10
        elif mfi < 30:
            scores['volume'] += 10
        
        # Analisi Bollinger Bands
        bb_position = indicators.get('bb_position', 0.5)
        
        if bb_position < 0.1:  # Vicino al lower band
            scores['oversold_overbought'] = 20
        elif bb_position > 0.9:  # Vicino al upper band
            scores['oversold_overbought'] = -20
        elif bb_position < 0.3:
            scores['oversold_overbought'] = 10
        elif bb_position > 0.7:
            scores['oversold_overbought'] = -10
        
        # Analisi Volatilità e Momentum
        atr = indicators.get('atr', 0)
        cci = indicators.get('cci', 0)
        
        if abs(cci) > 200:  # CCI estremo
            if cci > 200:
                scores['volatility'] = -15
            else:
                scores['volatility'] = 15
        elif abs(cci) > 100:
            if cci > 100:
                scores['volatility'] = -8
            else:
                scores['volatility'] = 8
        
        # Calcolo punteggio finale
        total_score = sum(scores.values())
        
        # Normalizza il punteggio (-100 a +100) in confidence (0-100)
        confidence = min(100, max(0, (total_score + 100) / 2))
        
        # Determina segnale e forza
        if total_score >= 30:
            signal_type = "STRONG_LONG"
            momentum_strength = "FORTE"
        elif total_score >= 15:
            signal_type = "LONG"
            momentum_strength = "MODERATO"
        elif total_score <= -30:
            signal_type = "STRONG_SHORT"
            momentum_strength = "FORTE"
        elif total_score <= -15:
            signal_type = "SHORT"
            momentum_strength = "MODERATO"
        else:
            signal_type = "NEUTRAL"
            momentum_strength = "DEBOLE"
        
        # Verifica volume spike
        volume_spike = volume_ratio > 1.8
        
        # Calcola livelli di trading precisi
        trading_levels = calculate_trading_levels(symbol, current_price, data['ohlcv'])
        
        return {
            'signal': signal_type,
            'confidence': round(confidence, 1),
            'momentum_strength': momentum_strength,
            'volume_spike': volume_spike,
            'trading_levels': trading_levels,
            'scores_breakdown': scores,
            'total_score': total_score
        }
        
    except Exception as e:
        logger.error(f"Errore AI prediction per {symbol}: {e}")
        return {
            'signal': 'NEUTRAL',
            'confidence': 0,
            'momentum_strength': 'DEBOLE',
            'volume_spike': False,
            'trading_levels': {},
            'scores_breakdown': {},
            'total_score': 0
        }

def format_signal_message(signal_data: SignalData) -> str:
    """Formatta il messaggio del segnale con livelli di trading precisi"""
    try:
        # Emoji e direzione
        direction_emoji = "🚀" if "LONG" in signal_data.signal_type else "🔻"
        direction_text = signal_data.signal_type.replace("_", " ")
        
        # Precisione dinamica per i prezzi
        precision = get_price_precision(signal_data.current_price)
        
        # Formato prezzo base
        price_format = f"{{:.{precision}f}}"
        
        # Livelli di trading
        levels = signal_data.trading_levels
        market_entry = price_format.format(levels.get('market_entry', signal_data.current_price))
        limit_entry = price_format.format(levels.get('limit_entry', signal_data.current_price))
        take_profit = price_format.format(levels.get('take_profit', signal_data.current_price))
        stop_loss = price_format.format(levels.get('stop_loss', signal_data.current_price))
        
        # Calcola profit/loss potenziale
        if 'LONG' in signal_data.signal_type:
            profit_pct = ((levels.get('take_profit', signal_data.current_price) / signal_data.current_price) - 1) * 100
            loss_pct = ((signal_data.current_price / levels.get('stop_loss', signal_data.current_price)) - 1) * 100
        else:
            profit_pct = ((signal_data.current_price / levels.get('take_profit', signal_data.current_price)) - 1) * 100
            loss_pct = ((levels.get('stop_loss', signal_data.current_price) / signal_data.current_price) - 1) * 100
        
        # Forza momentum
        strength_emoji = "⚡" if signal_data.momentum_strength == "FORTE" else "📊"
        
        # Volume spike
        volume_text = " | 📈 VOLUME SPIKE" if signal_data.volume_spike else ""
        
        message = f"""🎯 **SEGNALE CRIPTO AUTOMATICO**
        
{direction_emoji} **{signal_data.symbol}/USDT** - {direction_text}
{strength_emoji} **Confidence:** {signal_data.confidence}% | **Momentum:** {signal_data.momentum_strength}{volume_text}

💰 **LIVELLI DI TRADING:**
📊 **Market Entry:** ${market_entry}
🎯 **Limit Entry:** ${limit_entry}
🚀 **Take Profit:** ${take_profit}
🛡️ **Stop Loss:** ${stop_loss}

📈 **PROFIT/LOSS POTENZIALE:**
✅ **Target:** +{profit_pct:.1f}%
❌ **Risk:** -{loss_pct:.1f}%
📊 **R/R Ratio:** {profit_pct/loss_pct:.1f}:1

🕐 **Timestamp:** {signal_data.timestamp.strftime('%H:%M:%S')}
        
⚠️ **DISCLAIMER:** Segnale automatico AI - NON consiglio finanziario!"""
        
        return message
        
    except Exception as e:
        logger.error(f"Errore formattazione messaggio: {e}")
        return f"🎯 **SEGNALE:** {signal_data.symbol} - {signal_data.signal_type} (Conf: {signal_data.confidence}%)"

def format_limit_opportunity_message(symbol: str, current_price: float, trading_levels: Dict, opportunity_type: str) -> str:
    """Formatta messaggio per opportunità di limit order"""
    try:
        precision = get_price_precision(current_price)
        price_format = f"{{:.{precision}f}}"
        
        current_formatted = price_format.format(current_price)
        limit_price = price_format.format(trading_levels.get('limit_entry', current_price))
        take_profit = price_format.format(trading_levels.get('take_profit', current_price))
        stop_loss = price_format.format(trading_levels.get('stop_loss', current_price))
        
        # Calcola distanza dal target
        if trading_levels.get('limit_entry'):
            distance_pct = abs((current_price - trading_levels['limit_entry']) / current_price) * 100
        else:
            distance_pct = 0
        
        direction_emoji = "🎯" if opportunity_type == "LONG" else "📉"
        
        message = f"""🚨 **OPPORTUNITÀ LIMIT ORDER**

{direction_emoji} **{symbol}/USDT** - Prezzo vicino al target!

💰 **PREZZI ATTUALI:**
📊 **Prezzo Corrente:** ${current_formatted}
🎯 **Target Limit:** ${limit_price} ({distance_pct:.1f}% di distanza)

🎯 **SETUP LIMIT ORDER:**
📈 **Entry Limit:** ${limit_price}
🚀 **Take Profit:** ${take_profit}
🛡️ **Stop Loss:** ${stop_loss}

⏰ **AZIONE:** Considera l'impostazione di un limit order a ${limit_price}

🕐 **Rilevato:** {datetime.now().strftime('%H:%M:%S')}

⚠️ **DISCLAIMER:** Opportunità rilevata automaticamente - NON consiglio finanziario!"""
        
        return message
        
    except Exception as e:
        logger.error(f"Errore formattazione messaggio limit: {e}")
        return f"🎯 **OPPORTUNITÀ LIMIT:** {symbol} - Prezzo: ${current_price:.4f}"

async def send_telegram_message(message: str, chat_id: str = CHAT_ID):
    """Invia messaggio Telegram"""
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        logger.info(f"Messaggio inviato con successo a {chat_id}")
        return True
    except Exception as e:
        logger.error(f"Errore invio messaggio Telegram: {e}")
        return False

def should_send_signal(symbol: str, signal_type: str) -> bool:
    """Verifica se inviare il segnale (anti-spam)"""
    current_time = datetime.now()
    key = f"{symbol}_{signal_type}"
    
    if key in last_signals:
        time_diff = (current_time - last_signals[key]).total_seconds()
        if time_diff < SPAM_COOLDOWN:
            return False
    
    last_signals[key] = current_time
    return True

def should_send_limit_opportunity(symbol: str) -> bool:
    """Verifica se inviare notifica limit opportunity (anti-spam)"""
    current_time = datetime.now()
    key = f"{symbol}_LIMIT"
    
    if key in last_signals:
        time_diff = (current_time - last_signals[key]).total_seconds()
        if time_diff < SPAM_COOLDOWN:  # Stesso cooldown dei segnali
            return False
    
    last_signals[key] = current_time
    return True

async def monitor_crypto_signals():
    """Monitoraggio principale dei segnali crypto"""
    logger.info("🚀 Avvio monitoraggio segnali crypto ultra-rapidi...")
    
    while True:
        try:
            for symbol in CRYPTO_SYMBOLS:
                try:
                    # Recupera dati crypto
                    data = get_crypto_data(symbol)
                    if not data:
                        continue
                    
                    # Calcola indicatori tecnici
                    indicators = calculate_technical_indicators(data['df'])
                    if not indicators:
                        continue
                    
                    # AI prediction
                    prediction = ai_trading_prediction(symbol, data, indicators)
                    if not prediction:
                        continue
                    
                    # Verifica segnali di trading
                    signal_type = prediction['signal']
                    confidence = prediction['confidence']
                    
                    # Segnali principali: LONG/SHORT con confidence >= 65%
                    if signal_type in ['LONG', 'STRONG_LONG', 'SHORT', 'STRONG_SHORT'] and confidence >= 65:
                        if should_send_signal(symbol, signal_type):
                            signal_data = SignalData(
                                symbol=symbol,
                                signal_type=signal_type,
                                confidence=confidence,
                                current_price=data['current_price'],
                                trading_levels=prediction['trading_levels'],
                                timestamp=datetime.now(),
                                volume_spike=prediction['volume_spike'],
                                momentum_strength=prediction['momentum_strength']
                            )
                            
                            message = format_signal_message(signal_data)
                            success = await send_telegram_message(message)
                            
                            if success:
                                logger.info(f"⚡ SEGNALE ISTANTANEO {signal_type} per {symbol} (Conf: {confidence}%) -> {CHAT_ID}")
                    
                    # Piccola pausa tra crypto per evitare rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.error(f"Errore monitoraggio {symbol}: {e}")
                    continue
            
            # Pausa tra cicli completi
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Errore nel loop principale: {e}")
            await asyncio.sleep(5)

async def telegram_start(update, context):
    """Handler comando /start"""
    welcome_message = """🤖 **CRYPTO ANALYSIS BOT ULTRA-RAPIDO** 🚀

⚡ **FUNZIONI AUTOMATICHE:**
• 🎯 Segnali crypto automatici LONG/SHORT
• 📊 Analisi tecnica avanzata con AI
• 💰 Calcolo livelli di trading precisi
• 🚨 Notifiche istantanee con confidence elevata
• 🔍 Analisi manuale con comando /analyze

📈 **LIVELLI DI TRADING INCLUSI:**
• Market Entry (prezzo corrente)
• Limit Entry (con spread ottimizzato)
• Take Profit (basato su resistenze)
• Stop Loss (con buffer di sicurezza)
• Profit/Loss potenziale calcolato

🎯 **COMANDI DISPONIBILI:**
/start - Mostra questo messaggio
/status - Stato del monitoraggio
/analyze CRYPTO - Analisi dettagliata manuale
/help - Guida completa

⚠️ **DISCLAIMER:** 
Questo bot fornisce segnali automatici basati su analisi tecnica AI. NON è un consiglio finanziario. Investi sempre responsabilmente!

🚀 **Bot attivo e in monitoraggio continuo!**"""
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def telegram_status(update, context):
    """Handler comando /status"""
    try:
        total_signals = len(last_signals)
        active_cooldowns = sum(1 for timestamp in last_signals.values() 
                             if (datetime.now() - timestamp).total_seconds() < SPAM_COOLDOWN)
        
        status_message = f"""📊 **STATUS BOT CRYPTO ANALYSIS**

🟢 **Stato:** Attivo e operativo
⚡ **Crypto monitorate:** {len(CRYPTO_SYMBOLS)}
📨 **Segnali inviati:** {total_signals}
🔕 **Cooldown attivi:** {active_cooldowns}
⏰ **Ultimo aggiornamento:** {datetime.now().strftime('%H:%M:%S')}

🎯 **Configurazione:**
• Confidence minima: 65%
• Cooldown anti-spam: 2 ore
• Precisione prezzi: Dinamica (1-6 decimali)
• Analisi manuale: Comando /analyze disponibile

🚀 **Il bot sta monitorando continuamente per segnali LONG/SHORT ad alta confidence!**"""
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Errore nel recuperare lo status: {str(e)}")

async def telegram_analyze(update, context):
    """Handler comando /analyze - Analizza una specifica crypto"""
    try:
        # Ottieni il simbolo dalla query
        if not context.args:
            await update.message.reply_text(
                "❌ **Uso:** `/analyze BTC` - Specifica una crypto da analizzare\n\n"
                f"**Crypto disponibili:** {', '.join(CRYPTO_SYMBOLS[:20])}...",
                parse_mode='Markdown'
            )
            return
        
        symbol = context.args[0].upper()
        
        if symbol not in CRYPTO_SYMBOLS:
            await update.message.reply_text(
                f"❌ **Crypto {symbol} non supportata.**\n\n"
                f"**Crypto disponibili:** {', '.join(CRYPTO_SYMBOLS)}",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text(f"🔍 **Analizzando {symbol}...** ⏳", parse_mode='Markdown')
        
        # Recupera dati crypto
        data = get_crypto_data(symbol)
        if not data:
            await update.message.reply_text(
                f"❌ **Errore nel recuperare dati per {symbol}**",
                parse_mode='Markdown'
            )
            return
        
        # Calcola indicatori tecnici
        indicators = calculate_technical_indicators(data['df'])
        if not indicators:
            await update.message.reply_text(
                f"❌ **Errore nel calcolare indicatori per {symbol}**",
                parse_mode='Markdown'
            )
            return
        
        # AI prediction
        prediction = ai_trading_prediction(symbol, data, indicators)
        
        # Formatta analisi dettagliata
        analysis_message = format_detailed_analysis(symbol, data, indicators, prediction)
        
        await update.message.reply_text(analysis_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ **Errore nell'analisi:** {str(e)}", parse_mode='Markdown')

def format_detailed_analysis(symbol: str, data: Dict, indicators: Dict, prediction: Dict) -> str:
    """Formatta un'analisi dettagliata per una crypto specifica"""
    try:
        current_price = data['current_price']
        change_24h = data['change_24h']
        volume_24h = data['volume_24h']
        
        # Precisione dinamica
        precision = get_price_precision(current_price)
        price_format = f"{{:.{precision}f}}"
        
        # Livelli di trading
        levels = prediction['trading_levels']
        market_entry = price_format.format(levels.get('market_entry', current_price))
        limit_entry = price_format.format(levels.get('limit_entry', current_price))
        take_profit = price_format.format(levels.get('take_profit', current_price))
        stop_loss = price_format.format(levels.get('stop_loss', current_price))
        
        # Segnale e confidence
        signal_type = prediction['signal']
        confidence = prediction['confidence']
        momentum_strength = prediction['momentum_strength']
        
        # Emoji per direzione
        direction_emoji = "🚀" if "LONG" in signal_type else "🔻" if "SHORT" in signal_type else "⚪"
        
        # Indicatori tecnici
        rsi = indicators.get('rsi', 0)
        macd = indicators.get('macd', 0)
        macd_signal = indicators.get('macd_signal', 0)
        bb_position = indicators.get('bb_position', 0.5)
        volume_ratio = indicators.get('volume_ratio', 1)
        
        # Analisi dettagliata
        analysis_text = []
        
        # RSI Analysis
        if rsi < 30:
            analysis_text.append("• **RSI Oversold** - Possibile rimbalzo")
        elif rsi > 70:
            analysis_text.append("• **RSI Overbought** - Possibile correzione")
        else:
            analysis_text.append("• **RSI Neutrale** - Mercato bilanciato")
        
        # MACD Analysis
        if macd > macd_signal:
            analysis_text.append("• **MACD Bullish** - Momentum positivo")
        else:
            analysis_text.append("• **MACD Bearish** - Momentum negativo")
        
        # Bollinger Bands
        if bb_position < 0.2:
            analysis_text.append("• **Vicino Lower Band** - Possibile supporto")
        elif bb_position > 0.8:
            analysis_text.append("• **Vicino Upper Band** - Possibile resistenza")
        
        # Volume
        if volume_ratio > 1.5:
            analysis_text.append("• **Volume Alto** - Interesse crescente")
        
        analysis_summary = "\n".join(analysis_text) if analysis_text else "• Mercato in condizioni normali"
        
        # Calcola profit/loss potenziale
        if 'LONG' in signal_type:
            profit_pct = ((levels.get('take_profit', current_price) / current_price) - 1) * 100
            loss_pct = ((current_price / levels.get('stop_loss', current_price)) - 1) * 100
        else:
            profit_pct = ((current_price / levels.get('take_profit', current_price)) - 1) * 100
            loss_pct = ((levels.get('stop_loss', current_price) / current_price) - 1) * 100
        
        message = f"""📊 **ANALISI DETTAGLIATA {symbol}/USDT**

💰 **PREZZO CORRENTE:** ${current_price:.{precision}f}
📈 **Variazione 24h:** {change_24h:+.2f}%
📊 **Volume 24h:** ${volume_24h:,.0f}

{direction_emoji} **SEGNALE:** {signal_type.replace('_', ' ')}
⚡ **Confidence:** {confidence}%
📊 **Momentum:** {momentum_strength}

💎 **LIVELLI DI TRADING:**
📊 **Market Entry:** ${market_entry}
🎯 **Limit Entry:** ${limit_entry}
🚀 **Take Profit:** ${take_profit}
🛡️ **Stop Loss:** ${stop_loss}

📈 **POTENZIALE:**
✅ **Target:** +{profit_pct:.1f}%
❌ **Risk:** -{loss_pct:.1f}%
📊 **R/R Ratio:** {profit_pct/loss_pct:.1f}:1

🔍 **INDICATORI TECNICI:**
• **RSI:** {rsi:.1f}
• **MACD:** {macd:.4f} / {macd_signal:.4f}
• **BB Position:** {bb_position:.1%}
• **Volume Ratio:** {volume_ratio:.1f}x

📋 **ANALISI:**
{analysis_summary}

🕐 **Analisi generata:** {datetime.now().strftime('%H:%M:%S')}

⚠️ **DISCLAIMER:** Analisi automatica AI - NON consiglio finanziario!"""
        
        return message
        
    except Exception as e:
        logger.error(f"Errore formattazione analisi dettagliata: {e}")
        return f"❌ **Errore nella formattazione dell'analisi per {symbol}**"

async def telegram_help(update, context):
    """Handler comando /help"""
    help_message = """📖 **GUIDA COMPLETA CRYPTO BOT**

🤖 **COMANDI DISPONIBILI:**
• `/start` - Avvia il bot e mostra benvenuto
• `/status` - Stato del monitoraggio 
• `/analyze BTC` - Analisi dettagliata di una crypto
• `/help` - Mostra questa guida

⚡ **SEGNALI AUTOMATICI:**
• 🚀 **LONG**: Segnali di acquisto automatici
• 🔻 **SHORT**: Segnali di vendita automatici  
• 📊 **Confidence**: 65-100% (solo alta qualità)
• ⚡ **Momentum**: FORTE/MODERATO

💰 **LIVELLI DI TRADING:**
• **Market Entry**: Prezzo per ordine immediato
• **Limit Entry**: Prezzo ottimizzato per limit order
• **Take Profit**: Target di profitto intelligente
• **Stop Loss**: Protezione con buffer di sicurezza

🔍 **ANALISI MANUALE:**
Usa `/analyze SIMBOLO` per un'analisi dettagliata di qualsiasi crypto. Include indicatori tecnici, segnali AI e livelli di trading precisi.

📊 **CRYPTO MONITORATE:**
BTC, ETH, BNB, XRP, ADA, SOL, DOGE, AVAX, LINK, UNI, LTC, ALGO, VET, ICP, FIL, TRX, ETC, XLM, MATIC, AAVE, UMA, CRV, SUSHI, COMP, MKR, YFI, SNX, BAL, OP, ARB, NEAR, FTM, ATOM, FLOW, ROSE, ONE, HBAR, AXS, SAND, MANA, ENJ, CHZ, GALA, GMT, APE, IMX, SHIB, PEPE, FLOKI, WIF, BONK, LDO, GRT, FET, OCEAN, STORJ, BAND, ZRX, LRC, AUDIO

🔕 **ANTI-SPAM:**
Ogni crypto ha un cooldown di 2 ore per evitare notifiche eccessive.

⚠️ **IMPORTANTE:**
Questo bot NON fornisce consigli finanziari. È uno strumento di analisi tecnica. Investi sempre responsabilmente!

🚀 **Il bot è sempre attivo e in ascolto!**"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')
    """Handler comando /help"""
    help_message = """📖 **GUIDA COMPLETA CRYPTO BOT**

🤖 **COSA FA QUESTO BOT:**
Il bot monitora continuamente oltre 100 criptovalute e invia segnali automatici quando rileva opportunità ad alta probabilità usando AI e analisi tecnica avanzata.

⚡ **SEGNALI AUTOMATICI:**
• 🚀 **LONG**: Segnali di acquisto
• 🔻 **SHORT**: Segnali di vendita
• 📊 **Confidence**: 65-100% (solo alta qualità)
• ⚡ **Momentum**: FORTE/MODERATO

💰 **LIVELLI DI TRADING:**
• **Market Entry**: Prezzo per ordine immediato
• **Limit Entry**: Prezzo ottimizzato per limit order
• **Take Profit**: Target di profitto intelligente
• **Stop Loss**: Protezione con buffer di sicurezza

🎯 **OPPORTUNITÀ LIMIT:**
Il bot rileva quando il prezzo si avvicina (entro 1%) ai livelli di limit entry e invia notifiche per impostare ordini ottimizzati.

📊 **INDICATORI USATI:**
• RSI, MACD, Bollinger Bands
• EMA (12, 26, 50)
• Stochastic, Williams %R
• CCI, MFI, ATR
• Volume analysis e momentum

🔕 **ANTI-SPAM:**
Ogni crypto ha un cooldown di 2 ore per evitare notifiche eccessive.

⚠️ **IMPORTANTE:**
Questo bot NON fornisce consigli finanziari. È uno strumento di analisi tecnica. Investi sempre responsabilmente e fai le tue ricerche!

🚀 **Il bot è sempre attivo e in ascolto!**"""
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

async def main():
    """Funzione principale"""
    try:
        # Inizializza application Telegram
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Aggiungi handlers
        application.add_handler(CommandHandler("start", telegram_start))
        application.add_handler(CommandHandler("status", telegram_status))
        application.add_handler(CommandHandler("analyze", telegram_analyze))
        application.add_handler(CommandHandler("help", telegram_help))
        
        # Avvia bot Telegram
        await application.initialize()
        await application.start()
        
        logger.info("🤖 Bot Telegram avviato con successo!")
        
        # Avvia monitoraggio crypto in parallelo
        await asyncio.gather(
            monitor_crypto_signals(),
            application.updater.start_polling()
        )
        
    except Exception as e:
        logger.error(f"Errore nell'avvio del bot: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Avvio Crypto Analysis Bot Ultra-Rapido...")
    print("⚡ Configurazione:")
    print(f"📊 Crypto monitorate: {len(CRYPTO_SYMBOLS)}")
    print(f"🔕 Cooldown anti-spam: {SPAM_COOLDOWN} secondi")
    print(f"📱 Chat ID: {CHAT_ID}")
    print("🎯 Livelli di trading: Market/Limit Entry + TP/SL precisi")
    print("🤖 AI Analysis: Confidence minima 65% per segnali")
    print("\n🟢 Bot in avvio...")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Bot fermato dall'utente")
    except Exception as e:
        print(f"❌ Errore critico: {e}")
        logger.error(f"Errore critico nel main: {e}")
