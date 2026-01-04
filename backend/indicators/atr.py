"""
ATR Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate ATR (Average True Range) - measures market volatility

ATR (Average True Range):
- Measures how much price typically moves in a period
- Higher ATR = More volatile (larger price swings)
- Lower ATR = Less volatile (smaller price swings)

Why ATR Matters:
1. Stop-Loss Placement: SL = Entry - (2 × ATR)
   - Gives price room to breathe
   - Avoids being stopped out by normal volatility

2. Position Sizing: Risk per trade / ATR = Position size
   - Larger positions in low volatility
   - Smaller positions in high volatility

3. SuperTrend Calculation: ST = Price ± (Factor × ATR)
   - Dynamic support/resistance levels
   - Adjusts to market volatility

4. Profit Targets: Target = Entry + (3 × ATR)
   - Realistic profit expectations
   - Based on typical price movement

Your Settings:
- ATR Length: 14 periods (Wilder's original setting)
- Smoothing: RMA (Wilder's smoothing method)

How ATR Works:
1. Calculate True Range (TR) for each candle
2. Smooth TR using Wilder's smoothing (RMA)
3. Result is ATR - average volatility

Example:
BTC ATR = $800
- Typical 1h move: $800
- Stop-loss: Entry - ($800 × 2) = Entry - $1,600
- Target: Entry + ($800 × 3) = Entry + $2,400
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class ATRCalculator(BaseCalculator):
    """
    ATR Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. True Range (TR): Maximum of:
       - High - Low (current range)
       - |High - Previous Close| (gap up)
       - |Low - Previous Close| (gap down)
    
    2. ATR: Wilder's smoothing of TR
       - First ATR: Simple average of first 14 TRs
       - Subsequent: Previous ATR + (1/14 × (Current TR - Previous ATR))
    
    This matches Pine Script ta.atr(length) exactly
    
    Trading Applications:
    - Stop-Loss: Entry - (2 × ATR) [gives 2 ATR room]
    - Take-Profit: Entry + (3 × ATR) [3:2 reward-risk]
    - Position Size: Account Risk / ATR
    - SuperTrend: Price ± (Factor × ATR)
    
    Volatility Interpretation:
    - Rising ATR: Increasing volatility (trending market)
    - Falling ATR: Decreasing volatility (consolidating)
    - Spike in ATR: Potential trend change or breakout
    """
    
    def __init__(self, length: int = 14):
        """
        Initialize ATR calculator with your TradingView settings
        
        Args:
            length: Period for ATR calculation (default 14, Wilder's original)
        
        Note: 14 is the standard ATR period used globally
        """
        super().__init__("ATR")
        self.length = length
    
    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range (TR) - measures volatility per candle
        
        This matches Pine Script ta.tr() function (same as ADX)
        
        Args:
            df: DataFrame with high, low, close columns
        
        Returns:
            Series of True Range values
            
        How it works:
        TR is the greatest of three values:
        1. High - Low: Today's range
        2. |High - Previous Close|: Gap up magnitude
        3. |Low - Previous Close|: Gap down magnitude
        
        Example:
        Yesterday Close: $43,000
        Today High: $43,800, Low: $43,200
        
        TR = max(
            43,800 - 43,200 = 600,  # Today's range
            |43,800 - 43,000| = 800, # Gap up from yesterday
            |43,200 - 43,000| = 200  # Gap down from yesterday
        ) = 800
        
        Why not just High - Low?
        - Gaps are important! A $1000 gap + $500 range = $1500 total movement
        - TR captures TOTAL volatility including overnight gaps
        """
        high = df['high']
        low = df['low']
        close = df['close']
        prev_close = close.shift(1)
        
        # Calculate three ranges
        range1 = high - low
        range2 = (high - prev_close).abs()
        range3 = (low - prev_close).abs()
        
        # True Range is the maximum of the three
        tr = pd.concat([range1, range2, range3], axis=1).max(axis=1)
        
        return tr
    
    def wilder_smoothing(self, series: pd.Series, period: int) -> pd.Series:
        """
        Apply Wilder's Smoothing (RMA) - same as ta.rma() in Pine Script
        
        This is the same smoothing used in RSI and ADX
        
        Args:
            series: Series to smooth (True Range values)
            period: Smoothing period (14)
        
        Returns:
            Smoothed series (ATR values)
            
        How Wilder's Smoothing Works:
        - More weight to recent data than SMA
        - Less weight to recent data than EMA
        - Smoother than EMA, responds slower
        
        Formula:
        - First value: SMA of first N values
        - Next values: Previous + (alpha × (Current - Previous))
          where alpha = 1/N
        
        Example with period=14:
        - alpha = 1/14 = 0.0714 (7.14% weight to new data)
        - 92.86% weight to previous ATR
        - Very smooth, slow to change
        """
        alpha = 1.0 / period
        return series.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ATR (Average True Range)
        
        This matches Pine Script ta.atr(length) exactly
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: high, low, close
        
        Returns:
            DataFrame with one new column added:
            - atr: Average True Range (volatility measure)
            
        Process:
        1. Calculate True Range (TR) for each candle
        2. Apply Wilder's smoothing to TR
        3. Result is ATR
        
        Interpretation Examples:
        BTC/USDT 1h:
        - ATR = $800: Typical 1h move is $800
        - ATR = $1,500: Volatile (large moves expected)
        - ATR = $300: Calm (small moves expected)
        
        ETH/USDT 1h:
        - ATR = $50: Typical 1h move is $50
        - Use for stop-loss sizing
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.length + 10
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for ATR calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate True Range (TR)
        # TR measures the total price movement including gaps
        # This is the raw volatility per candle
        tr = self.calculate_true_range(df)
        
        # Step 2: Apply Wilder's Smoothing to get ATR
        # This smooths out the TR to show average volatility
        # Wilder's smoothing (RMA) is slower than EMA, very smooth
        # ATR = RMA(TR, 14)
        df['atr'] = self.wilder_smoothing(tr, self.length)
        
        # Step 3: Round to 8 decimal places (price precision)
        df['atr'] = df['atr'].round(8)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['atr']
        """
        return ['atr']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/atr.py
    
    This will:
    1. Calculate ATR for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show volatility analysis
    """
    print("=" * 80)
    print("ATR CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your ATR Settings:")
    print(f"   ATR Length: 14 periods (Wilder's original)")
    print(f"   Smoothing: RMA (Wilder's smoothing)")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings (14)
    calc = ATRCalculator(length=14)
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} ATR values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} ATR values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ ATR CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Use ATR:")
    print("   Stop-Loss: Entry - (2 × ATR)")
    print("   Take-Profit: Entry + (3 × ATR)")
    print("   Position Size: Account Risk / ATR")
    print("   SuperTrend: Price ± (Factor × ATR)")
    print("")
    print("   Volatility Levels:")
    print("   • High ATR = Large moves expected (widen stops)")
    print("   • Low ATR = Small moves expected (tighten stops)")
    print("   • Rising ATR = Increasing volatility (trending)")
    print("   • Falling ATR = Decreasing volatility (consolidating)")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see ATR data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       ROUND(i.atr::numeric, 2) as atr,")
    print("       ROUND((c.close - (i.atr * 2))::numeric, 2) as stop_loss,")
    print("       ROUND((c.close + (i.atr * 3))::numeric, 2) as take_profit,")
    print("       CASE ")
    print("           WHEN i.atr > LAG(i.atr, 5) OVER (ORDER BY c.datetime)")
    print("               THEN '📈 Increasing Volatility'")
    print("           WHEN i.atr < LAG(i.atr, 5) OVER (ORDER BY c.datetime)")
    print("               THEN '📉 Decreasing Volatility'")
    print("           ELSE '➡️ Stable'")
    print("       END as volatility_trend")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)