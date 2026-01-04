"""
Fetch data from Binance and store in PostgreSQL database
This script fetches OHLCV candles and stores them in the 'candles' table
"""

import ccxt
import pandas as pd
from datetime import datetime
from sqlalchemy import text
from database import engine

def fetch_binance_data(symbol='BTC/USDT', timeframe='1h', limit=100):
    """
    Fetch OHLCV data from Binance
    
    Args:
        symbol: Trading pair (e.g., 'BTC/USDT')
        timeframe: Candle timeframe (e.g., '1h', '15m', '1D')
        limit: Number of candles to fetch
    
    Returns:
        DataFrame with OHLCV data
    """
    print(f"\n📡 Fetching {limit} candles for {symbol} ({timeframe})...")
    
    try:
        # Connect to Binance
        exchange = ccxt.binance()
        
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
        print(f"✗ Error fetching data: {e}")
        return None

def store_candles_in_db(df):
    """
    Store candles DataFrame in PostgreSQL database
    
    Args:
        df: DataFrame with OHLCV data
    
    Returns:
        Number of candles inserted
    """
    if df is None or len(df) == 0:
        print("✗ No data to store")
        return 0
    
    print(f"\n💾 Storing {len(df)} candles in database...")
    
    try:
        with engine.connect() as connection:
            inserted_count = 0
            duplicate_count = 0
            
            # Insert each candle
            for idx, row in df.iterrows():
                try:
                    # Prepare INSERT query with ON CONFLICT (skip duplicates)
                    query = text("""
                        INSERT INTO candles 
                        (symbol, timeframe, timestamp, datetime, open, high, low, close, volume)
                        VALUES 
                        (:symbol, :timeframe, :timestamp, :datetime, :open, :high, :low, :close, :volume)
                        ON CONFLICT (symbol, timeframe, timestamp) 
                        DO NOTHING
                        RETURNING id
                    """)
                    
                    # Execute query
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
                    
                    # Check if inserted (returns id) or skipped (no result)
                    if result.rowcount > 0:
                        inserted_count += 1
                    else:
                        duplicate_count += 1
                
                except Exception as e:
                    print(f"  ✗ Error inserting candle at {row['datetime']}: {e}")
            
            # Commit transaction
            connection.commit()
            
            print(f"✓ Inserted {inserted_count} new candles")
            if duplicate_count > 0:
                print(f"  ℹ Skipped {duplicate_count} duplicate candles")
            
            return inserted_count
    
    except Exception as e:
        print(f"✗ Database error: {e}")
        return 0

def get_candle_count():
    """
    Get total number of candles in database
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT COUNT(*) FROM candles"))
            count = result.fetchone()[0]
            return count
    except Exception as e:
        print(f"✗ Error counting candles: {e}")
        return 0

def get_latest_candles(limit=5):
    """
    Get latest candles from database
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT symbol, timeframe, datetime, open, high, low, close, volume
                FROM candles
                ORDER BY datetime DESC
                LIMIT :limit
            """), {'limit': limit})
            
            rows = result.fetchall()
            return rows
    except Exception as e:
        print(f"✗ Error fetching candles: {e}")
        return []

# ============================================
# MAIN EXECUTION
# ============================================

if __name__ == "__main__":
    print("=" * 70)
    print("BINANCE DATA FETCHER - Store to PostgreSQL")
    print("=" * 70)
    
    # Step 1: Check current database status
    print("\n📊 Current Database Status:")
    print(f"  Total candles in database: {get_candle_count()}")
    
    # Step 2: Fetch data from Binance
    df = fetch_binance_data(symbol='ETH/USDT', timeframe='1h', limit=100)
    
    if df is not None:
        # Step 3: Store in database
        inserted = store_candles_in_db(df)
        
        # Step 4: Verify storage
        print("\n✅ Updated Database Status:")
        print(f"  Total candles in database: {get_candle_count()}")
        
        # Step 5: Show latest candles
        print("\n📋 Latest 5 Candles in Database:")
        latest = get_latest_candles(5)
        
        if latest:
            print("-" * 70)
            print(f"{'Symbol':<12} {'TF':<6} {'DateTime':<20} {'Close':>12} {'Volume':>15}")
            print("-" * 70)
            for row in latest:
                print(f"{row[0]:<12} {row[1]:<6} {str(row[2]):<20} ${row[6]:>11,.2f} {row[7]:>15,.2f}")
            print("-" * 70)
    
    print("\n" + "=" * 70)
    print("Script completed!")
    print("=" * 70)