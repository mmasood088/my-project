"""
Multi-Stock Data Fetcher
Fetches historical data for multiple stocks and timeframes
"""

import ccxt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from database import engine
import time

def fetch_historical_data(symbol, timeframe, days=30):
    """
    Fetch historical OHLCV data from Binance
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '15m', '1h', '1d')
        days: Number of days to fetch
    
    Returns:
        DataFrame with OHLCV data
    """
    print(f"\n📡 Fetching {days} days of {timeframe} data for {symbol}...")
    
    try:
        # Connect to Binance
        exchange = ccxt.binance()
        
        # Calculate how many candles we need based on timeframe
        if timeframe == '15m':
            candles_per_day = 96
        elif timeframe == '1h':
            candles_per_day = 24
        elif timeframe == '1d':
            candles_per_day = 1
        else:
            candles_per_day = 24  # Default
        
        limit = candles_per_day * days
        
        # Binance has a limit of 1000 candles per request
        # If we need more, we'll fetch in batches
        if limit > 1000:
            limit = 1000
            print(f"  ⚠️  Limiting to {limit} candles (Binance max per request)")
        
        # Fetch OHLCV data
        ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        
        # Convert to DataFrame
        df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # Add datetime column (human-readable)
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
        
        # Add symbol and timeframe columns
        df['symbol'] = symbol
        df['timeframe'] = timeframe
        
        print(f"✓ Fetched {len(df)} candles successfully!")
        print(f"  Date range: {df['datetime'].min()} to {df['datetime'].max()}")
        print(f"  Latest price: ${df['close'].iloc[-1]:,.2f}")
        
        return df
    
    except Exception as e:
        print(f"✗ Error fetching data for {symbol} ({timeframe}): {e}")
        return None

def store_candles_batch(df):
    """
    Store candles DataFrame in database (batch insert for speed)
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        Number of candles inserted
    """
    if df is None or len(df) == 0:
        print("✗ No data to store")
        return 0
    
    print(f"💾 Storing {len(df)} candles in database...")
    
    try:
        with engine.connect() as connection:
            inserted_count = 0
            duplicate_count = 0
            
            # Insert each candle
            for idx, row in df.iterrows():
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
                    print(f"  ✗ Error inserting candle: {e}")
            
            connection.commit()
            
            print(f"✓ Inserted {inserted_count} new candles")
            if duplicate_count > 0:
                print(f"  ℹ Skipped {duplicate_count} duplicates")
            
            return inserted_count
    
    except Exception as e:
        print(f"✗ Database error: {e}")
        return 0

def get_database_stats():
    """
    Get comprehensive database statistics
    """
    try:
        with engine.connect() as connection:
            # Total candles
            result = connection.execute(text("SELECT COUNT(*) FROM candles"))
            total = result.fetchone()[0]
            
            # Candles by symbol
            result = connection.execute(text("""
                SELECT 
                    symbol,
                    COUNT(*) as count,
                    MIN(datetime) as first_candle,
                    MAX(datetime) as last_candle
                FROM candles
                GROUP BY symbol
                ORDER BY symbol
            """))
            by_symbol = result.fetchall()
            
            # Candles by timeframe
            result = connection.execute(text("""
                SELECT 
                    timeframe,
                    COUNT(*) as count
                FROM candles
                GROUP BY timeframe
                ORDER BY timeframe
            """))
            by_timeframe = result.fetchall()
            
            return {
                'total': total,
                'by_symbol': by_symbol,
                'by_timeframe': by_timeframe
            }
    except Exception as e:
        print(f"✗ Error getting stats: {e}")
        return None

def display_stats(stats):
    """
    Display database statistics in a nice format
    """
    if not stats:
        return
    
    print("\n" + "=" * 80)
    print("📊 DATABASE STATISTICS")
    print("=" * 80)
    
    print(f"\n📈 Total Candles: {stats['total']:,}")
    
    print("\n📊 Breakdown by Symbol:")
    print("-" * 80)
    print(f"{'Symbol':<15} {'Count':>10} {'First Candle':<20} {'Last Candle':<20}")
    print("-" * 80)
    for row in stats['by_symbol']:
        print(f"{row[0]:<15} {row[1]:>10,} {str(row[2]):<20} {str(row[3]):<20}")
    print("-" * 80)
    
    print("\n⏰ Breakdown by Timeframe:")
    print("-" * 40)
    print(f"{'Timeframe':<15} {'Count':>10}")
    print("-" * 40)
    for row in stats['by_timeframe']:
        print(f"{row[0]:<15} {row[1]:>10,}")
    print("-" * 40)

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("MULTI-STOCK HISTORICAL DATA FETCHER")
    print("=" * 80)
    
    # Configuration
    SYMBOLS = ['BTC/USDT', 'ETH/USDT']
    TIMEFRAMES = ['15m', '1h', '1d']
    DAYS = 30
    
    # Display configuration
    print(f"\n⚙️  Configuration:")
    print(f"  Symbols: {', '.join(SYMBOLS)}")
    print(f"  Timeframes: {', '.join(TIMEFRAMES)}")
    print(f"  Historical period: {DAYS} days")
    
    # Show initial stats
    print("\n📊 Initial Database Status:")
    initial_stats = get_database_stats()
    if initial_stats:
        print(f"  Total candles: {initial_stats['total']:,}")
    
    # Fetch and store data for each combination
    total_inserted = 0
    
    for symbol in SYMBOLS:
        for timeframe in TIMEFRAMES:
            # Fetch data
            df = fetch_historical_data(symbol, timeframe, DAYS)
            
            if df is not None:
                # Store in database
                inserted = store_candles_batch(df)
                total_inserted += inserted
                
                # Small delay to avoid rate limiting
                time.sleep(0.5)
            
            print()  # Blank line for readability
    
    # Show final stats
    print("\n" + "=" * 80)
    print(f"✅ DATA FETCH COMPLETED!")
    print(f"   Total new candles inserted: {total_inserted:,}")
    print("=" * 80)
    
    final_stats = get_database_stats()
    if final_stats:
        display_stats(final_stats)
    
    print("\n" + "=" * 80)
    print("Script completed! Check Navicat to view your data.")
    print("=" * 80)