"""
Add New Symbol - Universal Data Fetcher
Author: Your Trading System
Purpose: Fetch data for ANY crypto coin and calculate ALL indicators

This script:
1. Accepts any Binance crypto pair
2. Fetches 3 months of historical data for ALL timeframes (15m, 1h, 1d)
3. Calculates ALL indicators (RSI, MACD, EMA, BB)
4. Ready to use in dashboard

Usage:
    python backend/add_new_symbol.py SOL/USDT
    python backend/add_new_symbol.py ADA/USDT
    python backend/add_new_symbol.py MATIC/USDT
"""

import sys
import ccxt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import time

# Import all indicator calculators
from indicators.rsi import RSICalculator
from indicators.macd import MACDCalculator
from indicators.ema import EMACalculator
from indicators.bollinger_bands import BollingerBandsCalculator

def fetch_historical_batches(symbol, timeframe, days=90):
    """
    Fetch historical data in batches (handles Binance 1000 candle limit)
    
    Args:
        symbol: Trading pair (e.g., 'SOL/USDT')
        timeframe: Candle timeframe ('15m', '1h', '1d')
        days: Number of days to fetch (default 90)
    
    Returns:
        DataFrame with all OHLCV data
    """
    print(f"\n📡 Fetching {days} days of {timeframe} data for {symbol}...")
    
    try:
        # Connect to Binance
        exchange = ccxt.binance()
        
        # Calculate timeframe duration in milliseconds
        timeframe_duration = {
            '15m': 15 * 60 * 1000,      # 15 minutes in ms
            '1h': 60 * 60 * 1000,       # 1 hour in ms
            '4h': 4 * 60 * 60 * 1000,   # 4 hours in ms
            '1d': 24 * 60 * 60 * 1000   # 1 day in ms
        }
        
        if timeframe not in timeframe_duration:
            print(f"  ✗ Unsupported timeframe: {timeframe}")
            return pd.DataFrame()
        
        duration = timeframe_duration[timeframe]
        
        # Calculate start time (90 days ago)
        now = int(datetime.now().timestamp() * 1000)
        start_time = now - (days * 24 * 60 * 60 * 1000)
        
        # Calculate total candles needed
        total_candles_needed = int((now - start_time) / duration)
        batches_needed = (total_candles_needed // 1000) + 1
        
        print(f"  📊 Need ~{total_candles_needed:,} candles")
        print(f"  🔄 Will fetch in {batches_needed} batches (1000 candles each)")
        
        # Fetch data in batches
        all_data = []
        current_time = start_time
        batch_num = 1
        
        while current_time < now and batch_num <= batches_needed:
            try:
                # Fetch 1000 candles starting from current_time
                print(f"     Batch {batch_num}/{batches_needed}...", end='')
                
                ohlcv = exchange.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=current_time,
                    limit=1000
                )
                
                if not ohlcv:
                    print(" No data")
                    break
                
                print(f" ✓ Got {len(ohlcv)} candles")
                
                # Add to collection
                all_data.extend(ohlcv)
                
                # Move to next batch (start after last candle)
                last_timestamp = ohlcv[-1][0]
                current_time = last_timestamp + duration
                
                batch_num += 1
                
                # Small delay to respect rate limits
                time.sleep(0.2)
                
            except Exception as e:
                print(f" ✗ Error: {e}")
                break
        
        if not all_data:
            print(f"  ✗ No data fetched")
            return pd.DataFrame()
        
        # Convert to DataFrame
        df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Remove duplicates (can happen at batch boundaries)
        df = df.drop_duplicates(subset=['timestamp'], keep='first')
        
        # Add datetime column
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Add symbol and timeframe
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        # Sort by timestamp
        df = df.sort_values('timestamp').reset_index(drop=True)
        
        print(f"  ✓ Fetched {len(df):,} candles successfully!")
        print(f"     Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"     Latest price: ${df['close'].iloc[-1]:,.2f}")
        
        return df
    
    except Exception as e:
        print(f"  ✗ Error fetching data: {e}")
        return pd.DataFrame()

def store_candles_batch(df):
    """
    Store candles in database (optimized for large datasets)
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        Tuple (inserted_count, duplicate_count)
    """
    if df is None or len(df) == 0:
        return 0, 0
    
    print(f"  💾 Storing {len(df):,} candles in database...")
    
    try:
        inserted_count = 0
        duplicate_count = 0
        
        # Store in batches of 100 for better performance
        batch_size = 100
        total_batches = (len(df) // batch_size) + 1
        
        with engine.connect() as connection:
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i + batch_size]
                batch_num = (i // batch_size) + 1
                
                if batch_num % 10 == 0:
                    print(f"     Progress: {batch_num}/{total_batches} batches...", end='\r')
                
                for idx, row in batch.iterrows():
                    try:
                        query = text("""
                            INSERT INTO candles 
                            (symbol, timeframe, timestamp, datetime, open, high, low, close, volume)
                            VALUES 
                            (:symbol, :timeframe, :timestamp, :datetime, :open, :high, :low, :close, :volume)
                            ON CONFLICT (symbol, timeframe, timestamp) 
                            DO NOTHING
                            RETURNING id
                        """)
                        
                        result = connection.execute(query, {
                            'symbol': row['symbol'],
                            'timeframe': row['timeframe'],
                            'timestamp': int(row['timestamp']),
                            'datetime': row['datetime'],
                            'open': float(row['open']),
                            'high': float(row['high']),
                            'low': float(row['low']),
                            'close': float(row['close']),
                            'volume': float(row['volume'])
                        })
                        
                        if result.rowcount > 0:
                            inserted_count += 1
                        else:
                            duplicate_count += 1
                    
                    except Exception as e:
                        pass
            
            connection.commit()
        
        print(f"\n  ✓ Inserted {inserted_count:,} new candles")
        if duplicate_count > 0:
            print(f"     ℹ Skipped {duplicate_count:,} duplicates")
        
        return inserted_count, duplicate_count
    
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return 0, 0

def calculate_all_indicators_for_symbol(symbol, timeframe):
    """
    Calculate ALL indicators for a symbol/timeframe combination
    NO LIMIT - processes ALL candles for complete historical indicators
    Includes: RSI, MACD, EMA, BB, ADX, ATR, Volume, SuperTrend, OBV, VWAP
    """
    print(f"\n{'─'*80}")
    print(f"📊 Calculating indicators for {symbol} ({timeframe})")
    print(f"{'─'*80}")
    
    # Initialize all calculators with YOUR settings
    rsi_calc = RSICalculator(rsi_length=14, rsi_ema_length=21)
    macd_calc = MACDCalculator(fast=9, slow=21, signal=5, ma_type='EMA', signal_type='EMA')
    ema_calc = EMACalculator(ema_44=44, ema_100=100, ema_200=200)
    bb_calc = BollingerBandsCalculator(length=20, mult_1=1.0, mult_2=2.0, mult_3=3.0, squeeze_threshold=4.0)
    
    # Calculate basic indicators first (NO LIMIT)
    print("\n1️⃣  Calculating RSI...", end='')
    rsi_stored = rsi_calc.run(symbol, timeframe, limit=None)
    print(f" ✓ {rsi_stored} values")
    
    print("2️⃣  Calculating MACD...", end='')
    macd_stored = macd_calc.run(symbol, timeframe, limit=None)
    print(f" ✓ {macd_stored} values")
    
    print("3️⃣  Calculating EMA...", end='')
    ema_stored = ema_calc.run(symbol, timeframe, limit=None)
    print(f" ✓ {ema_stored} values")
    
    print("4️⃣  Calculating Bollinger Bands...", end='')
    bb_stored = bb_calc.run(symbol, timeframe, limit=None)
    print(f" ✓ {bb_stored} values")
    
    # Now calculate comprehensive indicators (ADX, ATR, Volume, SuperTrend, OBV, VWAP)
    print("\n5️⃣  Calculating comprehensive indicators (ADX, ATR, Volume, SuperTrend, OBV, VWAP)...")
    
    # Import indicator runner
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), 'automation'))
    from indicator_runner import IndicatorRunner
    from sqlalchemy import text
    
    runner = IndicatorRunner()
    
    # FIXED: Get ALL candles, not just those without indicators
    # This ensures SuperTrend is calculated even if RSI/MACD already exist
    try:
        with engine.connect() as conn:
            candles_query = text("""
                SELECT c.id, c.symbol, c.timeframe, c.datetime, c.open, c.high, c.low, c.close, c.volume
                FROM candles c
                WHERE c.symbol = :symbol
                AND c.timeframe = :timeframe
                ORDER BY c.datetime ASC
            """)
            
            result = conn.execute(candles_query, {'symbol': symbol, 'timeframe': timeframe})
            all_candles = result.fetchall()
    except Exception as e:
        print(f"   ✗ Error fetching candles: {e}")
        all_candles = []
    
    if all_candles:
        print(f"   Processing {len(all_candles)} candles...")
        
        comprehensive_count = 0
        for i, candle_row in enumerate(all_candles):
            # Progress indicator every 500 candles
            if i > 0 and i % 500 == 0:
                print(f"   Progress: {i}/{len(all_candles)} candles ({i*100//len(all_candles)}%)")
            
            # Convert row to candle dict (convert Decimal to float)
            candle = {
                'id': candle_row[0],
                'symbol': candle_row[1],
                'timeframe': candle_row[2],
                'datetime': candle_row[3],
                'open': float(candle_row[4]),
                'high': float(candle_row[5]),
                'low': float(candle_row[6]),
                'close': float(candle_row[7]),
                'volume': float(candle_row[8])
            }
            
            # Get historical data for this candle
            historical_df = runner.get_historical_candles(
                symbol, timeframe, candle['datetime'], limit=250
            )
            
            if len(historical_df) < 250:
                continue
            
            # Calculate comprehensive indicators
            indicators = runner.calculate_indicators_for_candle(candle, historical_df)
            
            if indicators:
                # Update or insert indicators (handles both new and existing)
                if runner.store_indicators(candle['id'], indicators):
                    comprehensive_count += 1
        
        print(f"   ✓ Calculated comprehensive indicators for {comprehensive_count} candles")
    else:
        print(f"   ✗ No candles found for {symbol} {timeframe}")
    
    return {
        'rsi': rsi_stored,
        'macd': macd_stored,
        'ema': ema_stored,
        'bb': bb_stored,
        'comprehensive': comprehensive_count if candles else 0
    }
def add_to_tracked_symbols(symbol, exchange='binance'):
    """
    Add symbol to tracked_symbols table so automation picks it up
    
    Args:
        symbol: Trading pair (e.g., 'SOL/USDT')
        exchange: Exchange name (default 'binance')
    """
    print(f"\n📝 Adding {symbol} to tracked_symbols table...")
    
    try:
        with engine.connect() as connection:
            # Check if already exists
            check_query = text("""
                SELECT id FROM tracked_symbols 
                WHERE symbol = :symbol
            """)
            
            existing = connection.execute(check_query, {'symbol': symbol}).fetchone()
            
            if existing:
                print(f"  ℹ️  {symbol} already in tracked_symbols (ID: {existing[0]})")
                return True
            
            # Insert new symbol
            insert_query = text("""
                INSERT INTO tracked_symbols 
                (symbol, exchange, timeframes, active, added_by, notes, data_status, data_download_started)
                VALUES 
                (:symbol, :exchange, :timeframes, TRUE, 'script', :notes, 'downloading', CURRENT_TIMESTAMP)
                RETURNING id
            """)
            
            result = connection.execute(insert_query, {
                'symbol': symbol,
                'exchange': exchange,
                'timeframes': TIMEFRAMES,  # Use the global TIMEFRAMES variable
                'notes': f'Added via add_new_symbol.py on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'
            })
            
            connection.commit()
            
            new_id = result.fetchone()[0]
            print(f"  ✓ Added {symbol} to tracked_symbols (ID: {new_id})")
            print(f"    Exchange: {exchange}")
            print(f"    Timeframes: {', '.join(TIMEFRAMES)}")
            print(f"    Active: TRUE")
            
            return True
    
    except Exception as e:
        print(f"  ✗ Error adding to tracked_symbols: {e}")
        return False
# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    """
    Usage:
        python backend/add_new_symbol.py SOL/USDT
        python backend/add_new_symbol.py ADA/USDT
        python backend/add_new_symbol.py MATIC/USDT
    """
    
    # Parse command line arguments
    if len(sys.argv) < 2:
        print("=" * 80)
        print("ADD NEW SYMBOL - Universal Crypto Data Fetcher")
        print("=" * 80)
        print("\n📚 Usage:")
        print("  python backend/add_new_symbol.py SYMBOL")
        print("\n💡 Examples:")
        print("  python backend/add_new_symbol.py SOL/USDT")
        print("  python backend/add_new_symbol.py ADA/USDT")
        print("  python backend/add_new_symbol.py MATIC/USDT")
        print("\n🪙 Popular Binance Pairs:")
        print("  SOL/USDT  - Solana")
        print("  ADA/USDT  - Cardano")
        print("  MATIC/USDT - Polygon")
        print("  DOT/USDT  - Polkadot")
        print("  LINK/USDT - Chainlink")
        print("  AVAX/USDT - Avalanche")
        print("  ATOM/USDT - Cosmos")
        print("  XRP/USDT  - Ripple")
        print("  DOGE/USDT - Dogecoin")
        print("\n⏱️  Timeframes:")
        print("  Automatically fetches: 15m, 1h, 1d")
        print("\n📅 Historical Period:")
        print("  90 days (3 months) for each timeframe")
        print("=" * 80)
        sys.exit(1)
    
    symbol = sys.argv[1]
    
    # Define all timeframes to fetch (same as BTC/ETH)
    TIMEFRAMES = ['15m', '1h', '4h', '1d']  # ADD 4h timeframe
    DAYS = 180  # 6 months instead of 3
    
    print("=" * 80)
    print(f"ADDING NEW SYMBOL: {symbol}")
    print("=" * 80)
    print(f"\n⚙️  Configuration:")
    print(f"   Symbol: {symbol}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"   Historical period: {DAYS} days (3 months)")
    print(f"   Data source: Binance")
    
    # Track totals
    total_candles_inserted = 0
    total_candles_duplicate = 0
    indicator_results = {}
    
    # Process each timeframe
    for timeframe in TIMEFRAMES:
        print("\n" + "═" * 80)
        print(f"PROCESSING TIMEFRAME: {timeframe}")
        print("═" * 80)
        
        # Step 1: Fetch data
        df = fetch_historical_batches(symbol, timeframe, DAYS)
        
        if df is None or len(df) == 0:
            print(f"  ✗ Failed to fetch {timeframe} data, skipping...")
            continue
        
        # Step 2: Store in database
        inserted, duplicates = store_candles_batch(df)
        total_candles_inserted += inserted
        total_candles_duplicate += duplicates
        
        # Step 3: Calculate all indicators
        if inserted > 0 or duplicates > 0:
            results = calculate_all_indicators_for_symbol(symbol, timeframe)
            indicator_results[timeframe] = results
        # Step 4: Add to tracked_symbols table
        add_to_tracked_symbols(symbol, 'binance')
        # Step 5: Mark as ready in database
        try:
            with engine.connect() as connection:
                update_query = text("""
                    UPDATE tracked_symbols
                    SET data_status = 'ready',
                        data_download_completed = CURRENT_TIMESTAMP
                    WHERE symbol = :symbol
                """)
                connection.execute(update_query, {'symbol': symbol})
                connection.commit()
                print(f"\n✓ Marked {symbol} as ready in database")
        except Exception as e:
            print(f"\n⚠️  Could not update status: {e}")
        
        # Small delay between timeframes
        time.sleep(1)
    # Step 6: Calculate Support/Resistance
        print("\n" + "=" * 80)
        print("STEP 6: CALCULATING SUPPORT/RESISTANCE")
        print("=" * 80)
        
        from calculations.support_resistance import SupportResistanceCalculator
        
        sr_calc = SupportResistanceCalculator()
        
        for tf in TIMEFRAMES:
            print(f"\n  {tf}...", end='', flush=True)
            sr_calc.update_sr(symbol, tf, manual_support=0, manual_resistance=0, auto_sr_mode='Enabled')
        
        print("\n✅ Support/Resistance calculated for all timeframes")
    # Final summary
    print("\n" + "=" * 80)
    print("✅ SYMBOL ADDED SUCCESSFULLY!")
    print("=" * 80)
    print(f"\n📊 Summary for {symbol}:")
    print(f"   Total new candles inserted: {total_candles_inserted:,}")
    print(f"   Total duplicates skipped: {total_candles_duplicate:,}")
    
    print("\n📈 Indicators Calculated:")
    for tf, results in indicator_results.items():
        print(f"\n   {tf}:")
        print(f"      RSI: {results['rsi']} candles")
        print(f"      MACD: {results['macd']} candles")
        print(f"      EMA: {results['ema']} candles")
        print(f"      BB: {results['bb']} candles")
        print(f"      Comprehensive (ADX, ATR, Volume, ST, OBV, VWAP): {results.get('comprehensive', 0)} candles")
    
    print("\n💡 Next Steps:")
    print(f"   1. Verify data in Navicat:")
    print(f"\n      SELECT symbol, timeframe, COUNT(*) as candles,")
    print(f"             MIN(datetime) as first, MAX(datetime) as last")
    print(f"      FROM candles")
    print(f"      WHERE symbol = '{symbol}'")
    print(f"      GROUP BY symbol, timeframe;")
    print(f"\n   2. Add '{symbol}' to your dashboard configuration")
    print(f"   3. Ready to generate signals and track entries!")
    print("\n" + "=" * 80)