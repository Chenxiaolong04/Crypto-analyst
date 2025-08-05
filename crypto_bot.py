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
    trading_levels: Dict[str, Any]  # Cambiato da Dict[str, float] per includere più info
    timestamp: datetime
    volume_spike: bool
    momentum_strength: str
    leverage_info: Dict[str, Any] = None  # Informazioni leva
    volatility: float = 0.0  # Volatilità del mercato
    anti_fomo_triggered: bool = False  # Flag anti-FOMO

def calculate_optimal_leverage(confidence: float, volatility: float, signal_strength: str) -> Dict[str, Any]:
    """
    Calcola la leva ottimale per scalping basata su:
    - Confidence del segnale
    - Volatilità del mercato
    - Forza del segnale
    """
    try:
        # Base leverage calculation
        if confidence >= 85 and volatility < 2 and signal_strength in ["STRONG_LONG", "STRONG_SHORT"]:
            leverage = 20  # Alta leva per segnali molto forti e bassa volatilità
            risk_level = "MEDIUM"
        elif confidence >= 80 and volatility < 3:
            leverage = 15  # Leva media-alta
            risk_level = "MEDIUM"
        elif confidence >= 75 and volatility < 5:
            leverage = 10  # Leva moderata
            risk_level = "MEDIUM-LOW"
        elif confidence >= 70:
            leverage = 7   # Leva conservativa
            risk_level = "LOW"
        elif confidence >= 65:
            leverage = 5   # Leva molto conservativa
            risk_level = "LOW"
        else:
            leverage = 3   # Leva minima
            risk_level = "VERY_LOW"
        
        # Riduci leva per alta volatilità
        if volatility > 8:
            leverage = max(3, leverage - 5)
            risk_level = "HIGH"
        elif volatility > 5:
            leverage = max(3, leverage - 2)
        
        return {
            'leverage': leverage,
            'risk_level': risk_level,
            'max_position_size': f"{5 + (leverage - 3) * 2}%"  # 5-15% del capitale
        }
        
    except Exception as e:
        logger.error(f"Errore calcolo leva: {e}")
        return {'leverage': 3, 'risk_level': 'VERY_LOW', 'max_position_size': '5%'}

def calculate_trading_levels(symbol: str, current_price: float, ohlcv_data: List, signal_type: str = "LONG") -> Dict[str, Any]:
    """
    Calcola livelli di trading per SCALPING con:
    - Market entry: prezzo corrente
    - Limit entry: con spread intelligente  
    - Take profit: piccoli guadagni (0.5-2%)
    - Stop loss: protezione stretta (0.3-1%)
    - Percentuali e prezzi di uscita chiari
    """
    try:
        if not ohlcv_data or len(ohlcv_data) < 20:
            # Fallback con calcoli di base per scalping
            precision = get_price_precision(current_price)
            spread_pct = 0.2  # Spread stretto per scalping
            
            # SCALPING: profitti piccoli e veloci
            if signal_type in ["STRONG_LONG", "STRONG_SHORT"]:
                tp_pct = 1.2   # 1.2% target
                sl_pct = 0.6   # 0.6% stop loss
            else:
                tp_pct = 0.8   # 0.8% target  
                sl_pct = 0.4   # 0.4% stop loss
            
            if signal_type in ["LONG", "STRONG_LONG"]:
                limit_entry = round(current_price * (1 - spread_pct/100), precision)
                take_profit = round(current_price * (1 + tp_pct/100), precision)
                stop_loss = round(current_price * (1 - sl_pct/100), precision)
            else:  # SHORT
                limit_entry = round(current_price * (1 + spread_pct/100), precision)
                take_profit = round(current_price * (1 - tp_pct/100), precision)
                stop_loss = round(current_price * (1 + sl_pct/100), precision)
                
            return {
                'market_entry': round(current_price, precision),
                'limit_entry': limit_entry,
                'take_profit': take_profit,
                'stop_loss': stop_loss,
                'tp_percentage': f"+{tp_pct}%" if signal_type in ["LONG", "STRONG_LONG"] else f"-{tp_pct}%",
                'sl_percentage': f"-{sl_pct}%" if signal_type in ["LONG", "STRONG_LONG"] else f"+{sl_pct}%",
                'risk_reward_ratio': round(tp_pct / sl_pct, 2)
            }
        
        # Converti OHLCV in DataFrame
        df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['volume'] = pd.to_numeric(df['volume'])
        
        # Calcola precisione dinamica basata sul valore del token
        precision = get_price_precision(current_price)
        
        # Calcola volatilità per determinare livelli di scalping
        returns = df['close'].pct_change().dropna()
        volatility = returns.std() * 100  # Volatilità in percentuale
        
        # Analizza trend recente per evitare FOMO
        recent_prices = df['close'].tail(10)
        price_change_10min = ((recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]) * 100
        
        # PROTEZIONE ANTI-FOMO: se il prezzo è salito/sceso troppo velocemente, riduci aggressività
        rapid_movement = abs(price_change_10min) > 3  # Se movimento >3% in 10 candele
        
        # Spread per entry ottimizzato per scalping
        if volatility < 1:
            spread_pct = 0.05  # Spread molto stretto
        elif volatility < 2:
            spread_pct = 0.1
        elif volatility < 4:
            spread_pct = 0.2
        else:
            spread_pct = 0.3  # Max spread per scalping
        
        # SCALPING: Target profit piccoli ma consistenti
        if signal_type in ["STRONG_LONG", "STRONG_SHORT"]:
            if volatility < 2 and not rapid_movement:
                tp_pct = 1.5   # 1.5% per segnali forti in mercato stabile
                sl_pct = 0.7   # 0.7% stop loss
            else:
                tp_pct = 1.0   # Riduci target se volatilità alta o movimento rapido
                sl_pct = 0.5
        else:  # LONG/SHORT normali
            if volatility < 2 and not rapid_movement:
                tp_pct = 1.0   # 1% target per segnali normali
                sl_pct = 0.5   # 0.5% stop loss
            else:
                tp_pct = 0.7   # Target più conservativo
                sl_pct = 0.4
        
        # Calcolo livelli basato sulla direzione
        if signal_type in ["LONG", "STRONG_LONG"]:
            # LONG positions
            limit_entry = round(current_price * (1 - spread_pct/100), precision)
            take_profit = round(current_price * (1 + tp_pct/100), precision) 
            stop_loss = round(current_price * (1 - sl_pct/100), precision)
            tp_percentage = f"+{tp_pct}%"
            sl_percentage = f"-{sl_pct}%"
        else:
            # SHORT positions  
            limit_entry = round(current_price * (1 + spread_pct/100), precision)
            take_profit = round(current_price * (1 - tp_pct/100), precision)
            stop_loss = round(current_price * (1 + sl_pct/100), precision)
            tp_percentage = f"-{tp_pct}%"
            sl_percentage = f"+{sl_pct}%"
        
        # Calcola R/R ratio
        risk_reward = round(tp_pct / sl_pct, 2)
        
        return {
            'market_entry': round(current_price, precision),
            'limit_entry': limit_entry,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'tp_percentage': tp_percentage,
            'sl_percentage': sl_percentage,
            'risk_reward_ratio': risk_reward,
            'volatility': round(volatility, 2),
            'rapid_movement_detected': rapid_movement,
            'scalping_duration': "1-5 min" if signal_type.startswith("STRONG") else "3-10 min"
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
        
        # PROTEZIONE ANTI-FOMO: Analisi movimento recente
        recent_data = data['ohlcv'][-10:] if len(data['ohlcv']) >= 10 else data['ohlcv']
        if len(recent_data) > 1:
            recent_change = ((recent_data[-1][4] - recent_data[0][4]) / recent_data[0][4]) * 100
            rapid_movement = abs(recent_change) > 3  # Movimento >3% nelle ultime candele
            
            # Riduci confidence se c'è movimento rapido (possibile FOMO)
            if rapid_movement:
                confidence = confidence * 0.8  # Riduci del 20%
                logger.info(f"ANTI-FOMO: Movimento rapido rilevato per {symbol} ({recent_change:.2f}%), confidence ridotta")
        else:
            rapid_movement = False
        
        # Determina segnale e forza (soglie più alte per evitare falsi segnali)
        if total_score >= 35 and confidence >= 75:  # Soglie più rigorose
            signal_type = "STRONG_LONG"
            momentum_strength = "FORTE"
        elif total_score >= 20 and confidence >= 70:
            signal_type = "LONG"
            momentum_strength = "MODERATO"
        elif total_score <= -35 and confidence >= 75:
            signal_type = "STRONG_SHORT"
            momentum_strength = "FORTE"
        elif total_score <= -20 and confidence >= 70:
            signal_type = "SHORT"
            momentum_strength = "MODERATO"
        else:
            signal_type = "NEUTRAL"
            momentum_strength = "DEBOLE"
        
        # Verifica volume spike
        volume_spike = volume_ratio > 1.8
        
        # Calcola volatilità per leva
        returns = np.array([x[4] for x in data['ohlcv'][-20:]])
        volatility = np.std(np.diff(returns) / returns[:-1]) * 100 if len(returns) > 1 else 2.0
        
        # Calcola livelli di trading per scalping con direzione corretta
        trading_levels = calculate_trading_levels(symbol, current_price, data['ohlcv'], signal_type)
        
        # Calcola leva ottimale
        leverage_info = calculate_optimal_leverage(confidence, volatility, signal_type)
        
        return {
            'signal': signal_type,
            'confidence': round(confidence, 1),
            'momentum_strength': momentum_strength,
            'volume_spike': volume_spike,
            'trading_levels': trading_levels,
            'leverage_info': leverage_info,
            'volatility': round(volatility, 2),
            'anti_fomo_triggered': rapid_movement,
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
    """Formatta il messaggio del segnale con LEVA ottimale e info SCALPING"""
    try:
        # Emoji e direzione
        direction_emoji = "🚀" if "LONG" in signal_data.signal_type else "🔻"
        direction_text = signal_data.signal_type.replace("_", " ")
        
        # Precisione dinamica per i prezzi
        precision = get_price_precision(signal_data.current_price)
        price_format = f"{{:.{precision}f}}"
        
        # Livelli di trading
        levels = signal_data.trading_levels
        market_entry = price_format.format(levels.get('market_entry', signal_data.current_price))
        limit_entry = price_format.format(levels.get('limit_entry', signal_data.current_price))
        take_profit = price_format.format(levels.get('take_profit', signal_data.current_price))
        stop_loss = price_format.format(levels.get('stop_loss', signal_data.current_price))
        
        # Informazioni leva dal signal_data (assumendo che sia stato aggiunto)
        leverage_info = getattr(signal_data, 'leverage_info', {'leverage': 5, 'risk_level': 'MEDIUM', 'max_position_size': '10%'})
        volatility = getattr(signal_data, 'volatility', 2.0)
        anti_fomo = getattr(signal_data, 'anti_fomo_triggered', False)
        
        # Percentuali di trading dal levels
        tp_percentage = levels.get('tp_percentage', '+1.0%')
        sl_percentage = levels.get('sl_percentage', '-0.5%') 
        rr_ratio = levels.get('risk_reward_ratio', 2.0)
        scalping_duration = levels.get('scalping_duration', '3-10 min')
        
        # Calcola profit/loss con leva
        leverage = leverage_info['leverage']
        base_profit = float(tp_percentage.replace('%', '').replace('+', '').replace('-', ''))
        base_loss = float(sl_percentage.replace('%', '').replace('+', '').replace('-', ''))
        
        leveraged_profit = base_profit * leverage
        leveraged_loss = base_loss * leverage
        
        # Forza momentum e indicatori
        strength_emoji = "⚡" if signal_data.momentum_strength == "FORTE" else "📊"
        volume_text = " | 📈 VOLUME SPIKE" if signal_data.volume_spike else ""
        fomo_warning = " | ⚠️ MOVIMENTO RAPIDO" if anti_fomo else ""
        
        # Risk level emoji
        risk_emojis = {
            'VERY_LOW': '🟢', 'LOW': '🟢', 'MEDIUM-LOW': '🟡', 
            'MEDIUM': '🟡', 'HIGH': '🟠', 'VERY_HIGH': '🔴'
        }
        risk_emoji = risk_emojis.get(leverage_info['risk_level'], '🟡')
        
        message = f"""🎯 **SEGNALE SCALPING AI** 
        
{direction_emoji} **{signal_data.symbol}/USDT** - {direction_text}
{strength_emoji} **Confidence:** {signal_data.confidence}% | **Momentum:** {signal_data.momentum_strength}{volume_text}{fomo_warning}

💎 **SETUP SCALPING:**
⏱️ **Durata:** {scalping_duration}
📊 **Volatilità:** {volatility}%
{risk_emoji} **Risk Level:** {leverage_info['risk_level']}

⚡ **LEVA CONSIGLIATA:** {leverage}x
💰 **Position Size:** {leverage_info['max_position_size']} del capitale

💱 **LIVELLI DI TRADING:**
📊 **Market Entry:** ${market_entry} 
🎯 **Limit Entry:** ${limit_entry}
🚀 **Take Profit:** ${take_profit} ({tp_percentage})
🛡️ **Stop Loss:** ${stop_loss} ({sl_percentage})

� **PROFITTO CON LEVA {leverage}x:**
✅ **Target:** +{leveraged_profit:.1f}% (senza leva: {tp_percentage})
❌ **Risk:** -{leveraged_loss:.1f}% (senza leva: {sl_percentage})
📊 **R/R Ratio:** {rr_ratio}:1

🕐 **Timestamp:** {signal_data.timestamp.strftime('%H:%M:%S')}
        
⚠️ **SCALPING DISCLAIMER:** 
• Chiudi posizione velocemente ({scalping_duration})
• Usa SEMPRE stop loss con leva {leverage}x
• NON è consiglio finanziario!"""
        
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
                                momentum_strength=prediction['momentum_strength'],
                                leverage_info=prediction.get('leverage_info', {'leverage': 5, 'risk_level': 'MEDIUM'}),
                                volatility=prediction.get('volatility', 2.0),
                                anti_fomo_triggered=prediction.get('anti_fomo_triggered', False)
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
    """Formatta un'analisi dettagliata con LEVA e setup SCALPING per una crypto specifica"""
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
        
        # Nuove informazioni per scalping
        leverage_info = prediction.get('leverage_info', {'leverage': 5, 'risk_level': 'MEDIUM', 'max_position_size': '10%'})
        volatility = prediction.get('volatility', 2.0)
        anti_fomo = prediction.get('anti_fomo_triggered', False)
        
        # Info dai levels
        tp_percentage = levels.get('tp_percentage', '+1.0%')
        sl_percentage = levels.get('sl_percentage', '-0.5%')
        rr_ratio = levels.get('risk_reward_ratio', 2.0)
        scalping_duration = levels.get('scalping_duration', '3-10 min')
        rapid_movement = levels.get('rapid_movement_detected', False)
        
        # Emoji per direzione e risk level
        direction_emoji = "🚀" if "LONG" in signal_type else "🔻" if "SHORT" in signal_type else "⚪"
        risk_emojis = {
            'VERY_LOW': '🟢', 'LOW': '🟢', 'MEDIUM-LOW': '🟡', 
            'MEDIUM': '🟡', 'HIGH': '🟠', 'VERY_HIGH': '🔴'
        }
        risk_emoji = risk_emojis.get(leverage_info['risk_level'], '🟡')
        
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
            analysis_text.append("• **RSI Oversold** - Buona opportunità di rimbalzo")
        elif rsi > 70:
            analysis_text.append("• **RSI Overbought** - Possibile correzione in arrivo")
        else:
            analysis_text.append("• **RSI Neutrale** - Mercato bilanciato, attendi conferme")
        
        # MACD Analysis
        if macd > macd_signal:
            analysis_text.append("• **MACD Bullish** - Momentum positivo confermato")
        else:
            analysis_text.append("• **MACD Bearish** - Momentum negativo, cautela")
        
        # Bollinger Bands
        if bb_position < 0.2:
            analysis_text.append("• **Vicino Lower Band** - Supporto forte, possibile rimbalzo")
        elif bb_position > 0.8:
            analysis_text.append("• **Vicino Upper Band** - Resistenza, possibile correzione")
        
        # Volume
        if volume_ratio > 1.5:
            analysis_text.append("• **Volume Alto** - Movimento confermato da volume spike")
        
        # Anti-FOMO warning
        if anti_fomo or rapid_movement:
            analysis_text.append("• **⚠️ MOVIMENTO RAPIDO** - Possibile FOMO, attendi conferma")
        
        analysis_summary = "\n".join(analysis_text) if analysis_text else "• Mercato in condizioni normali"
        
        # Calcola profit/loss con leva
        leverage = leverage_info['leverage']
        base_profit = float(tp_percentage.replace('%', '').replace('+', '').replace('-', ''))
        base_loss = float(sl_percentage.replace('%', '').replace('+', '').replace('-', ''))
        
        leveraged_profit = base_profit * leverage
        leveraged_loss = base_loss * leverage

        message = f"""📊 **ANALISI SCALPING DETTAGLIATA {symbol}/USDT**

💰 **PREZZO CORRENTE:** ${current_price:.{precision}f}
📈 **Variazione 24h:** {change_24h:+.2f}%
📊 **Volume 24h:** ${volume_24h:,.0f}

{direction_emoji} **SEGNALE:** {signal_type.replace('_', ' ')}
⚡ **Confidence:** {confidence}%
📊 **Momentum:** {momentum_strength}

💎 **SETUP SCALPING:**
⏱️ **Durata consigliata:** {scalping_duration}
📊 **Volatilità:** {volatility}%
{risk_emoji} **Risk Level:** {leverage_info['risk_level']}

⚡ **LEVA CONSIGLIATA:** {leverage}x
💰 **Position Size:** {leverage_info['max_position_size']} del capitale

💱 **LIVELLI DI TRADING:**
📊 **Market Entry:** ${market_entry}
🎯 **Limit Entry:** ${limit_entry}
🚀 **Take Profit:** ${take_profit} ({tp_percentage})
🛡️ **Stop Loss:** ${stop_loss} ({sl_percentage})

� **PROFIT/LOSS CON LEVA {leverage}x:**
✅ **Target:** +{leveraged_profit:.1f}% (senza leva: {tp_percentage})
❌ **Risk:** -{leveraged_loss:.1f}% (senza leva: {sl_percentage})
📊 **R/R Ratio:** {rr_ratio}:1

🔍 **INDICATORI TECNICI:**
• **RSI:** {rsi:.1f}
• **MACD:** {macd:.4f} / {macd_signal:.4f}
• **BB Position:** {bb_position:.1%}
• **Volume Ratio:** {volume_ratio:.1f}x

📋 **ANALISI AI:**
{analysis_summary}

🕐 **Analisi generata:** {datetime.now().strftime('%H:%M:%S')}

⚠️ **SCALPING DISCLAIMER:** 
• Chiudi posizione entro {scalping_duration}
• Usa SEMPRE stop loss con leva {leverage}x
• NON è consiglio finanziario!"""
        
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
