"""
Candle Fetcher
Automatically fetch new candles from exchanges and store in database
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from typing import Optional, List, Dict

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from automation.exchanges.binance_adapter import BinanceAdapter


class CandleFetcher:
    """
    Fetch and store candles from exchanges
    """
    
    def __init__(self):
        self.engine = engine
        self.exchanges = {
            'binance': BinanceAdapter()
        }
    
    def get_last_candle_datetime(self, symbol: str, timeframe: str) -> Optional[datetime]:
        """
        Get datetime of last candle in database for symbol/timeframe
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
        
        Returns:
            Datetime of last candle, or None if no candles exist
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT MAX(datetime) as last_datetime
                    FROM candles
                    WHERE symbol = :symbol AND timeframe = :timeframe
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()
                
                return result[0] if result and result[0] else None
        
        except Exception as e:
            print(f"  ✗ Error getting last candle datetime: {e}")
            return None
    
    def insert_candles(self, symbol: str, timeframe: str, 
                      candles: List[Dict]) -> int:
        """
        Insert candles into database (skip duplicates)
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            candles: List of candle dicts from exchange adapter
        
        Returns:
            Number of candles inserted
        """
        if not candles:
            return 0
        
        inserted_count = 0
        
        try:
            with self.engine.connect() as conn:
                for candle in candles:
                    # Check if candle already exists
                    check_query = text("""
                        SELECT id FROM candles
                        WHERE symbol = :symbol 
                        AND timeframe = :timeframe 
                        AND datetime = :datetime
                    """)
                    
                    existing = conn.execute(check_query, {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'datetime': candle['datetime']
                    }).fetchone()
                    
                    if existing:
                        continue  # Skip duplicate
                    
                    # Insert new candle
                    insert_query = text("""
                        INSERT INTO candles (
                            symbol, timeframe, timestamp, datetime,
                            open, high, low, close, volume
                        ) VALUES (
                            :symbol, :timeframe, :timestamp, :datetime,
                            :open, :high, :low, :close, :volume
                        )
                    """)

                    # Convert datetime to Unix timestamp in milliseconds
                    timestamp_ms = int(candle['datetime'].timestamp() * 1000)

                    conn.execute(insert_query, {
                        'symbol': symbol,
                        'timeframe': timeframe,
                        'timestamp': timestamp_ms,
                        'datetime': candle['datetime'],
                        'open': candle['open'],
                        'high': candle['high'],
                        'low': candle['low'],
                        'close': candle['close'],
                        'volume': candle['volume']
                    })
                    
                    inserted_count += 1
                
                conn.commit()
        
        except Exception as e:
            print(f"  ✗ Error inserting candles: {e}")
            import traceback
            traceback.print_exc()
        
        return inserted_count
    
    def fetch_and_store(self, exchange_name: str, symbol: str, 
                       timeframe: str, limit: int = 100) -> int:
        """
        Fetch new candles from exchange and store in database
        
        Args:
            exchange_name: Exchange name (e.g., 'binance')
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Maximum candles to fetch
        
        Returns:
            Number of new candles stored
        """
        try:
            # Get exchange adapter
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                print(f"  ✗ Unknown exchange: {exchange_name}")
                return 0
            
            # Get last candle datetime from database
            last_datetime = self.get_last_candle_datetime(symbol, timeframe)
            
            if last_datetime:
                # Fetch candles after last datetime
                since = last_datetime + timedelta(minutes=1)
                print(f"  → Fetching {symbol} {timeframe} since {since.strftime('%Y-%m-%d %H:%M')}")
            else:
                # No candles in database, fetch recent candles
                since = None
                print(f"  → Fetching last {limit} candles for {symbol} {timeframe}")
            
            # Fetch candles from exchange
            candles = exchange.get_candles(symbol, timeframe, since=since, limit=limit)
            
            if not candles:
                print(f"  ⚠️  No new candles fetched")
                return 0
            
            # Insert into database
            inserted = self.insert_candles(symbol, timeframe, candles)
            
            if inserted > 0:
                print(f"  ✓ Stored {inserted} new candles ({candles[0]['datetime']} to {candles[-1]['datetime']})")
            else:
                print(f"  ✓ All {len(candles)} candles already in database")
            
            return inserted
        
        except Exception as e:
            print(f"  ✗ Error in fetch_and_store: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def fetch_all_symbols_timeframes(self, exchange_name: str = 'binance'):
        """
        Fetch candles for all symbols and timeframes from exchange
        
        Args:
            exchange_name: Exchange to fetch from
        """
        exchange = self.exchanges.get(exchange_name)
        if not exchange:
            print(f"✗ Unknown exchange: {exchange_name}")
            return
        
        symbols = exchange.get_supported_symbols()
        timeframes = exchange.get_supported_timeframes()
        
        print("=" * 80)
        print(f"FETCHING CANDLES FROM {exchange_name.upper()}")
        print("=" * 80)
        print(f"Symbols: {', '.join(symbols)}")
        print(f"Timeframes: {', '.join(timeframes)}")
        print()
        
        total_inserted = 0
        
        for symbol in symbols:
            for timeframe in timeframes:
                print(f"\n{symbol} {timeframe}:")
                inserted = self.fetch_and_store(exchange_name, symbol, timeframe)
                total_inserted += inserted
        
        print("\n" + "=" * 80)
        print(f"✅ COMPLETE: Stored {total_inserted} new candles")
        print("=" * 80)


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("CANDLE FETCHER TEST")
    print("=" * 80)
    
    fetcher = CandleFetcher()
    
    # Test fetching for one symbol/timeframe
    print("\nTest 1: Fetch BTC/USDT 1h")
    print("-" * 80)
    fetcher.fetch_and_store('binance', 'BTC/USDT', '1h', limit=10)
    
    # Test fetching all symbols/timeframes
    print("\n\nTest 2: Fetch all symbols and timeframes")
    print("-" * 80)
    fetcher.fetch_all_symbols_timeframes('binance')