"""
VWAP Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate VWAP (Volume Weighted Average Price) - institutional benchmark

VWAP (Volume Weighted Average Price):
- Average price weighted by volume
- Shows where most volume traded
- Used by institutions as execution benchmark
- Resets daily (cumulative within trading day)

How VWAP Works:
VWAP = Σ(Price × Volume) / Σ(Volume)

Where Price = (High + Low + Close) / 3 (typical price)

Why VWAP Matters:
1. Institutional Benchmark: Big players use VWAP for order execution
2. Support/Resistance: VWAP acts as dynamic S/R level
3. Trend Filter: Price > VWAP = Bullish, Price < VWAP = Bearish
4. Fair Value: VWAP shows "fair" price based on actual trading

Your Settings:
- Neutral Zone: 0.5% (price within ±0.5% of VWAP = neutral)

Trading Logic:
- Price > VWAP + 0.5%: Bullish (above fair value)
- Price < VWAP - 0.5%: Bearish (below fair value)
- Price within ±0.5% of VWAP: Neutral (at fair value)

Example:
Hour 1: Price=$100, Volume=1000 → VWAP = $100
Hour 2: Price=$102, Volume=1500 → VWAP = ($100×1000 + $102×1500) / 2500 = $101.20
Hour 3: Price=$98, Volume=2000 → VWAP = (previous + $98×2000) / 4500 = $99.78
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class VWAPCalculator(BaseCalculator):
    """
    VWAP Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. Typical Price: (High + Low + Close) / 3
       - Representative price for the period
    
    2. Price × Volume: Typical Price multiplied by Volume
       - Dollar volume traded at that price
    
    3. Cumulative PV: Sum of all (Price × Volume)
       - Total dollar volume
    
    4. Cumulative Volume: Sum of all Volume
       - Total volume traded
    
    5. VWAP: Cumulative PV / Cumulative Volume
       - Volume-weighted average price
    
    Note: In crypto, VWAP is cumulative across all time
          In stocks, VWAP resets daily
    
    Trading Interpretation:
    - Price > VWAP: Above average (bullish zone)
    - Price < VWAP: Below average (bearish zone)
    - Price touching VWAP: Potential support/resistance
    - VWAP slope up: Uptrend, VWAP slope down: Downtrend
    """
    
    def __init__(self, neutral_zone: float = 0.5):
        """
        Initialize VWAP calculator with your TradingView settings
        
        Args:
            neutral_zone: Percentage for neutral zone (default 0.5%, matches your Pine Script)
        
        Note: 0.5% neutral zone means price within ±0.5% of VWAP is considered neutral
        """
        super().__init__("VWAP")
        self.neutral_zone = neutral_zone / 100.0  # Convert percentage to decimal
    
    def calculate_typical_price(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate Typical Price (HLC/3)
        
        This matches Pine Script hlc3 or (high + low + close) / 3
        
        Args:
            df: DataFrame with high, low, close columns
        
        Returns:
            Series of typical price values
            
        Why use Typical Price?
        - More representative than just close
        - Considers full price range (high, low, close)
        - Reduces impact of outlier closes
        
        Example:
        High=$105, Low=$95, Close=$102
        Typical Price = (105 + 95 + 102) / 3 = $100.67
        """
        # Convert to float to avoid Decimal issues
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)
        
        return (high + low + close) / 3.0
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate VWAP (Volume Weighted Average Price)
        
        This matches Pine Script ta.vwap(close) function
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: high, low, close, volume
        
        Returns:
            DataFrame with one new column added:
            - vwap: Volume Weighted Average Price
            
        Process:
        1. Calculate typical price (HLC/3)
        2. Calculate price × volume
        3. Calculate cumulative sum of (price × volume)
        4. Calculate cumulative sum of volume
        5. VWAP = Cumulative PV / Cumulative Volume
        
        Interpretation:
        - VWAP rising: Average price increasing (uptrend)
        - VWAP falling: Average price decreasing (downtrend)
        - Price > VWAP: Trading above average (bullish)
        - Price < VWAP: Trading below average (bearish)
        """
        # Validation: Check if we have enough data
        min_candles_needed = 20
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for VWAP calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate typical price (HLC/3)
        # This is more representative than just using close
        typical_price = self.calculate_typical_price(df)
        
        # Step 2: Calculate price × volume (dollar volume)
        # This shows how much money traded at each price
        # Convert volume to float to avoid Decimal issues
        volume = df['volume'].astype(float)
        pv = typical_price * volume
        
        # Step 3: Calculate cumulative price × volume
        # Sum of all dollar volume up to this point
        cumulative_pv = pv.cumsum()
        
        # Step 4: Calculate cumulative volume
        # Total volume traded up to this point
        cumulative_volume = volume.cumsum()
        
        # Step 5: Calculate VWAP
        # VWAP = Total dollar volume / Total volume
        # This gives the average price weighted by volume
        df['vwap'] = cumulative_pv / cumulative_volume
        
        # Step 6: Round to 8 decimal places (price precision)
        df['vwap'] = df['vwap'].round(8)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['vwap']
        """
        return ['vwap']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/vwap.py
    
    This will:
    1. Calculate VWAP for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show VWAP analysis
    """
    print("=" * 80)
    print("VWAP CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your VWAP Settings:")
    print(f"   Neutral Zone: ±0.5% of VWAP")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings (0.5%)
    calc = VWAPCalculator(neutral_zone=0.5)
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} VWAP values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} VWAP values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ VWAP CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read VWAP:")
    print("   Price > VWAP + 0.5%: Above fair value (bullish)")
    print("   Price < VWAP - 0.5%: Below fair value (bearish)")
    print("   Price within ±0.5%: At fair value (neutral)")
    print("")
    print("   Trading Strategies:")
    print("   • Buy when price dips to VWAP (support)")
    print("   • Sell when price spikes above VWAP (resistance)")
    print("   • Trend: Price consistently > VWAP = Uptrend")
    print("   • Trend: Price consistently < VWAP = Downtrend")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see VWAP data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       ROUND(i.vwap::numeric, 2) as vwap,")
    print("       ROUND(((c.close - i.vwap) / i.vwap * 100)::numeric, 2) as distance_pct,")
    print("       CASE ")
    print("           WHEN c.close > (i.vwap * 1.005) THEN '🟢 Above VWAP'")
    print("           WHEN c.close < (i.vwap * 0.995) THEN '🔴 Below VWAP'")
    print("           ELSE '⚪ At VWAP'")
    print("       END as vwap_position")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)