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
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

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

def calculate_support_resistance(df: pd.DataFrame, window=20):
    """Calcola livelli di supporto e resistenza"""
    try:
        highs = df['high'].rolling(window=window, center=True).max()
        lows = df['low'].rolling(window=window, center=True).min()
        
        # Trova i picchi locali (resistenze)
        resistance_levels = []
        support_levels = []
        
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == highs.iloc[i]:
                resistance_levels.append((i, df['high'].iloc[i]))
            if df['low'].iloc[i] == lows.iloc[i]:
                support_levels.append((i, df['low'].iloc[i]))
        
        # Raggruppa livelli simili
        def group_levels(levels, threshold=0.01):
            if not levels:
                return []
            
            grouped = []
            levels.sort(key=lambda x: x[1])
            
            current_group = [levels[0]]
            for level in levels[1:]:
                if abs(level[1] - current_group[-1][1]) / current_group[-1][1] < threshold:
                    current_group.append(level)
                else:
                    # Prendi il livello più forte del gruppo (quello con più tocchi)
                    grouped.append(max(current_group, key=lambda x: x[1]))
                    current_group = [level]
            
            if current_group:
                grouped.append(max(current_group, key=lambda x: x[1]))
            
            return grouped[-5:]  # Ritorna solo i 5 livelli più recenti
        
        resistance_levels = group_levels(resistance_levels)
        support_levels = group_levels(support_levels)
        
        return {
            'resistance': [level[1] for level in resistance_levels],
            'support': [level[1] for level in support_levels],
            'resistance_idx': [level[0] for level in resistance_levels],
            'support_idx': [level[0] for level in support_levels]
        }
    except Exception as e:
        logger.error(f"Errore calcolo supporti/resistenze: {e}")
        return {'resistance': [], 'support': [], 'resistance_idx': [], 'support_idx': []}

def analyze_macd_signals(macd_data: dict, df: pd.DataFrame) -> dict:
    """Analizza segnali MACD per trading long/short"""
    try:
        macd_line = macd_data['MACD']
        signal_line = macd_data['Signal']
        histogram = macd_data['Histogram']
        
        # Segnali di crossover
        crossovers = []
        for i in range(1, len(macd_line)):
            if (macd_line.iloc[i] > signal_line.iloc[i] and 
                macd_line.iloc[i-1] <= signal_line.iloc[i-1]):
                crossovers.append(('bullish', i))
            elif (macd_line.iloc[i] < signal_line.iloc[i] and 
                  macd_line.iloc[i-1] >= signal_line.iloc[i-1]):
                crossovers.append(('bearish', i))
        
        # Ultimo segnale
        last_signal = crossovers[-1] if crossovers else ('neutral', 0)
        
        # Divergenze
        price_trend = 'up' if df['close'].iloc[-1] > df['close'].iloc[-10] else 'down'
        macd_trend = 'up' if macd_line.iloc[-1] > macd_line.iloc[-10] else 'down'
        divergence = 'bullish' if price_trend == 'down' and macd_trend == 'up' else \
                    'bearish' if price_trend == 'up' and macd_trend == 'down' else 'none'
        
        # Forza del segnale
        current_histogram = histogram.iloc[-1]
        prev_histogram = histogram.iloc[-2] if len(histogram) > 1 else 0
        momentum = 'increasing' if current_histogram > prev_histogram else 'decreasing'
        
        return {
            'last_crossover': last_signal[0],
            'crossover_position': last_signal[1],
            'divergence': divergence,
            'momentum': momentum,
            'histogram_value': current_histogram,
            'signal_strength': abs(current_histogram)
        }
    except Exception as e:
        logger.error(f"Errore analisi MACD: {e}")
        return {
            'last_crossover': 'neutral',
            'crossover_position': 0,
            'divergence': 'none',
            'momentum': 'neutral',
            'histogram_value': 0,
            'signal_strength': 0
        }

def ai_trading_prediction(indicators: dict, macd_signals: dict, support_resistance: dict, df: pd.DataFrame, crypto_data: dict = None) -> dict:
    """Sistema AI avanzato per trading professionale con analisi multi-timeframe e dati di mercato"""
    try:
        score = 0
        signals = []
        confidence = 0
        
        current_price = df['close'].iloc[-1]
        
        # Usa dati di mercato avanzati se disponibili per SCALPING
        volatility_1m = crypto_data.get('volatility_1m', 0) if crypto_data else 0
        volatility_5m = crypto_data.get('volatility_5m', 0) if crypto_data else 0
        volatility_15m = crypto_data.get('volatility_15m', 0) if crypto_data else 0
        volatility_24h = crypto_data.get('volatility_24h', 0) if crypto_data else 0
        volatility_4h = crypto_data.get('volatility_4h', 0) if crypto_data else 0
        
        momentum_1m = crypto_data.get('momentum_1m', 0) if crypto_data else 0
        momentum_5m = crypto_data.get('momentum_5m', 0) if crypto_data else 0
        momentum_15m = crypto_data.get('momentum_15m', 0) if crypto_data else 0
        momentum_1h = crypto_data.get('momentum_1h', 0) if crypto_data else 0
        momentum_4h = crypto_data.get('momentum_4h', 0) if crypto_data else 0
        
        position_1m = crypto_data.get('position_1m', 50) if crypto_data else 50
        position_5m = crypto_data.get('position_5m', 50) if crypto_data else 50
        position_24h = crypto_data.get('position_24h', 50) if crypto_data else 50
        
        volume_ratio_5m = crypto_data.get('volume_ratio_5m', 1) if crypto_data else 1
        volume_ratio_1h = crypto_data.get('volume_ratio_1h', 1) if crypto_data else 1
        
        range_1m = crypto_data.get('range_1m', 0) if crypto_data else 0
        range_5m = crypto_data.get('range_5m', 0) if crypto_data else 0
        range_15m = crypto_data.get('range_15m', 0) if crypto_data else 0
        range_24h = crypto_data.get('range_24h', 0) if crypto_data else 0
        
        market_cap_rank = crypto_data.get('market_cap_rank', 999) if crypto_data else 999
        
        # Fallback volatility calculation se non abbiamo crypto_data
        if volatility_24h == 0:
            high_24h = df['high'].tail(24).max()
            low_24h = df['low'].tail(24).min()
            volatility_24h = ((high_24h - low_24h) / current_price) * 100
        
        # 1. ANALISI RSI MULTI-TIMEFRAME (peso: 20%)
        rsi = indicators['rsi']
        if rsi < 20:  # RSI estremamente oversold
            score += 4
            signals.append("🔥 RSI ESTREMO oversold (20) - FORTISSIMA opportunità LONG")
        elif rsi < 30:
            score += 3
            signals.append("📈 RSI ipervenduto - Opportunità LONG confermata")
        elif rsi < 35:
            score += 2
            signals.append("📈 RSI sotto 35 - Possibile LONG")
        elif rsi > 80:  # RSI estremamente overbought
            score -= 4
            signals.append("⚠️ RSI ESTREMO overbought (80) - FORTISSIMA opportunità SHORT")
        elif rsi > 70:
            score -= 3
            signals.append("📉 RSI ipercomprato - Opportunità SHORT confermata")
        elif rsi > 65:
            score -= 2
            signals.append("📉 RSI sopra 65 - Possibile SHORT")
        elif 45 <= rsi <= 55:
            score += 0.5
            signals.append("⚖️ RSI equilibrato - Mercato neutrale")
        
        # 2. ANALISI MOMENTUM SCALPING ULTRA-PRECISO (peso: 30%)
        momentum_score = 0
        
        # MICRO-MOMENTUM (1m) - Per entry precisissimi
        if abs(momentum_1m) > 0.5:  # Movimento forte in 1 minuto
            if momentum_1m > 0.5:
                momentum_score += 2
                signals.append(f"⚡ MICRO-Momentum 1m ESPLOSIVO: +{momentum_1m:.2f}%")
            else:
                momentum_score -= 2
                signals.append(f"💥 MICRO-Momentum 1m CRASH: {momentum_1m:.2f}%")
        
        # SCALPING MOMENTUM (5m) - Timeframe principale
        if abs(momentum_5m) > 1:
            if momentum_5m > 1:
                momentum_score += 3
                signals.append(f"🚀 SCALP-Momentum 5m FORTE: +{momentum_5m:.2f}%")
            else:
                momentum_score -= 3
                signals.append(f"🔥 SCALP-Momentum 5m NEGATIVO: {momentum_5m:.2f}%")
        
        # SHORT-TERM MOMENTUM (15m) - Conferma direzione
        if abs(momentum_15m) > 2:
            if momentum_15m > 2:
                momentum_score += 2
                signals.append(f"� SHORT-Momentum 15m eccellente: +{momentum_15m:.1f}%")
            else:
                momentum_score -= 2
                signals.append(f"� SHORT-Momentum 15m pessimo: {momentum_15m:.1f}%")
        
        # TREND MOMENTUM (1h) - Bias generale  
        if abs(momentum_1h) > 3:
            if momentum_1h > 3:
                momentum_score += 2
                signals.append(f"� TREND-Momentum 1h forte: +{momentum_1h:.1f}%")
            else:
                momentum_score -= 2
                signals.append(f"� TREND-Momentum 1h debole: {momentum_1h:.1f}%")
        
        # MAJOR TREND (4h) - Context generale
        if abs(momentum_4h) > 5:
            if momentum_4h > 5:
                momentum_score += 1.5
                signals.append(f"🌟 MAJOR-Trend 4h molto forte: +{momentum_4h:.1f}%")
            else:
                momentum_score -= 1.5
                signals.append(f"⚠️ MAJOR-Trend 4h molto debole: {momentum_4h:.1f}%")
            
        score += momentum_score
        
        # 3. ANALISI MACD PROFESSIONALE (peso: 20%)
        histogram_strength = abs(macd_signals.get('histogram_value', 0))
        if macd_signals['last_crossover'] == 'bullish':
            if histogram_strength > 0.002:  # Crossover molto forte
                score += 4
                signals.append("🚀 MACD crossover FORTISSIMO - Entry LONG garantito")
            elif histogram_strength > 0.001:
                score += 3
                signals.append("🚀 MACD crossover FORTE - Entry LONG confermato")
            else:
                score += 2
                signals.append("📈 MACD crossover bullish - Segnale LONG")
        elif macd_signals['last_crossover'] == 'bearish':
            if histogram_strength > 0.002:
                score -= 4
                signals.append("💥 MACD crossover FORTISSIMO - Entry SHORT garantito")
            elif histogram_strength > 0.001:
                score -= 3
                signals.append("💥 MACD crossover FORTE - Entry SHORT confermato")
            else:
                score -= 2
                signals.append("📉 MACD crossover bearish - Segnale SHORT")
        
        # Divergenze premium
        if macd_signals['divergence'] == 'bullish':
            score += 3
            signals.append("⚡ Divergenza bullish MACD - Inversione LONG imminente")
        elif macd_signals['divergence'] == 'bearish':
            score -= 3
            signals.append("⚡ Divergenza bearish MACD - Inversione SHORT imminente")
        
        # 4. ANALISI POSITION SCALPING MULTI-TIMEFRAME (peso: 20%)
        position_score = 0
        
        # Position 1m - Micro-timing per scalping estremo
        if position_1m < 5:  # Vicino al bottom 1m
            position_score += 4
            signals.append(f"🎯 MICRO-BOTTOM 1m ({position_1m:.1f}%) - Entry PERFETTO LONG!")
        elif position_1m > 95:  # Vicino al top 1m
            position_score -= 4
            signals.append(f"🎯 MICRO-TOP 1m ({position_1m:.1f}%) - Entry PERFETTO SHORT!")
        elif position_1m < 15:
            position_score += 2
            signals.append(f"✅ LOW-ZONE 1m ({position_1m:.1f}%) - LONG timing buono")
        elif position_1m > 85:
            position_score -= 2
            signals.append(f"✅ HIGH-ZONE 1m ({position_1m:.1f}%) - SHORT timing buono")
        
        # Position 5m - Timing principale scalping
        if position_5m < 8:
            position_score += 3
            signals.append(f"🚀 SCALP-BOTTOM 5m ({position_5m:.1f}%) - LONG confermato!")
        elif position_5m > 92:
            position_score -= 3
            signals.append(f"💥 SCALP-TOP 5m ({position_5m:.1f}%) - SHORT confermato!")
        elif position_5m < 20:
            position_score += 1.5
            signals.append(f"📈 Low-zone 5m ({position_5m:.1f}%) - LONG valido")
        elif position_5m > 80:
            position_score -= 1.5
            signals.append(f"📉 High-zone 5m ({position_5m:.1f}%) - SHORT valido")
        
        # Position 24h - Context generale per bias
        if position_24h < 10:
            position_score += 1
            signals.append(f"💎 DAILY-BOTTOM ({position_24h:.1f}%) - Bias LONG generale")
        elif position_24h > 90:
            position_score -= 1
            signals.append(f"⚠️ DAILY-TOP ({position_24h:.1f}%) - Bias SHORT generale")
        
        score += position_score
        
        # 5. ANALISI SUPPORT/RESISTANCE STRATEGICA (peso: 15%)
        entry_quality = 0
        stop_distance = 0
        target_distance = 0
        
        if support_resistance['support']:
            nearest_support = min(support_resistance['support'], key=lambda x: abs(x - current_price))
            support_distance = (current_price - nearest_support) / current_price * 100
            
            if support_distance < 0.5:  # Molto vicino al supporto
                score += 4
                entry_quality += 2
                stop_distance = support_distance + 0.3
                signals.append(f"🎯 PERFETTO! Su supporto chiave ${nearest_support:.2f}")
            elif support_distance < 1.5:
                score += 2
                entry_quality += 1
                stop_distance = support_distance + 0.5
                signals.append(f"✅ Vicino supporto ${nearest_support:.2f}")
        
        if support_resistance['resistance']:
            nearest_resistance = min(support_resistance['resistance'], key=lambda x: abs(x - current_price))
            resistance_distance = (nearest_resistance - current_price) / current_price * 100
            
            if resistance_distance < 0.5:  # Molto vicino alla resistenza
                score -= 4
                entry_quality += 2
                stop_distance = resistance_distance + 0.3
                signals.append(f"🎯 PERFETTO! Su resistenza chiave ${nearest_resistance:.2f}")
            elif resistance_distance < 1.5:
                score -= 2
                entry_quality += 1
                stop_distance = resistance_distance + 0.5
                signals.append(f"✅ Vicino resistenza ${nearest_resistance:.2f}")
            
            target_distance = resistance_distance
        
        # 6. ANALISI VOLUME SCALPING PRECISION (peso: 15%)
        volume_ratio = indicators.get('volume_ratio', 1)
        volume_score = 0
        
        # Volume 5m per timing micro-entry
        if volume_ratio_5m > 5:  # Volume 5m esplosivo
            volume_score += 4
            signals.append(f"💥 VOLUME 5m ESPLOSIVO ({volume_ratio_5m:.1f}x) - Movimento GARANTITO!")
        elif volume_ratio_5m > 3:
            volume_score += 3
            signals.append(f"� Volume 5m molto forte ({volume_ratio_5m:.1f}x) - Breakout confermato!")
        elif volume_ratio_5m > 2:
            volume_score += 2
            signals.append(f"📊 Volume 5m elevato ({volume_ratio_5m:.1f}x) - Movimento valido")
        elif volume_ratio_5m < 0.3:
            volume_score -= 2
            signals.append(f"⚠️ Volume 5m morto ({volume_ratio_5m:.1f}x) - Skip trade!")
        
        # Volume 1h per context + volume 5m
        if volume_ratio > 2.5 and volume_ratio_1h > 1.5:  # Volume combinato forte
            volume_score += 2
            signals.append("💎 VOLUME MULTI-TF confermato - Movimento SICURO!")
        elif volume_ratio > 2:
            volume_score += 1.5
            signals.append("📈 Volume generale elevato - Segnale confermato")
        elif volume_ratio < 0.5:
            volume_score -= 1
            signals.append("⚠️ Volume basso - Movimento poco convincente")
        
        score += volume_score
        
        # 7. ANALISI VOLATILITÀ SCALPING & BREAKOUT (peso: 15%)
        volatility_score = 0
        
        # Range compression su timeframe corti = esplosione imminente
        if range_1m < 0.5 and range_5m < 1.5 and range_15m < 3:
            volatility_score += 4
            signals.append(f"💎 COMPRESSIONE ESTREMA multi-TF - ESPLOSIONE GARANTITA!")
        elif range_5m < 1 and range_15m < 2:
            volatility_score += 3
            signals.append(f"💎 Compressione 5m-15m - Breakout imminente!")
        elif range_1m < 0.3:
            volatility_score += 2
            signals.append(f"⚡ Micro-compressione 1m - Setup scalping perfetto!")
        
        # Volatilità attiva = movimenti forti per scalping
        elif range_5m > 3:
            volatility_score += 2
            signals.append(f"⚡ Volatilità 5m attiva ({range_5m:.1f}%) - Scalping attivo!")
        elif range_1m > 1:
            volatility_score += 1
            signals.append(f"📈 Volatilità 1m buona ({range_1m:.1f}%) - Micro-movimenti")
        
        # Volatilità ottimale per scalping con leva
        if 2 < volatility_5m < 8:  # Sweet spot per scalping
            volatility_score += 2
            signals.append(f"✅ Volatilità 5m PERFETTA ({volatility_5m:.1f}%) per scalping ad alta leva!")
        elif volatility_5m > 15:  # Troppo volatile per leva alta
            volatility_score -= 2
            signals.append(f"⚠️ Volatilità 5m ESTREMA ({volatility_5m:.1f}%) - Riduci leva!")
        elif volatility_24h > 25:  # Mercato troppo caotico
            volatility_score -= 3
            signals.append(f"🚨 Volatilità 24h PERICOLOSA ({volatility_24h:.1f}%) - EVITA trading!")
        
        score += volatility_score
        
        # 8. BONUS/MALUS PER CRYPTO DI NICCHIA E POTENZIALE (peso: 5%)
        niche_score = 0
        
        # Crypto di nicchia (rank alto) con potenziale maggiore
        if market_cap_rank > 100:
            niche_score += 1
            signals.append("� CRYPTO DI NICCHIA - Potenziale x10 maggiore")
        elif market_cap_rank > 50:
            niche_score += 0.5
            signals.append("📈 Crypto mid-cap - Buon potenziale")
        
        # Bonus per grandi variazioni 24h (momentum trading)
        change_24h = crypto_data.get('change_24h', 0) if crypto_data else 0
        if abs(change_24h) > 15:
            niche_score += 1.5
            signals.append(f"� MOVIMENTO FORTE 24h: {change_24h:+.1f}%")
        elif abs(change_24h) > 10:
            niche_score += 1
            signals.append(f"⚡ Movimento significativo 24h: {change_24h:+.1f}%")
        
        score += niche_score
        
        # 9. CALCOLO RISK MANAGEMENT AVANZATO
        risk_multiplier = 1
        if volatility_24h > 15:  # Alta volatilità
            risk_multiplier = 0.4
            signals.append(f"⚠️ VOLATILITÀ ESTREMA ({volatility_24h:.1f}%) - Riduci leva drasticamente!")
        elif volatility_24h > 10:
            risk_multiplier = 0.6
            signals.append(f"⚠️ Alta volatilità ({volatility_24h:.1f}%) - Riduci leva!")
        elif volatility_24h > 7:
            risk_multiplier = 0.8
            signals.append(f"⚠️ Volatilità moderata-alta ({volatility_24h:.1f}%)")
        elif volatility_24h < 3:
            risk_multiplier = 1.3
            signals.append(f"✅ Bassa volatilità ({volatility_24h:.1f}%) - Leva sicura")
        
        # 10. CALCOLO CONFIDENZA AVANZATA
        max_score = 18  # Aumentato per i nuovi fattori
        raw_confidence = min(100, abs(score) / max_score * 100)
        
        # Boost confidenza per segnali multipli convergenti
        convergence_boost = 0
        if volume_ratio > 2 and abs(momentum_4h) > 3:
            convergence_boost += 10
        if entry_quality > 1 and histogram_strength > 0.001:
            convergence_boost += 10
        if abs(change_24h) > 8 and (position_24h < 20 or position_24h > 80):
            convergence_boost += 5
        
        confidence = min(100, raw_confidence + convergence_boost)
        
        # 11. SISTEMA DI RACCOMANDAZIONI PROFESSIONALE AVANZATO
        direction = "LONG" if score > 0 else "SHORT" if score < 0 else "HOLD"
        
        # Calcolo leva ottimale per SCALPING ULTRA-AGGRESSIVO
        base_leverage = 1
        if confidence > 95 and volatility_5m < 2 and abs(score) > 12:
            base_leverage = 50  # Leva MASSIMA per setup perfetti su 5m
        elif confidence > 92 and volatility_5m < 3 and abs(score) > 10:
            base_leverage = 40  # Leva ULTRA per setup quasi perfetti
        elif confidence > 88 and volatility_5m < 4 and abs(score) > 8:
            base_leverage = 30  # Leva ALTA per buoni setup
        elif confidence > 85 and volatility_5m < 5 and abs(score) > 6:
            base_leverage = 25
        elif confidence > 80 and volatility_5m < 6:
            base_leverage = 20
        elif confidence > 75 and volatility_5m < 8:
            base_leverage = 15
        elif confidence > 70:
            base_leverage = 10  # Leva minima per scalping
        elif confidence > 60:
            base_leverage = 5   # Setup deboli
        else:
            base_leverage = 1   # No scalping
        
        optimal_leverage = max(1, int(base_leverage * risk_multiplier))
        
        # Position sizing per SCALPING con alta leva
        if confidence > 90 and optimal_leverage >= 25:
            position_size = "ULTRA (8-12% capitale) - SCALPING ESTREMO"
        elif confidence > 85 and optimal_leverage >= 20:
            position_size = "MEGA (5-8% capitale) - SCALPING AGGRESSIVO"
        elif confidence > 80 and optimal_leverage >= 15:
            position_size = "GRANDE (3-5% capitale) - SCALPING ATTIVO"
        elif confidence > 75 and optimal_leverage >= 10:
            position_size = "MEDIA (2-3% capitale) - SCALPING NORMALE"
        elif confidence > 65 and optimal_leverage >= 5:
            position_size = "PICCOLA (1-2% capitale) - SCALPING PRUDENTE"
        elif confidence > 55:
            position_size = "MICRO (0.5-1% capitale) - SCALPING MINIMO"
        else:
            position_size = "NESSUNA - SKIP (setup insufficiente)"
        
        # Risk/Reward calculation migliorato
        if stop_distance > 0:
            risk_reward = target_distance / stop_distance if target_distance > 0 else 3.0
        else:
            risk_reward = 3.0
        
        # Determina raccomandazione finale
        if score >= 6:
            recommendation = "STRONG LONG"
            action = "🔥 STRONG BUY"
            trade_confidence = "MOLTO ALTA"
        elif score >= 3:
            recommendation = "LONG"
            action = "🟢 BUY"
            trade_confidence = "ALTA"
        elif score >= 1:
            recommendation = "WEAK LONG"
            action = "🟡 WEAK BUY"
            trade_confidence = "MEDIA"
        elif score <= -6:
            recommendation = "STRONG SHORT"
            action = "� STRONG SELL"
            trade_confidence = "MOLTO ALTA"
        elif score <= -3:
            recommendation = "SHORT"
            action = "�🔴 SELL"
            trade_confidence = "ALTA"
        elif score <= -1:
            recommendation = "WEAK SHORT"
            action = "🟡 WEAK SELL"
            trade_confidence = "MEDIA"
        else:
            recommendation = "HOLD"
            action = "⚪ HOLD"
            trade_confidence = "BASSA"
        
        return {
            'recommendation': recommendation,
            'action': action,
            'direction': direction,
            'score': score,
            'confidence': round(confidence, 1),
            'trade_confidence': trade_confidence,
            'timeframe': "Non definito",
            'signals': signals[:8],  # Top 8 segnali
            'optimal_leverage': optimal_leverage,
            'position_size': position_size,
            'volatility_5m': round(volatility_5m, 1),
            'volatility_24h': round(volatility_24h, 1),
            'risk_reward': round(risk_reward, 1),
            'stop_distance': round(stop_distance, 2),
            'entry_quality': entry_quality,
            'momentum_score': momentum_score,
            'volume_score': volume_score,
            'volatility_score': volatility_score,
            'niche_score': niche_score,
            'convergence_boost': convergence_boost,
            'risk_level': 'EXTREME' if confidence > 95 else 'VERY_HIGH' if confidence > 85 else 'HIGH' if confidence > 70 else 'MEDIUM' if confidence > 50 else 'LOW'
        }
        
    except Exception as e:
        logger.error(f"Errore predizione AI: {e}")
        return {
            'recommendation': 'HOLD',
            'action': '⚪ HOLD',
            'direction': 'HOLD',
            'score': 0,
            'confidence': 0,
            'trade_confidence': 'NESSUNA',
            'signals': ['Errore nell\'analisi'],
            'optimal_leverage': 1,
            'position_size': 'NESSUNA',
            'volatility': 0,
            'risk_reward': 0,
            'risk_level': 'UNKNOWN'
        }

class CryptoAnalysisBot:
    def __init__(self, telegram_token: str, cryptopanic_token: str = None):
        self.telegram_token = telegram_token
        self.cryptopanic_token = cryptopanic_token
        
        # Inizializza exchange Bybit (no restrizioni geografiche)
        self.exchange = ccxt.bybit({
            'apiKey': '',  # Non necessario per dati pubblici
            'secret': '',
            'timeout': 30000,
            'enableRateLimit': True,
            'sandbox': False,  # Usa API di produzione
        })
    
    async def get_crypto_data(self, symbol: str) -> dict:
        """Recupera dati crypto da Bybit ottimizzati per scalping e trade ad alta frequenza"""
        try:
            # Assicurati che il simbolo sia in formato USDT
            if not symbol.endswith('USDT'):
                symbol = f"{symbol.upper()}USDT"
            
            # Ottieni ticker per prezzo e variazione 24h
            ticker = self.exchange.fetch_ticker(symbol)
            
            # DATI SCALPING: Timeframe corti per trade rapidi
            ohlcv_1m = self.exchange.fetch_ohlcv(symbol, '1m', limit=200)  # 3+ ore di dati
            ohlcv_5m = self.exchange.fetch_ohlcv(symbol, '5m', limit=100)   # 8+ ore di dati
            ohlcv_15m = self.exchange.fetch_ohlcv(symbol, '15m', limit=96)  # 24 ore di dati
            
            # Timeframe più lunghi per context
            ohlcv_1h = self.exchange.fetch_ohlcv(symbol, '1h', limit=48)    # 48 ore
            ohlcv_4h = self.exchange.fetch_ohlcv(symbol, '4h', limit=24)    # 4 giorni
            
            # Crea DataFrames per tutti i timeframe di scalping
            df_1m = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1m['timestamp'] = pd.to_datetime(df_1m['timestamp'], unit='ms')
            df_1m.set_index('timestamp', inplace=True)
            
            df_5m = pd.DataFrame(ohlcv_5m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_5m['timestamp'] = pd.to_datetime(df_5m['timestamp'], unit='ms')
            df_5m.set_index('timestamp', inplace=True)
            
            df_15m = pd.DataFrame(ohlcv_15m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_15m['timestamp'] = pd.to_datetime(df_15m['timestamp'], unit='ms')
            df_15m.set_index('timestamp', inplace=True)
            
            df_1h = pd.DataFrame(ohlcv_1h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_1h['timestamp'] = pd.to_datetime(df_1h['timestamp'], unit='ms')
            df_1h.set_index('timestamp', inplace=True)
            
            df_4h = pd.DataFrame(ohlcv_4h, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df_4h['timestamp'] = pd.to_datetime(df_4h['timestamp'], unit='ms')
            df_4h.set_index('timestamp', inplace=True)
            
            # DataFrame principale per analisi = 5m (ottimo per scalping)
            df = df_5m.copy()
            
            # Calcola metriche scalping ultra-precise
            current_price = ticker['last']
            
            # VOLATILITÀ SCALPING: Multi-timeframe per precisione estrema
            vol_1m = ((df_1m['high'].tail(60).max() - df_1m['low'].tail(60).min()) / current_price) * 100  # 1h di 1m
            vol_5m = ((df_5m['high'].tail(24).max() - df_5m['low'].tail(24).min()) / current_price) * 100  # 2h di 5m
            vol_15m = ((df_15m['high'].tail(16).max() - df_15m['low'].tail(16).min()) / current_price) * 100  # 4h di 15m
            vol_24h = ((ticker['high'] - ticker['low']) / current_price) * 100
            vol_4h = ((df_4h['high'].tail(6).max() - df_4h['low'].tail(6).min()) / current_price) * 100  # 24h di 4h
            
            # VOLUME ANALYSIS per entry timing
            volume_24h = ticker['quoteVolume']
            avg_volume_1h = df_1h['volume'].tail(24).mean()
            avg_volume_5m = df_5m['volume'].tail(12).mean()  # 1h di 5m
            volume_ratio_1h = volume_24h / (avg_volume_1h * 24) if avg_volume_1h > 0 else 1
            volume_ratio_5m = df_5m['volume'].iloc[-1] / avg_volume_5m if avg_volume_5m > 0 else 1
            
            # MOMENTUM SCALPING: Precisione al minuto
            price_1m = df_1m['close'].iloc[-2] if len(df_1m) > 1 else current_price
            price_5m = df_5m['close'].iloc[-2] if len(df_5m) > 1 else current_price
            price_15m = df_15m['close'].iloc[-2] if len(df_15m) > 1 else current_price
            price_1h = df_1h['close'].iloc[-2] if len(df_1h) > 1 else current_price
            price_4h = df_4h['close'].iloc[-2] if len(df_4h) > 1 else current_price
            
            momentum_1m = ((current_price - price_1m) / price_1m) * 100
            momentum_5m = ((current_price - price_5m) / price_5m) * 100
            momentum_15m = ((current_price - price_15m) / price_15m) * 100
            momentum_1h = ((current_price - price_1h) / price_1h) * 100
            momentum_4h = ((current_price - price_4h) / price_4h) * 100
            
            # RANGE ANALYSIS per breakout scalping
            range_1m = ((df_1m['high'].tail(10).max() - df_1m['low'].tail(10).min()) / df_1m['low'].tail(10).min()) * 100
            range_5m = ((df_5m['high'].tail(12).max() - df_5m['low'].tail(12).min()) / df_5m['low'].tail(12).min()) * 100
            range_15m = ((df_15m['high'].tail(8).max() - df_15m['low'].tail(8).min()) / df_15m['low'].tail(8).min()) * 100
            range_24h = ((ticker['high'] - ticker['low']) / ticker['low']) * 100
            
            # MARKET STRUCTURE per timing perfetto
            high_1m = df_1m['high'].tail(5).max()
            low_1m = df_1m['low'].tail(5).min()
            high_5m = df_5m['high'].tail(6).max()
            low_5m = df_5m['low'].tail(6).min()
            high_24h = ticker['high']
            low_24h = ticker['low']
            
            # Position in range su diversi timeframe
            position_1m = ((current_price - low_1m) / (high_1m - low_1m)) * 100 if high_1m != low_1m else 50
            position_5m = ((current_price - low_5m) / (high_5m - low_5m)) * 100 if high_5m != low_5m else 50
            position_24h = ((current_price - low_24h) / (high_24h - low_24h)) * 100 if high_24h != low_24h else 50
            
            return {
                'symbol': symbol,
                'price': current_price,
                'change_24h': ticker['percentage'],
                'volume_24h': volume_24h,
                'high_24h': high_24h,
                'low_24h': low_24h,
                'df': df,  # DataFrame principale 5m per scalping
                'df_1m': df_1m,  # 1m per micro-scalping 
                'df_5m': df_5m,  # 5m principal timeframe
                'df_15m': df_15m,  # 15m per context
                'df_1h': df_1h,  # 1h per trend
                'df_4h': df_4h,  # 4h per bias generale
                
                # METRICHE SCALPING ULTRA-PRECISE
                'volatility_1m': round(vol_1m, 2),
                'volatility_5m': round(vol_5m, 2),
                'volatility_15m': round(vol_15m, 2),
                'volatility_24h': round(vol_24h, 2),
                'volatility_4h': round(vol_4h, 2),
                
                # VOLUME per timing entry/exit
                'volume_ratio_1h': round(volume_ratio_1h, 2),
                'volume_ratio_5m': round(volume_ratio_5m, 2),
                
                # MOMENTUM multi-timeframe scalping
                'momentum_1m': round(momentum_1m, 3),  # Precision al millesimo per scalping
                'momentum_5m': round(momentum_5m, 3),
                'momentum_15m': round(momentum_15m, 2),
                'momentum_1h': round(momentum_1h, 2),
                'momentum_4h': round(momentum_4h, 2),
                
                # RANGE analysis per breakout
                'range_1m': round(range_1m, 2),
                'range_5m': round(range_5m, 2),
                'range_15m': round(range_15m, 2),
                'range_24h': round(range_24h, 2),
                
                # POSITION per timing perfetto
                'position_1m': round(position_1m, 1),
                'position_5m': round(position_5m, 1),
                'position_24h': round(position_24h, 1),
                
                'market_cap_rank': self._estimate_market_cap_rank(symbol)
            }
        except Exception as e:
            logger.error(f"Errore recupero dati crypto: {e}")
            raise
    
    def _estimate_market_cap_rank(self, symbol: str) -> int:
        """Stima il ranking di market cap"""
        top_cryptos = {
            'BTCUSDT': 1, 'ETHUSDT': 2, 'BNBUSDT': 3, 'XRPUSDT': 4, 'ADAUSDT': 5,
            'DOGEUSDT': 6, 'SOLUSDT': 7, 'TRXUSDT': 8, 'MATICUSDT': 9, 'DOTUSDT': 10,
            'LTCUSDT': 11, 'BCHUSDT': 12, 'AVAXUSDT': 13, 'SHIBUSDT': 14, 'UNIUSDT': 15,
            'LINKUSDT': 16, 'XLMUSDT': 17, 'ETCUSDT': 18, 'ATOMUSDT': 19, 'VETUSDT': 20,
            'FILUSDT': 25, 'THETAUSDT': 30, 'AAVEUSDT': 35, 'ALGOUSDT': 40, 'ICPUSDT': 45,
            'NEARUSDT': 50, 'MANAUSDT': 60, 'SANDUSDT': 70, 'AXSUSDT': 80, 'CRVUSDT': 90,
            'SUSHIUSDT': 100, 'COMPUSDT': 110, 'MKRUSDT': 120, 'SNXUSDT': 130, 'YFIUSDT': 140
        }
        return top_cryptos.get(symbol, 999)  # 999 per crypto sconosciute/di nicchia
    
    def calculate_technical_indicators(self, df: pd.DataFrame, crypto_data: dict = None) -> dict:
        """Calcola indicatori tecnici avanzati"""
        try:
            # RSI (14 periodi)
            rsi_series = calculate_rsi(df['close'], 14)
            rsi = rsi_series.iloc[-1] if not pd.isna(rsi_series.iloc[-1]) else 50
            
            # MACD
            macd_data = calculate_macd(df['close'])
            macd = macd_data['MACD'].iloc[-1] if not pd.isna(macd_data['MACD'].iloc[-1]) else 0
            macd_signal = macd_data['Signal'].iloc[-1] if not pd.isna(macd_data['Signal'].iloc[-1]) else 0
            macd_histogram = macd_data['Histogram'].iloc[-1] if not pd.isna(macd_data['Histogram'].iloc[-1]) else 0
            
            # Analisi segnali MACD
            macd_signals = analyze_macd_signals(macd_data, df)
            
            # Calcola supporti e resistenze
            support_resistance = calculate_support_resistance(df)
            
            # Volume medio
            avg_volume = df['volume'].tail(20).mean()
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
            
            # Predizione AI
            basic_indicators = {
                'rsi': round(rsi, 1),
                'macd': round(macd, 6),
                'macd_signal': round(macd_signal, 6),
                'macd_histogram': round(macd_histogram, 6),
                'volume_ratio': round(volume_ratio, 2)
            }
            
            ai_prediction = ai_trading_prediction(basic_indicators, macd_signals, support_resistance, df, crypto_data)
            
            return {
                'rsi': round(rsi, 1),
                'macd': round(macd, 6),
                'macd_signal': round(macd_signal, 6),
                'macd_histogram': round(macd_histogram, 6),
                'volume_ratio': round(volume_ratio, 2),
                'macd_signals': macd_signals,
                'support_resistance': support_resistance,
                'ai_prediction': ai_prediction,
                'macd_data': macd_data  # Per i grafici
            }
        except Exception as e:
            logger.error(f"Errore calcolo indicatori: {e}")
            return {
                'rsi': 50.0,
                'macd': 0.0,
                'macd_signal': 0.0,
                'macd_histogram': 0.0,
                'volume_ratio': 1.0,
                'macd_signals': {'last_crossover': 'neutral', 'divergence': 'none', 'momentum': 'neutral'},
                'support_resistance': {'resistance': [], 'support': []},
                'ai_prediction': {'recommendation': 'HOLD', 'action': '⚪ HOLD', 'confidence': 0}
            }
    
    def generate_technical_suggestions(self, indicators: dict, price_data: dict) -> str:
        """Genera suggerimenti tecnici avanzati basati su indicatori multipli"""
        suggestions = []
        
        # Analisi RSI
        rsi = indicators.get('rsi', 50)
        if rsi > 70:
            suggestions.append("🔴 RSI ipercomprato - attendi correzione o esci dalle posizioni long")
        elif rsi < 30:
            suggestions.append("🟢 RSI ipervenduto - opportunità di acquisto o chiusura short")
        elif 45 <= rsi <= 55:
            suggestions.append("🟡 RSI neutro - momentum equilibrato")
        
        # Analisi MACD avanzata
        macd_signals = indicators.get('macd_signals', {})
        crossover = macd_signals.get('last_crossover', 'neutral')
        divergence = macd_signals.get('divergence', 'none')
        momentum = macd_signals.get('momentum', 'neutral')
        
        if crossover == 'bullish':
            suggestions.append("📈 MACD crossover bullish - segnale di acquisto confermato")
        elif crossover == 'bearish':
            suggestions.append("📉 MACD crossover bearish - segnale di vendita confermato")
        
        if divergence == 'bullish':
            suggestions.append("⚡ Divergenza bullish MACD - possibile inversione al rialzo")
        elif divergence == 'bearish':
            suggestions.append("⚡ Divergenza bearish MACD - possibile inversione al ribasso")
        
        # Analisi Supporti/Resistenze
        sr = indicators.get('support_resistance', {})
        current_price = price_data.get('price', 0)
        
        if sr.get('resistance'):
            nearest_resistance = min(sr['resistance'], key=lambda x: abs(x - current_price))
            resistance_distance = (nearest_resistance - current_price) / current_price
            if resistance_distance < 0.02:
                suggestions.append(f"🎯 Vicino alla resistenza ${nearest_resistance:.2f} - attenzione")
        
        if sr.get('support'):
            nearest_support = min(sr['support'], key=lambda x: abs(x - current_price))
            support_distance = (current_price - nearest_support) / current_price
            if support_distance < 0.02:
                suggestions.append(f"🛡️ Vicino al supporto ${nearest_support:.2f} - possibile rimbalzo")
        
        # Analisi Volume
        volume_ratio = indicators.get('volume_ratio', 1)
        if volume_ratio > 2:
            suggestions.append("� Volume molto elevato - movimento forte e significativo")
        elif volume_ratio > 1.5:
            suggestions.append("📊 Volume elevato - movimento confermato")
        elif volume_ratio < 0.5:
            suggestions.append("📊 Volume basso - movimento poco convincente")
        
        # Predizione AI integrata
        ai_pred = indicators.get('ai_prediction', {})
        confidence = ai_pred.get('confidence', 0)
        if confidence > 70:
            action = ai_pred.get('action', 'HOLD')
            suggestions.append(f"🤖 AI ad alta confidenza: {action}")
        
        return " | ".join(suggestions[:4])  # Limita a 4 suggerimenti principali
    
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
        """Genera grafico candlestick avanzato con supporti, resistenze e segnali MACD"""
        try:
            # Setup del grafico
            fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(14, 12), 
                                               gridspec_kw={'height_ratios': [3, 1, 1]})
            
            # Prendi solo ultimi 50 candles per leggibilità
            df_chart = df.tail(50).copy()
            chart_start_idx = len(df) - 50
            
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
            
            # Aggiungi supporti e resistenze
            if 'support_resistance' in indicators:
                sr = indicators['support_resistance']
                
                # Disegna livelli di resistenza
                for resistance in sr.get('resistance', []):
                    ax1.axhline(y=resistance, color='red', linestyle='--', alpha=0.7, linewidth=2)
                    ax1.text(45, resistance, f'R: {resistance:.2f}', color='red', fontweight='bold')
                
                # Disegna livelli di supporto
                for support in sr.get('support', []):
                    ax1.axhline(y=support, color='green', linestyle='--', alpha=0.7, linewidth=2)
                    ax1.text(45, support, f'S: {support:.2f}', color='green', fontweight='bold')
            
            # Aggiungi segnali MACD sul grafico principale
            if 'macd_signals' in indicators:
                macd_sigs = indicators['macd_signals']
                crossover_pos = macd_sigs.get('crossover_position', 0)
                
                if crossover_pos > chart_start_idx and crossover_pos < len(df):
                    chart_pos = crossover_pos - chart_start_idx
                    if 0 <= chart_pos < len(df_chart):
                        signal_price = df_chart.iloc[chart_pos]['close']
                        signal_type = macd_sigs.get('last_crossover', 'neutral')
                        
                        if signal_type == 'bullish':
                            ax1.scatter(chart_pos, signal_price, color='lime', s=100, marker='^', 
                                       label='MACD Buy Signal', zorder=5)
                        elif signal_type == 'bearish':
                            ax1.scatter(chart_pos, signal_price, color='red', s=100, marker='v', 
                                       label='MACD Sell Signal', zorder=5)
            
            # Aggiungi predizione AI
            if 'ai_prediction' in indicators:
                prediction = indicators['ai_prediction']
                action_color = 'green' if 'BUY' in prediction['action'] else \
                              'red' if 'SELL' in prediction['action'] else 'gray'
                
                ax1.text(0.02, 0.98, f"AI: {prediction['action']}\nConf: {prediction['confidence']}%", 
                        transform=ax1.transAxes, fontsize=11, fontweight='bold',
                        bbox=dict(boxstyle="round,pad=0.3", facecolor=action_color, alpha=0.7),
                        verticalalignment='top', color='white')
            
            ax1.set_title(f'{symbol} - Analisi Tecnica Avanzata', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Prezzo (USDT)', fontsize=12)
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            # RSI subplot con zone di trading
            rsi_data = calculate_rsi(df_chart['close'], 14)
            ax2.plot(range(len(rsi_data)), rsi_data, 'purple', linewidth=2)
            ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Ipercomprato (70)')
            ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Ipervenduto (30)')
            ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.5, label='Neutrale')
            
            # Evidenzia zone critiche RSI
            ax2.fill_between(range(len(rsi_data)), 70, 100, alpha=0.2, color='red', label='Zona Sell')
            ax2.fill_between(range(len(rsi_data)), 0, 30, alpha=0.2, color='green', label='Zona Buy')
            
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper right', fontsize=9)
            ax2.grid(True, alpha=0.3)
            
            # MACD subplot migliorato
            macd_data = indicators.get('macd_data', calculate_macd(df_chart['close']))
            ax3.plot(range(len(macd_data['MACD'])), macd_data['MACD'], 'blue', label='MACD', linewidth=2)
            ax3.plot(range(len(macd_data['Signal'])), macd_data['Signal'], 'red', label='Signal', linewidth=2)
            
            # Istogramma colorato
            histogram = macd_data['Histogram']
            colors = ['green' if h > 0 else 'red' for h in histogram]
            ax3.bar(range(len(histogram)), histogram, alpha=0.6, color=colors, label='Histogram')
            
            # Linea zero
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.8, linewidth=1)
            
            # Evidenzia crossover
            for i in range(1, len(macd_data['MACD'])):
                if (macd_data['MACD'].iloc[i] > macd_data['Signal'].iloc[i] and 
                    macd_data['MACD'].iloc[i-1] <= macd_data['Signal'].iloc[i-1]):
                    ax3.scatter(i, macd_data['MACD'].iloc[i], color='lime', s=50, marker='^', zorder=5)
                elif (macd_data['MACD'].iloc[i] < macd_data['Signal'].iloc[i] and 
                      macd_data['MACD'].iloc[i-1] >= macd_data['Signal'].iloc[i-1]):
                    ax3.scatter(i, macd_data['MACD'].iloc[i], color='red', s=50, marker='v', zorder=5)
            
            ax3.set_ylabel('MACD', fontsize=12)
            ax3.set_xlabel('Tempo (ore)', fontsize=12)
            ax3.legend(loc='upper right', fontsize=9)
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
        """Formatta il messaggio di risposta con predizioni AI"""
        symbol = crypto_data['symbol']
        price = crypto_data['price']
        change_24h = crypto_data['change_24h']
        volume_24h = crypto_data['volume_24h']
        
        # Emoji per variazione
        change_emoji = "🟢" if change_24h > 0 else "🔴" if change_24h < 0 else "🟡"
        change_sign = "+" if change_24h > 0 else ""
        
        # Predizione AI
        ai_pred = indicators.get('ai_prediction', {})
        
        message = f"""📊 **ANALISI SCALPING ULTRA-AGGRESSIVA {symbol}** (Bybit)

💰 **Prezzo attuale:** ${price:,.2f}
{change_emoji} **Variazione 24h:** {change_sign}{change_24h:.2f}%
📈 **Volume 24h:** ${volume_24h:,.0f}

🚀 **PREDIZIONE AI SCALPING:**
{ai_pred.get('action', '⚪ HOLD')} **{ai_pred.get('recommendation', 'HOLD')}**
⚡ **Direzione:** {ai_pred.get('direction', 'HOLD')} | **Leva:** {ai_pred.get('optimal_leverage', 1)}x
🎯 **Confidenza:** {ai_pred.get('confidence', 0)}% | **Timeframe:** {ai_pred.get('timeframe', 'N/A')}
💰 **Position Size:** {ai_pred.get('position_size', 'N/A')}

📊 **VOLATILITÀ MULTI-TF (Scalping):**
• Vol 5m: {ai_pred.get('volatility_5m', 0)}% | Vol 24h: {ai_pred.get('volatility_24h', 0)}%
• R/R: {ai_pred.get('risk_reward', 0)}:1 | Risk Level: {ai_pred.get('risk_level', 'N/A')}

📋 **Indicatori Tecnici:**
• RSI (14): {indicators.get('rsi', 'N/A')} {self._get_rsi_zone(indicators.get('rsi', 50))}
• MACD: {indicators.get('macd', 'N/A'):.6f}
• MACD Signal: {indicators.get('macd_signal', 'N/A'):.6f}
• Volume Ratio: {indicators.get('volume_ratio', 'N/A')}x

📈 **Segnali MACD:**"""

        # Aggiungi dettagli MACD
        macd_signals = indicators.get('macd_signals', {})
        crossover = macd_signals.get('last_crossover', 'neutral')
        divergence = macd_signals.get('divergence', 'none')
        momentum = macd_signals.get('momentum', 'neutral')
        
        crossover_emoji = "🟢" if crossover == 'bullish' else "🔴" if crossover == 'bearish' else "🟡"
        message += f"\n• Ultimo Crossover: {crossover_emoji} {crossover.upper()}"
        
        if divergence != 'none':
            div_emoji = "🟢" if divergence == 'bullish' else "🔴"
            message += f"\n• Divergenza: {div_emoji} {divergence.upper()}"
        
        momentum_emoji = "⬆️" if momentum == 'increasing' else "⬇️" if momentum == 'decreasing' else "➡️"
        message += f"\n• Momentum: {momentum_emoji} {momentum.upper()}"

        # Supporti e Resistenze
        sr = indicators.get('support_resistance', {})
        if sr.get('resistance') or sr.get('support'):
            message += "\n\n🎯 **Livelli Chiave:**"
            
            if sr.get('resistance'):
                message += f"\n• Resistenze: " + ", ".join([f"${r:.2f}" for r in sr['resistance'][:3]])
            
            if sr.get('support'):
                message += f"\n• Supporti: " + ", ".join([f"${s:.2f}" for s in sr['support'][:3]])

        # Segnali AI top
        ai_signals = ai_pred.get('signals', [])
        if ai_signals:
            message += "\n\n🧠 **Segnali AI:**"
            for signal in ai_signals[:3]:  # Top 3 segnali
                message += f"\n• {signal}"

        message += f"\n\n💡 **Analisi Tecnica:**\n{suggestions}"

        message += "\n\n📰 **Notizie Recenti:**"

        # Aggiungi news
        for i, article in enumerate(news, 1):
            message += f"\n• [{article['title']}]({article['url']})"
        
        message += f"\n\n📈 **Grafico con S/R e segnali MACD allegato**\n⏰ Aggiornato: {datetime.now().strftime('%H:%M:%S')}"
        
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
            indicators = self.calculate_technical_indicators(crypto_data['df'], crypto_data)
            
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
        message = """🤖 **Bot Analisi Crypto Avanzato PRO** 

**Comandi disponibili:**
• `/btc` - Analisi completa Bitcoin
• `/crypto <simbolo>` - Analisi crypto completa
• `/trade <simbolo>` - 🔥 **ANALISI TRADING PRO con LEVA**
• `/best` - 🚀 **TOP CRYPTO LONG/SHORT con LEVA**
• `/signals <simbolo>` - Segnali MACD avanzati  
• `/ai <simbolo>` - Predizione AI dettagliata

**� NUOVO: Scanner Crypto con Leva**
⚡ **SCANSIONE AUTOMATICA** di 30+ crypto principali
🎯 **RANKING INTELLIGENTE** Long/Short per sicurezza
💰 **LEVA OTTIMALE** per ogni opportunità
📊 **FILTRO CONFIDENZA** solo trade sicuri >65%
🧠 **AI SCORING** combinato per migliori setup

**Funzionalità Avanzate:**
📊 Prezzi real-time e variazioni 24h
📈 Indicatori tecnici (RSI, MACD + segnali)
🎯 Supporti e resistenze automatici
🤖 Predizioni AI con confidenza e direzione
� Calcolo leva ottimale (1x-10x)
�📰 Ultime notizie crypto
📊 Grafici professionali con segnali
💡 Strategie di trading complete
⚠️ Risk management professionale

**Esempi Trading PRO:**
`/best` - 🔥 **Migliori crypto LONG/SHORT ora**
`/trade BTC` - Setup completo Bitcoin con leva
`/trade ETH` - Analisi Ethereum + entry/exit
`/crypto SOL` - Analisi completa Solana
`/signals MATIC` - Segnali MACD avanzati

**Features Premium:**
🎯 Entry price preciso + stop loss calcolato
⚡ Leva ottimale basata su volatilità e confidenza
💰 Position sizing intelligente (% capitale)
📊 Take profit multipli con risk/reward
🧠 AI coaching per gestione trade
⚠️ Alert rischio e warning volatilità
🚀 Scanner automatico migliori opportunità

⚠️ **Disclaimer:** Questo bot fornisce analisi educative per trading. Non costituisce consulenza finanziaria. Usa sempre stop loss, gestisci il rischio e non investire più di quello che puoi permetterti di perdere."""

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /help"""
        await self.start_command(update, context)
    
    async def signals_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /signals <simbolo> per segnali MACD avanzati"""
        if not context.args:
            await update.message.reply_text(
                "❌ Uso corretto: /signals <simbolo>\nEsempio: /signals BTC"
            )
            return
            
        symbol = context.args[0].upper()
        
        try:
            waiting_msg = await update.message.reply_text(f"🔄 Analizzando segnali MACD per {symbol}...")
            
            # Recupera dati crypto con più candele per analisi MACD
            crypto_data = await self.get_crypto_data(symbol)
            df = crypto_data['df']
            
            # Estendi a 200 candele per analisi più accurata
            if len(df) >= 100:
                ohlcv = self.exchange.fetch_ohlcv(crypto_data['symbol'], '1h', limit=200)
                df_extended = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_extended['timestamp'] = pd.to_datetime(df_extended['timestamp'], unit='ms')
                df_extended.set_index('timestamp', inplace=True)
                crypto_data['df'] = df_extended
            
            # Calcola indicatori
            indicators = self.calculate_technical_indicators(crypto_data['df'], crypto_data)
            macd_signals = indicators['macd_signals']
            ai_pred = indicators['ai_prediction']
            
            # Messaggio dettagliato sui segnali MACD
            message = f"""📊 **Segnali MACD Avanzati - {symbol}**

💰 **Prezzo attuale:** ${crypto_data['price']:,.2f}

🎯 **SEGNALI MACD:**
• **Ultimo Crossover:** {self._get_crossover_emoji(macd_signals['last_crossover'])} {macd_signals['last_crossover'].upper()}
• **Divergenza:** {self._get_divergence_emoji(macd_signals['divergence'])} {macd_signals['divergence'].upper()}
• **Momentum:** {self._get_momentum_emoji(macd_signals['momentum'])} {macd_signals['momentum'].upper()}
• **Forza Segnale:** {macd_signals['signal_strength']:.6f}

🤖 **PREDIZIONE AI:**
{ai_pred['action']} **{ai_pred['recommendation']}**
• **Confidenza:** {ai_pred['confidence']}%
• **Livello Rischio:** {ai_pred['risk_level']}

📈 **STRATEGIA CONSIGLIATA:**"""

            # Aggiungi strategia basata sui segnali
            if macd_signals['last_crossover'] == 'bullish' and ai_pred['confidence'] > 60:
                message += "\n🟢 **ENTRY LONG:** Segnale di acquisto confermato"
                message += f"\n📊 Stop Loss: Sotto supporto più vicino"
                message += f"\n🎯 Take Profit: Verso resistenza più vicina"
            elif macd_signals['last_crossover'] == 'bearish' and ai_pred['confidence'] > 60:
                message += "\n🔴 **ENTRY SHORT:** Segnale di vendita confermato"
                message += f"\n📊 Stop Loss: Sopra resistenza più vicina"
                message += f"\n🎯 Take Profit: Verso supporto più vicino"
            else:
                message += "\n🟡 **HOLD:** Attendere segnali più chiari"
                message += f"\n⏱️ Monitorare crossover MACD e volumi"

            # Supporti e resistenze
            sr = indicators['support_resistance']
            if sr['support'] or sr['resistance']:
                message += "\n\n🎯 **LIVELLI CHIAVE:**"
                if sr['resistance']:
                    message += f"\n🔴 Resistenze: " + ", ".join([f"${r:.2f}" for r in sr['resistance'][:3]])
                if sr['support']:
                    message += f"\n🟢 Supporti: " + ", ".join([f"${s:.2f}" for s in sr['support'][:3]])

            message += f"\n\n⏰ Analisi: {datetime.now().strftime('%H:%M:%S')}"
            message += f"\n⚠️ *Sempre usa stop loss e gestisci il rischio*"

            await waiting_msg.delete()
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Errore segnali MACD {symbol}: {e}")
            await update.message.reply_text(f"❌ Errore nell'analisi dei segnali per {symbol}")

    async def trade_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /trade <simbolo> per analisi trading professionale con leva"""
        if not context.args:
            await update.message.reply_text(
                "❌ Uso corretto: /trade <simbolo>\nEsempio: /trade BTC"
            )
            return
            
        symbol = context.args[0].upper()
        await self._professional_trade_analysis(symbol, update, context)

    async def _professional_trade_analysis(self, symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analisi trading professionale completa"""
        try:
            waiting_msg = await update.message.reply_text(f"⚡ Analisi trading PRO per {symbol}...")
            
            # Recupera dati estesi per analisi più accurata
            crypto_data = await self.get_crypto_data(symbol)
            df = crypto_data['df']
            
            # Estendi dataset per analisi più precisa
            try:
                ohlcv = self.exchange.fetch_ohlcv(crypto_data['symbol'], '1h', limit=200)
                df_extended = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df_extended['timestamp'] = pd.to_datetime(df_extended['timestamp'], unit='ms')
                df_extended.set_index('timestamp', inplace=True)
                crypto_data['df'] = df_extended
                df = df_extended
            except:
                pass  # Usa dati esistenti se non riesce
            
            # Calcola indicatori avanzati
            indicators = self.calculate_technical_indicators(df)
            ai_pred = indicators['ai_prediction']
            macd_signals = indicators['macd_signals']
            sr = indicators['support_resistance']
            
            current_price = crypto_data['price']
            
            # Calcola entry preciso e gestione rischio
            entry_price = current_price
            stop_loss = 0
            take_profit_1 = 0
            take_profit_2 = 0
            
            if ai_pred['direction'] == 'LONG':
                # Entry LONG
                if sr.get('support'):
                    nearest_support = min(sr['support'], key=lambda x: abs(x - current_price))
                    stop_loss = nearest_support * 0.995  # 0.5% sotto supporto
                else:
                    stop_loss = current_price * 0.97  # 3% stop loss di default
                
                if sr.get('resistance'):
                    resistances = sorted(sr['resistance'])[:2]
                    take_profit_1 = resistances[0] * 0.995 if len(resistances) > 0 else current_price * 1.05
                    take_profit_2 = resistances[1] * 0.995 if len(resistances) > 1 else current_price * 1.10
                else:
                    take_profit_1 = current_price * 1.05
                    take_profit_2 = current_price * 1.10
                    
            elif ai_pred['direction'] == 'SHORT':
                # Entry SHORT
                if sr.get('resistance'):
                    nearest_resistance = min(sr['resistance'], key=lambda x: abs(x - current_price))
                    stop_loss = nearest_resistance * 1.005  # 0.5% sopra resistenza
                else:
                    stop_loss = current_price * 1.03  # 3% stop loss di default
                
                if sr.get('support'):
                    supports = sorted(sr['support'], reverse=True)[:2]
                    take_profit_1 = supports[0] * 1.005 if len(supports) > 0 else current_price * 0.95
                    take_profit_2 = supports[1] * 1.005 if len(supports) > 1 else current_price * 0.90
                else:
                    take_profit_1 = current_price * 0.95
                    take_profit_2 = current_price * 0.90
            
            # Calcola percentuali di rischio/guadagno
            if ai_pred['direction'] != 'HOLD':
                risk_pct = abs(entry_price - stop_loss) / entry_price * 100
                reward1_pct = abs(take_profit_1 - entry_price) / entry_price * 100
                reward2_pct = abs(take_profit_2 - entry_price) / entry_price * 100
                risk_reward_1 = reward1_pct / risk_pct if risk_pct > 0 else 0
                risk_reward_2 = reward2_pct / risk_pct if risk_pct > 0 else 0
            else:
                risk_pct = reward1_pct = reward2_pct = 0
                risk_reward_1 = risk_reward_2 = 0

            # Messaggio di analisi professionale
            message = f"""⚡ **ANALISI TRADING PROFESSIONALE - {symbol}**

💰 **SITUAZIONE ATTUALE:**
• Prezzo: ${current_price:,.2f}
• Volatilità 24h: {ai_pred['volatility']}%
• Volume Ratio: {indicators.get('volume_ratio', 1):.1f}x

🤖 **RACCOMANDAZIONE AI:**
{ai_pred['action']} **{ai_pred['recommendation']}**
• **Direzione:** {ai_pred['direction']}
• **Confidenza Trading:** {ai_pred['trade_confidence']}
• **Score AI:** {ai_pred['score']}/12

⚡ **SETUP TRADING OTTIMALE:**"""

            if ai_pred['direction'] != 'HOLD':
                message += f"""
📊 **ENTRY:** ${entry_price:,.2f}
🛡️ **STOP LOSS:** ${stop_loss:,.2f} (-{risk_pct:.1f}%)
🎯 **TAKE PROFIT 1:** ${take_profit_1:,.2f} (+{reward1_pct:.1f}%) - R/R {risk_reward_1:.1f}
🚀 **TAKE PROFIT 2:** ${take_profit_2:,.2f} (+{reward2_pct:.1f}%) - R/R {risk_reward_2:.1f}

💎 **GESTIONE CAPITALE:**
• **Leva Ottimale:** {ai_pred['optimal_leverage']}x
• **Size Posizione:** {ai_pred['position_size']}
• **Rischio per Trade:** {risk_pct:.1f}%
• **Quality Entry:** {ai_pred['entry_quality']}/2 ⭐"""
                
                # Strategia di gestione
                message += f"\n\n📋 **STRATEGIA GESTIONE:**"
                if ai_pred['trade_confidence'] == 'MOLTO ALTA':
                    message += f"\n• Entry: 100% all'entry price"
                    message += f"\n• TP1: Chiudi 50% posizione"
                    message += f"\n• TP2: Chiudi resto + trail stop"
                elif ai_pred['trade_confidence'] == 'ALTA':
                    message += f"\n• Entry: 70% all'entry, 30% su pullback"
                    message += f"\n• TP1: Chiudi 40% posizione"
                    message += f"\n• TP2: Chiudi resto gradualmente"
                else:
                    message += f"\n• Entry: 50% all'entry, 50% su conferma"
                    message += f"\n• TP1: Chiudi 60% posizione"
                    message += f"\n• Usa stop loss stretto"
                    
            else:
                message += f"\n🟡 **NESSUN TRADE CONSIGLIATO**"
                message += f"\n• Segnali contrastanti o poco chiari"
                message += f"\n• Attendere setup migliore"
                message += f"\n• Monitorare per prossime opportunità"

            # Top segnali AI
            message += f"\n\n🧠 **TOP SEGNALI AI:**"
            for i, signal in enumerate(ai_pred['signals'][:4], 1):
                message += f"\n{i}. {signal}"

            # Condizioni di mercato
            message += f"\n\n📊 **CONDIZIONI MERCATO:**"
            message += f"\n• RSI: {indicators.get('rsi', 50):.1f} {self._get_rsi_zone(indicators.get('rsi', 50))}"
            
            crossover = macd_signals.get('last_crossover', 'neutral')
            crossover_emoji = "🟢" if crossover == 'bullish' else "🔴" if crossover == 'bearish' else "🟡"
            message += f"\n• MACD: {crossover_emoji} {crossover.upper()}"
            
            if sr.get('support'):
                nearest_support = min(sr['support'], key=lambda x: abs(x - current_price))
                support_dist = abs(current_price - nearest_support) / current_price * 100
                message += f"\n• Supporto: ${nearest_support:.2f} ({support_dist:.1f}% away)"
                
            if sr.get('resistance'):
                nearest_resistance = min(sr['resistance'], key=lambda x: abs(x - current_price))
                resist_dist = abs(nearest_resistance - current_price) / current_price * 100
                message += f"\n• Resistenza: ${nearest_resistance:.2f} ({resist_dist:.1f}% away)"

            # Warning e note importanti
            message += f"\n\n⚠️ **AVVERTENZE TRADING:**"
            if ai_pred['volatility'] > 6:
                message += f"\n• 🔥 ALTA VOLATILITÀ - Riduci leva e size!"
            if ai_pred['optimal_leverage'] > 5:
                message += f"\n• ⚡ Leva alta - Solo per trader esperti"
            if ai_pred['confidence'] < 60:
                message += f"\n• 🤔 Confidenza media - Prudenza consigliata"
                
            message += f"\n• 📖 Sempre usa stop loss FISSO"
            message += f"\n• 💰 Non rischiare più del 2-3% del capitale"
            message += f"\n• 📊 Monitora price action per conferme"

            message += f"\n\n⏰ Analisi: {datetime.now().strftime('%H:%M:%S')}"
            message += f"\n⚠️ *Non è consulenza finanziaria - Trade a tuo rischio*"

            await waiting_msg.delete()
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Errore analisi trading {symbol}: {e}")
            await update.message.reply_text(f"❌ Errore nell'analisi trading per {symbol}")

    async def best_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /best per le migliori crypto da tradare con leva"""
        await self._analyze_best_crypto_trades(update, context)

    async def _analyze_best_crypto_trades(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analizza le migliori crypto per trading LONG e SHORT con leva"""
        try:
            waiting_msg = await update.message.reply_text("🔍 Scansionando le migliori crypto per trading con leva...")
            
            # Lista estesa con crypto di nicchia e alto potenziale
            top_symbols = [
                # Top crypto principali
                'BTC', 'ETH', 'BNB', 'XRP', 'ADA', 'DOGE', 'SOL', 'MATIC', 
                'DOT', 'AVAX', 'SHIB', 'UNI', 'LINK', 'LTC', 'BCH', 'XLM',
                'ALGO', 'VET', 'FIL', 'TRX', 'ETC', 'THETA', 'AAVE', 'ATOM',
                
                # Layer 1/Layer 2 di nicchia con alto potenziale
                'ICP', 'NEAR', 'FTM', 'FLOW', 'ROSE', 'ONE', 'ZIL', 'WAVES',
                'QTUM', 'IOTA', 'APT', 'SUI', 'SEI', 'INJ', 'TIA',
                
                # DeFi ad alta volatilità 
                'CRV', 'COMP', 'SUSHI', 'YFI', 'MKR', 'SNX', 'BAL', 'KNC', 'LRC',
                
                # Gaming/Metaverse (movimenti forti)
                'MANA', 'SAND', 'AXS', 'ENJ', 'GALA', 'TLM', 'ALICE', 'CHR', 'PYR',
                
                # AI/Data tokens (trend emergenti)
                'FET', 'OCEAN', 'RNDR', 'GRT', 'NKN',
                
                # Storage/Infrastructure di nicchia
                'AR', 'STORJ', 'SC', 'HNT', 'IOTX',
                
                # Privacy coins volatili
                'XMR', 'ZEC', 'DASH', 'SCRT',
                
                # Meme coins per swing trading
                'PEPE', 'FLOKI', 'BONK', 'WIF'
            ]
            
            long_opportunities = []
            short_opportunities = []
            analyzed_count = 0
            
            for symbol in top_symbols:
                try:
                    # Aggiorna messaggio di progresso ogni 10 crypto
                    if analyzed_count % 10 == 0:
                        await waiting_msg.edit_text(f"🔍 Analizzando crypto... {analyzed_count}/{len(top_symbols)}\n🔎 Attualmente: {symbol}")
                    
                    # Recupera dati crypto
                    crypto_data = await self.get_crypto_data(symbol)
                    
                    # Calcola indicatori tecnici
                    indicators = self.calculate_technical_indicators(crypto_data['df'], crypto_data)
                    ai_pred = indicators['ai_prediction']
                    
                    # Filtra solo crypto con alta confidenza e buona leva
                    if ai_pred['confidence'] > 65 and ai_pred['optimal_leverage'] >= 2:
                        
                        # Calcola score combinato per ranking
                        combined_score = (
                            ai_pred['score'] * 0.4 +  # 40% score AI
                            (ai_pred['confidence'] / 10) * 0.3 +  # 30% confidenza normalizzata
                            (ai_pred['optimal_leverage'] / 2) * 0.2 +  # 20% leva ottimale
                            ai_pred['entry_quality'] * 0.1  # 10% qualità entry
                        )
                        
                        crypto_info = {
                            'symbol': symbol,
                            'price': crypto_data['price'],
                            'change_24h': crypto_data['change_24h'],
                            'direction': ai_pred['direction'],
                            'recommendation': ai_pred['recommendation'],
                            'action': ai_pred['action'],
                            'confidence': ai_pred['confidence'],
                            'score': ai_pred['score'],
                            'optimal_leverage': ai_pred['optimal_leverage'],
                            'position_size': ai_pred['position_size'],
                            'volatility': ai_pred['volatility'],
                            'risk_reward': ai_pred['risk_reward'],
                            'trade_confidence': ai_pred['trade_confidence'],
                            'combined_score': combined_score,
                            'top_signals': ai_pred['signals'][:2]  # Top 2 segnali
                        }
                        
                        # Separa per LONG e SHORT
                        if ai_pred['direction'] == 'LONG':
                            long_opportunities.append(crypto_info)
                        elif ai_pred['direction'] == 'SHORT':
                            short_opportunities.append(crypto_info)
                    
                    analyzed_count += 1
                    
                except Exception as e:
                    logger.error(f"Errore analisi {symbol}: {e}")
                    analyzed_count += 1
                    continue
            
            # Ordina per combined_score (dal migliore al peggiore)
            long_opportunities.sort(key=lambda x: x['combined_score'], reverse=True)
            short_opportunities.sort(key=lambda x: abs(x['combined_score']), reverse=True)
            
            # Prendi solo i top 8 per categoria
            top_longs = long_opportunities[:8]
            top_shorts = short_opportunities[:8]
            
            # Crea messaggio con i risultati
            current_time = datetime.now().strftime('%H:%M:%S')
            
            message = f"""🔥 **TOP CRYPTO TRADING CON LEVA** 
⏰ Scansione completata: {current_time}
📊 Analizzate: {analyzed_count} crypto | Filtrate: Confidenza >65%

🟢 **MIGLIORI OPPORTUNITÀ LONG:**"""
            
            if top_longs:
                for i, crypto in enumerate(top_longs, 1):
                    confidence_emoji = "🔥" if crypto['confidence'] > 80 else "⚡" if crypto['confidence'] > 70 else "✅"
                    leva_emoji = "🚀" if crypto['optimal_leverage'] >= 5 else "📈"
                    
                    message += f"""
{i}. **{crypto['symbol']}** ${crypto['price']:,.2f} ({crypto['change_24h']:+.1f}%)
   {confidence_emoji} **{crypto['recommendation']}** | Conf: {crypto['confidence']}%
   {leva_emoji} Leva: {crypto['optimal_leverage']}x | Size: {crypto['position_size'].split('(')[0]}
   💎 Score: {crypto['score']}/12 | R/R: {crypto['risk_reward']}:1
   🧠 {crypto['top_signals'][0] if crypto['top_signals'] else 'Segnale forte'}"""
            else:
                message += "\n❌ Nessuna opportunità LONG sicura trovata"
            
            message += f"\n\n🔴 **MIGLIORI OPPORTUNITÀ SHORT:**"
            
            if top_shorts:
                for i, crypto in enumerate(top_shorts, 1):
                    confidence_emoji = "🔥" if crypto['confidence'] > 80 else "⚡" if crypto['confidence'] > 70 else "✅"
                    leva_emoji = "🚀" if crypto['optimal_leverage'] >= 5 else "📉"
                    
                    message += f"""
{i}. **{crypto['symbol']}** ${crypto['price']:,.2f} ({crypto['change_24h']:+.1f}%)
   {confidence_emoji} **{crypto['recommendation']}** | Conf: {crypto['confidence']}%
   {leva_emoji} Leva: {crypto['optimal_leverage']}x | Size: {crypto['position_size'].split('(')[0]}
   💎 Score: {crypto['score']}/12 | R/R: {crypto['risk_reward']}:1
   🧠 {crypto['top_signals'][0] if crypto['top_signals'] else 'Segnale forte'}"""
            else:
                message += "\n❌ Nessuna opportunità SHORT sicura trovata"
            
            # Aggiungi statistiche e avvertenze
            message += f"\n\n📊 **STATISTICHE SCANSIONE:**"
            message += f"\n• Total LONG sicuri: {len(top_longs)}"
            message += f"\n• Total SHORT sicuri: {len(top_shorts)}"
            message += f"\n• Confidenza media LONG: {sum(c['confidence'] for c in top_longs)/len(top_longs):.1f}%" if top_longs else "\n• Confidenza media LONG: N/A"
            message += f"\n• Confidenza media SHORT: {sum(c['confidence'] for c in top_shorts)/len(top_shorts):.1f}%" if top_shorts else "\n• Confidenza media SHORT: N/A"
            
            message += f"\n\n💡 **CONSIGLI OPERATIVI:**"
            if top_longs or top_shorts:
                message += f"\n• Inizia con le crypto in top 3 di ogni categoria"
                message += f"\n• Usa sempre stop loss sui supporti/resistenze"
                message += f"\n• Non superare il 3% del capitale per trade"
                message += f"\n• Per leva >5x riduci la position size"
                message += f"\n• Monitora volatilità prima di entrare"
            else:
                message += f"\n• Mercato attualmente incerto per trading con leva"
                message += f"\n• Attendi setup più chiari prima di tradare"
                message += f"\n• Considera strategie DCA per accumulo"
            
            message += f"\n\n🔄 **COMANDI RAPIDI:**"
            if top_longs:
                message += f"\n• `/trade {top_longs[0]['symbol']}` - Analisi completa migliore LONG"
            if top_shorts:
                message += f"\n• `/trade {top_shorts[0]['symbol']}` - Analisi completa migliore SHORT"
            
            message += f"\n\n⚠️ **DISCLAIMER:** Analisi basata su AI e indicatori tecnici. Non è consulenza finanziaria. Trading con leva comporta rischi elevati."
            
            await waiting_msg.delete()
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Errore analisi best crypto: {e}")
            try:
                await waiting_msg.delete()
            except:
                pass
            await update.message.reply_text("❌ Errore durante l'analisi delle migliori crypto. Riprova tra qualche minuto.")

    async def ai_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Comando /ai <simbolo> per predizione AI specifica"""
        if not context.args:
            await update.message.reply_text(
                "❌ Uso corretto: /ai <simbolo>\nEsempio: /ai ETH"
            )
            return
            
        symbol = context.args[0].upper()
        await self._ai_analysis(symbol, update, context)

    async def _ai_analysis(self, symbol: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Analisi AI dettagliata per un simbolo"""
        try:
            waiting_msg = await update.message.reply_text(f"🤖 AI sta analizzando {symbol}...")
            
            crypto_data = await self.get_crypto_data(symbol)
            indicators = self.calculate_technical_indicators(crypto_data['df'], crypto_data)
            ai_pred = indicators['ai_prediction']
            
            message = f"""🤖 **Analisi AI Dettagliata - {symbol}**

💰 **Prezzo:** ${crypto_data['price']:,.2f}
📊 **Variazione 24h:** {crypto_data['change_24h']:+.2f}%

🧠 **PREDIZIONE AI:**
{ai_pred['action']} **{ai_pred['recommendation']}**

📊 **METRICHE:**
• **Confidenza:** {ai_pred['confidence']}%
• **Score:** {ai_pred['score']}/10
• **Rischio:** {ai_pred['risk_level']}

🔍 **SEGNALI IDENTIFICATI:**"""

            for i, signal in enumerate(ai_pred['signals'], 1):
                message += f"\n{i}. {signal}"

            # Aggiungi raccomandazione temporale
            confidence = ai_pred['confidence']
            if confidence > 80:
                message += "\n\n⚡ **AZIONE IMMEDIATA CONSIGLIATA**"
            elif confidence > 60:
                message += "\n\n⏰ **AZIONE NELLE PROSSIME ORE**"
            elif confidence > 40:
                message += "\n\n📅 **MONITORARE NEI PROSSIMI GIORNI**"
            else:
                message += "\n\n🤷 **SITUAZIONE INCERTA - ATTENDERE**"

            message += f"\n\n⏰ {datetime.now().strftime('%H:%M:%S')}"
            message += f"\n⚠️ *Questa è solo un'analisi AI, non consulenza finanziaria*"

            await waiting_msg.delete()
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            
        except Exception as e:
            logger.error(f"Errore AI {symbol}: {e}")
            await update.message.reply_text(f"❌ Errore nell'analisi AI per {symbol}")

    def _get_crossover_emoji(self, crossover):
        """Emoji per crossover MACD"""
        return "🟢" if crossover == 'bullish' else "🔴" if crossover == 'bearish' else "🟡"
    
    def _get_divergence_emoji(self, divergence):
        """Emoji per divergenza"""
        return "🟢" if divergence == 'bullish' else "🔴" if divergence == 'bearish' else "➡️"
    
    def _get_momentum_emoji(self, momentum):
        """Emoji per momentum"""
        return "⬆️" if momentum == 'increasing' else "⬇️" if momentum == 'decreasing' else "➡️"
    
    def run(self):
        """Avvia il bot"""
        # Crea applicazione con timeouts configurati
        application = Application.builder().token(self.telegram_token).build()
        
        # Aggiungi handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("help", self.help_command))
        application.add_handler(CommandHandler("btc", self.btc_command))
        application.add_handler(CommandHandler("crypto", self.crypto_command))
        application.add_handler(CommandHandler("trade", self.trade_command))
        application.add_handler(CommandHandler("best", self.best_command))
        application.add_handler(CommandHandler("signals", self.signals_command))
        application.add_handler(CommandHandler("ai", self.ai_command))
        
        # Avvia bot con gestione errori
        logger.info("🚀 Bot MACD Trading avviato con funzionalità AI!")
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

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Handler per health check del servizio"""
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Bot is running!')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Silenzioso per non sporcare i logs
        pass

def start_health_server():
    """Avvia server per health check (richiesto da Render)"""
    port = int(os.getenv('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    logger.info(f"🌐 Server health check avviato sulla porta {port}")
    server.serve_forever()

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
    
    # Avvia server health check in thread separato
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    
    # Crea e avvia bot
    bot = CryptoAnalysisBot(telegram_token, cryptopanic_token)
    bot.run()

if __name__ == "__main__":
    main()
