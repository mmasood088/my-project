"""
Calculate All Indicators - For All Historical Data
Author: Your Trading System
Purpose: Calculate RSI, MACD, EMA for ALL candles in database

This script:
1. Finds all unique symbol/timeframe combinations in candles table
2. For each combination, calculates ALL indicators
3. Processes in batches to avoid memory issues
4. Shows progress and statistics
"""

from indicators.rsi import RSICalculator
from indicators.macd import MACDCalculator
from indicators.ema import EMACalculator
from sqlalchemy import text
from database import engine

def get_symbol_timeframe_combinations():
    """
    Get all unique symbol/timeframe combinations from candles table
    
    Returns:
        List of tuples: [(symbol, timeframe, count), ...]
    """
    try:
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT 
                    symbol,
                    timeframe,
                    COUNT(*) as candle_count
                FROM candles
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """))
            
            combinations = result.fetchall()
            return combinations
    except Exception as e:
        print(f"✗ Error getting combinations: {e}")
        return []

def calculate_all_indicators():
    """
    Calculate RSI, MACD, and EMA for all symbol/timeframe combinations
    """
    print("=" * 80)
    print("CALCULATE ALL INDICATORS - Full Historical Data")
    print("=" * 80)
    
    # Get all combinations
    combinations = get_symbol_timeframe_combinations()
    
    if not combinations:
        print("\n✗ No data found in candles table")
        return
    
    print(f"\n📊 Found {len(combinations)} symbol/timeframe combinations:")
    for symbol, timeframe, count in combinations:
        print(f"   {symbol:<15} {timeframe:<6} {count:>6,} candles")
    
    # Initialize calculators
    rsi_calc = RSICalculator(rsi_length=14, rsi_ema_length=21)
    macd_calc = MACDCalculator(fast=9, slow=21, signal=5, ma_type='EMA', signal_type='EMA')
    ema_calc = EMACalculator(ema_44=44, ema_100=100, ema_200=200)
    
    # Process each combination
    total_processed = 0
    
    for symbol, timeframe, count in combinations:
        print("\n" + "─" * 80)
        print(f"Processing {symbol} {timeframe} ({count:,} candles)")
        print("─" * 80)
        
        # Calculate RSI
        print("\n1️⃣  Calculating RSI...")
        rsi_stored = rsi_calc.run(symbol, timeframe, limit=count)
        print(f"   ✓ Stored {rsi_stored:,} RSI values")
        
        # Calculate MACD
        print("\n2️⃣  Calculating MACD...")
        macd_stored = macd_calc.run(symbol, timeframe, limit=count)
        print(f"   ✓ Stored {macd_stored:,} MACD values")
        
        # Calculate EMA
        print("\n3️⃣  Calculating EMA...")
        ema_stored = ema_calc.run(symbol, timeframe, limit=count)
        print(f"   ✓ Stored {ema_stored:,} EMA values")
        
        total_processed += count
    
    # Final summary
    print("\n" + "=" * 80)
    print("✅ ALL INDICATORS CALCULATED!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total combinations processed: {len(combinations)}")
    print(f"   Total candles processed: {total_processed:,}")
    print(f"   Indicators calculated: RSI, RSI-EMA, MACD, MACD Signal, MACD Histogram, EMA 44/100/200")
    
    # Verification query
    print("\n💡 Verification:")
    print("   Run this query in Navicat to verify:")
    print("\n" + "─" * 80)
    print("SELECT ")
    print("    c.symbol,")
    print("    c.timeframe,")
    print("    COUNT(*) as total_candles,")
    print("    COUNT(CASE WHEN i.rsi IS NOT NULL THEN 1 END) as with_rsi,")
    print("    COUNT(CASE WHEN i.macd_line IS NOT NULL THEN 1 END) as with_macd,")
    print("    COUNT(CASE WHEN i.ema_44 IS NOT NULL THEN 1 END) as with_ema")
    print("FROM candles c")
    print("LEFT JOIN indicators i ON c.id = i.candle_id")
    print("GROUP BY c.symbol, c.timeframe")
    print("ORDER BY c.symbol, c.timeframe;")
    print("─" * 80)

if __name__ == "__main__":
    calculate_all_indicators()