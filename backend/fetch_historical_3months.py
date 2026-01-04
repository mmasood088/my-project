"""
Historical Data Fetcher - 3 Months
Author: Your Trading System
Purpose: Fetch 3 months of historical data for BTC/USDT and ETH/USDT

This script fetches comprehensive historical data across all timeframes:
- 15 minute candles (~8,640 candles)
- 1 hour candles (~2,160 candles)
- 1 day candles (~90 candles)

Binance API Limitations:
- Maximum 1000 candles per request
- Rate limit: ~1200 requests per minute
- Solution: Fetch in batches, use time-based pagination

Process:
1. For each symbol (BTC/USDT, ETH/USDT)
2. For each timeframe (15m, 1h, 1d)
3. Calculate how many batches needed
4. Fetch data backwards from current time
5. Store in database (skip duplicates)
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import time

def fetch_historical_batches(symbol, timeframe, days=90):
    """
    Fetch historical data in batches (handles Binance 1000 candle limit)
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candle timeframe ('15m', '1h', '1d')
        days: Number of days to fetch (default 90 = 3 months)
    
    Returns:
        DataFrame with all OHLCV data
        
    How it works:
    1. Calculate total candles needed based on timeframe
    2. Determine how many batches required (max 1000 per batch)
    3. Fetch backwards from current time
    4. Use 'since' parameter to paginate through history
    5. Combine all batches into single DataFrame
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
        now = int(datetime.now().timestamp() * 1000)  # Current time in ms
        start_time = now - (days * 24 * 60 * 60 * 1000)  # 90 days ago
        
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
                time.sleep(0.2)  # 200ms delay between requests
                
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
                
                if batch_num % 10 == 0:  # Progress update every 10 batches
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
                        print(f"\n     ✗ Error inserting candle: {e}")
            
            connection.commit()
        
        print(f"\n  ✓ Inserted {inserted_count:,} new candles")
        if duplicate_count > 0:
            print(f"     ℹ Skipped {duplicate_count:,} duplicates")
        
        return inserted_count, duplicate_count
    
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        return 0, 0

def get_database_stats():
    """
    Get comprehensive database statistics
    """
    try:
        with engine.connect() as connection:
            # Total candles
            result = connection.execute(text("SELECT COUNT(*) FROM candles"))
            total = result.fetchone()[0]
            
            # By symbol and timeframe
            result = connection.execute(text("""
                SELECT 
                    symbol,
                    timeframe,
                    COUNT(*) as count,
                    MIN(datetime) as first_candle,
                    MAX(datetime) as last_candle
                FROM candles
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """))
            by_combo = result.fetchall()
            
            return {
                'total': total,
                'by_combo': by_combo
            }
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
        return None

def display_stats(stats):
    """
    Display database statistics
    """
    if not stats:
        return
    
    print("\n" + "=" * 90)
    print("📊 DATABASE STATISTICS")
    print("=" * 90)
    
    print(f"\n📈 Total Candles: {stats['total']:,}")
    
    print("\n📊 Breakdown by Symbol & Timeframe:")
    print("─" * 90)
    print(f"{'Symbol':<15} {'Timeframe':<12} {'Count':>10} {'First Candle':<20} {'Last Candle':<20}")
    print("─" * 90)
    for row in stats['by_combo']:
        print(f"{row[0]:<15} {row[1]:<12} {row[2]:>10,} {str(row[3]):<20} {str(row[4]):<20}")
    print("─" * 90)

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 90)
    print("HISTORICAL DATA FETCHER - 3 MONTHS")
    print("=" * 90)
    
    # Configuration
    SYMBOLS = ['BTC/USDT', 'ETH/USDT']
    TIMEFRAMES = ['15m', '1h', '1d']
    DAYS = 90  # 3 months
    
    print(f"\n⚙️  Configuration:")
    print(f"   Symbols: {', '.join(SYMBOLS)}")
    print(f"   Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"   Historical period: {DAYS} days (3 months)")
    print(f"   Expected total: ~21,780 candles")
    
    # Show initial stats
    print("\n📊 Initial Database Status:")
    initial_stats = get_database_stats()
    if initial_stats:
        print(f"   Total candles: {initial_stats['total']:,}")
    
    # Track totals
    total_inserted = 0
    total_duplicates = 0
    
    # Fetch data for each combination
    for symbol in SYMBOLS:
        print("\n" + "═" * 90)
        print(f"Processing {symbol}")
        print("═" * 90)
        
        for timeframe in TIMEFRAMES:
            # Fetch historical data
            df = fetch_historical_batches(symbol, timeframe, DAYS)
            
            if df is not None and len(df) > 0:
                # Store in database
                inserted, duplicates = store_candles_batch(df)
                total_inserted += inserted
                total_duplicates += duplicates
            
            # Small delay between symbols/timeframes
            time.sleep(1)
    
    # Show final stats
    print("\n" + "=" * 90)
    print("✅ DATA FETCH COMPLETED!")
    print("=" * 90)
    print(f"\n📊 Summary:")
    print(f"   New candles inserted: {total_inserted:,}")
    print(f"   Duplicates skipped: {total_duplicates:,}")
    
    final_stats = get_database_stats()
    if final_stats:
        display_stats(final_stats)
    
    print("\n" + "=" * 90)
    print("✅ All historical data loaded!")
    print("=" * 90)
    print("\n💡 Next Steps:")
    print("   1. Check Navicat to verify data")
    print("   2. Run indicator calculators on new data:")
    print("      - python backend/indicators/rsi.py")
    print("      - python backend/indicators/macd.py")
    print("      - python backend/indicators/ema.py")
    print("   3. Then proceed with Bollinger Bands!")
    print("\n" + "=" * 90)