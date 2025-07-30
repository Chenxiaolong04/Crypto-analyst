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

def ai_trading_prediction(indicators: dict, macd_signals: dict, support_resistance: dict, df: pd.DataFrame) -> dict:
    """Sistema AI per predizione trading basato su indicatori multipli"""
    try:
        score = 0
        signals = []
        confidence = 0
        
        current_price = df['close'].iloc[-1]
        
        # Analisi RSI (peso: 20%)
        rsi = indicators['rsi']
        if rsi < 30:
            score += 2
            signals.append("RSI ipervenduto (bullish)")
        elif rsi > 70:
            score -= 2
            signals.append("RSI ipercomprato (bearish)")
        elif 40 <= rsi <= 60:
            score += 0.5
            signals.append("RSI neutrale (stabile)")
        
        # Analisi MACD (peso: 30%)
        if macd_signals['last_crossover'] == 'bullish':
            score += 3
            signals.append("MACD crossover bullish")
        elif macd_signals['last_crossover'] == 'bearish':
            score -= 3
            signals.append("MACD crossover bearish")
        
        if macd_signals['divergence'] == 'bullish':
            score += 2
            signals.append("Divergenza bullish MACD")
        elif macd_signals['divergence'] == 'bearish':
            score -= 2
            signals.append("Divergenza bearish MACD")
        
        if macd_signals['momentum'] == 'increasing' and macd_signals['histogram_value'] > 0:
            score += 1
            signals.append("Momentum MACD crescente")
        elif macd_signals['momentum'] == 'decreasing' and macd_signals['histogram_value'] < 0:
            score -= 1
            signals.append("Momentum MACD decrescente")
        
        # Analisi Supporti/Resistenze (peso: 25%)
        if support_resistance['support']:
            nearest_support = min(support_resistance['support'], key=lambda x: abs(x - current_price))
            support_distance = (current_price - nearest_support) / current_price
            
            if support_distance < 0.02:  # Vicino al supporto (2%)
                score += 2
                signals.append(f"Vicino al supporto ({nearest_support:.2f})")
        
        if support_resistance['resistance']:
            nearest_resistance = min(support_resistance['resistance'], key=lambda x: abs(x - current_price))
            resistance_distance = (nearest_resistance - current_price) / current_price
            
            if resistance_distance < 0.02:  # Vicino alla resistenza (2%)
                score -= 2
                signals.append(f"Vicino alla resistenza ({nearest_resistance:.2f})")
        
        # Analisi Volume (peso: 15%)
        volume_ratio = indicators.get('volume_ratio', 1)
        if volume_ratio > 1.5:
            score += 1
            signals.append("Volume elevato")
        elif volume_ratio < 0.7:
            score -= 0.5
            signals.append("Volume basso")
        
        # Analisi Trend (peso: 10%)
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        sma_50 = df['close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else sma_20
        
        if current_price > sma_20 > sma_50:
            score += 1
            signals.append("Trend rialzista")
        elif current_price < sma_20 < sma_50:
            score -= 1
            signals.append("Trend ribassista")
        
        # Calcola confidenza (0-100%)
        max_score = 10
        confidence = min(100, abs(score) / max_score * 100)
        
        # Determina raccomandazione
        if score >= 3:
            recommendation = "STRONG LONG"
            action = "🟢 BUY"
        elif score >= 1:
            recommendation = "LONG"
            action = "🟡 WEAK BUY"
        elif score <= -3:
            recommendation = "STRONG SHORT"
            action = "🔴 SELL"
        elif score <= -1:
            recommendation = "SHORT"
            action = "🟡 WEAK SELL"
        else:
            recommendation = "HOLD"
            action = "⚪ HOLD"
        
        return {
            'recommendation': recommendation,
            'action': action,
            'score': score,
            'confidence': round(confidence, 1),
            'signals': signals[:5],  # Top 5 segnali
            'risk_level': 'HIGH' if confidence > 80 else 'MEDIUM' if confidence > 50 else 'LOW'
        }
        
    except Exception as e:
        logger.error(f"Errore predizione AI: {e}")
        return {
            'recommendation': 'HOLD',
            'action': '⚪ HOLD',
            'score': 0,
            'confidence': 0,
            'signals': ['Errore nell\'analisi'],
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
        """Recupera dati crypto da Bybit"""
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
            
            ai_prediction = ai_trading_prediction(basic_indicators, macd_signals, support_resistance, df)
            
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
        
        message = f"""📊 **Analisi Avanzata {symbol}** (Bybit)

💰 **Prezzo attuale:** ${price:,.2f}
{change_emoji} **Variazione 24h:** {change_sign}{change_24h:.2f}%
📈 **Volume 24h:** ${volume_24h:,.0f}

🤖 **PREDIZIONE AI:**
{ai_pred.get('action', '⚪ HOLD')} **{ai_pred.get('recommendation', 'HOLD')}**
� **Confidenza:** {ai_pred.get('confidence', 0)}% | **Rischio:** {ai_pred.get('risk_level', 'UNKNOWN')}

�📋 **Indicatori Tecnici:**
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
        message = """🤖 **Bot Analisi Crypto Avanzato** 

**Comandi disponibili:**
• `/btc` - Analisi completa Bitcoin
• `/crypto <simbolo>` - Analisi crypto completa
• `/signals <simbolo>` - Segnali MACD avanzati  
• `/ai <simbolo>` - Predizione AI dettagliata

**Funzionalità Avanzate:**
📊 Prezzi real-time e variazioni 24h
📈 Indicatori tecnici (RSI, MACD + segnali)
🎯 Supporti e resistenze automatici
🤖 Predizioni AI con confidenza
📰 Ultime notizie crypto
📊 Grafici professionali con segnali
💡 Strategie di trading intelligenti

**Esempi:**
`/crypto ETH` - Analisi completa Ethereum
`/signals BTC` - Segnali MACD Bitcoin  
`/ai SOL` - Predizione AI Solana

**Nuove Features:**
🎯 Tracciamento supporti/resistenze sui grafici
⚡ Segnali crossover MACD in tempo reale
🧠 Sistema AI per predizioni long/short
📊 Analisi divergenze e momentum

⚠️ **Disclaimer:** Questo bot fornisce solo informazioni educative. Non costituisce consulenza finanziaria. Usa sempre stop loss e gestisci il rischio."""

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
            indicators = self.calculate_technical_indicators(crypto_data['df'])
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
            indicators = self.calculate_technical_indicators(crypto_data['df'])
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
