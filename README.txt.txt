ALTER USER postgres PASSWORD 'trading123';
CREATE DATABASE trading_db;

# Step 1: Go to project folder
cd ~/trading-dashboard

# Step 2: Activate virtual environment
source venv/bin/activate

# Step 3: Now you can run your Python scripts
python backend/test_binance.py

Database connection command
psql -h localhost -U postgres -d trading_db
trading123

📋 PHASE 4: FULL AUTOMATION SYSTEM
Step 1: Auto Candle Fetcher

Fetch new candles from Binance API every 15 minutes
Fetch for all symbols (BTC/USDT, ETH/USDT, SOL/USDT)
Fetch for all timeframes (15m, 1h, 4h, 1d)
Store in candles table
Handle duplicates (skip existing candles)

Step 2: Auto Indicator Calculator

Run all 11 indicators on newly fetched candles
Calculate: RSI, MACD, EMA Stack, Bollinger Bands, ADX, Volume Analysis, ATR, OBV, VWAP, SuperTrend (2 configs)
Store in indicators table
Update existing indicators if candle is recent

Step 3: Auto Signal Generator

Generate signals from updated indicators
Calculate scoring system (A-BUY, BUY, WATCH, CAUTION, SELL)
Store in signals table
Auto-create entries from new BUY/A-BUY signals

Step 4: Auto Entry Updater

Fetch active entries from entry_tracking table
Update with latest candle prices
Check validation, exits, signal-based exits, trailing stops
Update database with new status

Step 5: Scheduler (Cron Job)

Run Steps 1-4 every 15 minutes
Log execution times and errors
Send alerts on failures
System becomes fully automated