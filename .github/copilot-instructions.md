# Copilot Instructions for Crypto Analysis Bot

<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

## Project Overview
This is a Telegram bot for cryptocurrency analysis that provides:
- Real-time crypto prices and 24h changes
- Technical indicators (RSI, MACD, volume analysis)
- Latest news with clickable links
- Candlestick charts with technical overlays
- Technical suggestions and market insights

## Key Technologies
- Python with python-telegram-bot for Telegram integration
- ccxt library for Binance API data
- pandas-ta for technical indicators calculation
- matplotlib/plotly for chart generation
- CryptoPanic API for news fetching
- Designed for Replit hosting (free tier compatible)

## Code Style Guidelines
- Use async/await for API calls and bot operations
- Implement proper error handling for API failures
- Keep functions modular and well-documented
- Use environment variables for API keys and sensitive data
- Format messages with clear emoji indicators and readable structure
- Optimize for memory usage (Replit constraints)

## Bot Commands Structure
- `/btc` - Quick Bitcoin analysis
- `/crypto <symbol>` - Analysis for any cryptocurrency
- Response includes: price, 24h change, RSI, MACD, volume, news, technical suggestions

## API Integration Notes
- Binance API for market data (free tier)
- CryptoPanic API for news (free tier)
- Implement rate limiting and error recovery
- Cache data when possible to reduce API calls
