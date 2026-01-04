"""
ADX Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate ADX (trend strength) and DI+/DI- (trend direction)

ADX (Average Directional Index):
- Measures trend STRENGTH (not direction)
- Range: 0-100 (typically 0-60)
- ADX > 25: Strong trend (trade with trend)
- ADX < 20: Weak trend / consolidation (avoid trend trades)

DI+ (Directional Indicator Plus):
- Measures bullish pressure
- When DI+ > DI-: Buyers in control (uptrend)

DI- (Directional Indicator Minus):
- Measures bearish pressure
- When DI- > DI+: Sellers in control (downtrend)

Your Settings:
- DI Length: 14 periods (how fast DI responds)
- ADX Smoothing: 14 periods (how smooth ADX line is)

Trading Logic (from your Pine Script):
- Strong uptrend: ADX > 25 AND DI+ > DI-
- Strong downtrend: ADX > 25 AND DI- > DI+
- Consolidation: ADX < 20 (avoid trending strategies)
- Trend reversal: DI+ crosses DI- (or vice versa)

Scoring Impact (from your dashboard):
Intraday:
- ADX > 25: +2.0 points (strong trend confirmed)
- DI+ > DI-: Directional bonus

Swing:
- ADX > 25: +3.0 points (trend strength important)
- DI crossover: Entry timing signal
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class ADXCalculator(BaseCalculator):
    """
    ADX Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. TR (True Range): Maximum of:
       - High - Low
       - |High - Previous Close|
       - |Low - Previous Close|
    
    2. +DM (Positive Directional Movement):
       - If (High - Previous High) > (Previous Low - Low):
         +DM = Max(High - Previous High, 0)
       - Else: +DM = 0
    
    3. -DM (Negative Directional Movement):
       - If (Previous Low - Low) > (High - Previous High):
         -DM = Max(Previous Low - Low, 0)
       - Else: -DM = 0
    
    4. +DI (Positive Directional Indicator):
       - +DI = 100 × (Smoothed +DM / Smoothed TR)
    
    5. -DI (Negative Directional Indicator):
       - -DI = 100 × (Smoothed -DM / Smoothed TR)
    
    6. DX (Directional Index):
       - DX = 100 × |+DI - -DI| / (+DI + -DI)
    
    7. ADX (Average Directional Index):
       - ADX = Smoothed DX (using Wilder's smoothing)
    """
    
    def __init__(self, di_length: int = 14, adx_smoothing: int = 14):
        """
        Initialize ADX calculator with your TradingView settings
        
        Args:
            di_length: Period for DI calculation (default 14, matches your Pine Script)
            adx_smoothing: Period for ADX smoothing (default 14, matches your Pine Script)
        
        Note: Both use 14 periods (your exact TradingView settings)
        """
        super().__init__("ADX")
        self.di_length = di_length
        self.adx_smoothing = adx_smoothing
    
    def calculate_true_range(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate True Range (TR) - measures volatility
        
        This matches Pine Script ta.tr() function
        
        Args:
            df: DataFrame with high, low, close columns
        
        Returns:
            Series of True Range values
            
        How it works:
        TR is the greatest of:
        1. Current High - Current Low (today's range)
        2. |Current High - Previous Close| (gap up)
        3. |Current Low - Previous Close| (gap down)
        
        Example:
        Yesterday Close: 100
        Today High: 105, Low: 98
        TR = max(105-98, |105-100|, |98-100|)
           = max(7, 5, 2) = 7
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
    
    def calculate_directional_movement(self, df: pd.DataFrame) -> tuple:
        """
        Calculate +DM and -DM (Directional Movements)
        
        This matches Pine Script directional movement calculation
        
        Args:
            df: DataFrame with high, low columns
        
        Returns:
            Tuple of (+DM series, -DM series)
            
        How it works:
        +DM (Positive Directional Movement):
        - Measures upward price movement
        - +DM = High - Previous High (if positive and > downward movement)
        
        -DM (Negative Directional Movement):
        - Measures downward price movement
        - -DM = Previous Low - Low (if positive and > upward movement)
        
        Example:
        Yesterday: High=105, Low=98
        Today: High=108, Low=100
        
        Up move = 108 - 105 = 3
        Down move = 100 - 98 = 2
        
        Since up move > down move:
        +DM = 3, -DM = 0
        """
        high = df['high']
        low = df['low']
        
        # Calculate price movements
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        
        # Initialize +DM and -DM
        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)
        
        # Assign +DM when up_move > down_move and up_move > 0
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        
        # Assign -DM when down_move > up_move and down_move > 0
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        
        return pd.Series(plus_dm, index=df.index), pd.Series(minus_dm, index=df.index)
    
    def wilder_smoothing(self, series: pd.Series, period: int) -> pd.Series:
        """
        Apply Wilder's Smoothing (same as RMA in Pine Script)
        
        This matches Pine Script ta.rma() function
        
        Args:
            series: Series to smooth
            period: Smoothing period
        
        Returns:
            Smoothed series
            
        How it works:
        Wilder's smoothing is a type of exponential moving average:
        - First value: Simple average of first N values
        - Subsequent values: Previous smoothed value + (1/N × (Current - Previous))
        
        This gives more weight to recent data but smoother than EMA
        """
        alpha = 1.0 / period
        return series.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate ADX, DI+, and DI-
        
        This matches your Pine Script ADX calculation exactly
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: high, low, close
        
        Returns:
            DataFrame with three new columns added:
            - di_plus: Positive Directional Indicator (0-100)
            - di_minus: Negative Directional Indicator (0-100)
            - adx: Average Directional Index (0-100, typically 0-60)
            
        Process:
        1. Calculate True Range (TR)
        2. Calculate +DM and -DM
        3. Smooth TR, +DM, -DM using Wilder's smoothing
        4. Calculate +DI and -DI (as percentage of smoothed TR)
        5. Calculate DX (directional index)
        6. Smooth DX to get ADX
        """
        # Validation: Check if we have enough data
        min_candles_needed = max(self.di_length, self.adx_smoothing) + 50
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for ADX calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate True Range
        # TR measures total price movement (including gaps)
        tr = self.calculate_true_range(df)
        
        # Step 2: Calculate Directional Movements (+DM and -DM)
        # These measure upward and downward price pressure
        plus_dm, minus_dm = self.calculate_directional_movement(df)
        
        # Step 3: Smooth TR, +DM, -DM using Wilder's smoothing
        # Smoothing reduces noise and makes trends clearer
        smoothed_tr = self.wilder_smoothing(tr, self.di_length)
        smoothed_plus_dm = self.wilder_smoothing(plus_dm, self.di_length)
        smoothed_minus_dm = self.wilder_smoothing(minus_dm, self.di_length)
        
        # Step 4: Calculate +DI and -DI (directional indicators)
        # These show the strength of upward vs downward movement
        # Formula: DI = 100 × (Smoothed DM / Smoothed TR)
        # Range: 0-100 (percentage of total movement)
        df['di_plus'] = 100 * (smoothed_plus_dm / smoothed_tr)
        df['di_minus'] = 100 * (smoothed_minus_dm / smoothed_tr)
        
        # Step 5: Calculate DX (Directional Index)
        # DX measures how strongly directional the market is
        # Formula: DX = 100 × |DI+ - DI-| / (DI+ + DI-)
        # High DX = strong directional movement (either up or down)
        # Low DX = choppy, non-directional movement
        di_sum = df['di_plus'] + df['di_minus']
        di_diff = (df['di_plus'] - df['di_minus']).abs()
        dx = 100 * (di_diff / di_sum)
        
        # Step 6: Smooth DX to get ADX (Average Directional Index)
        # ADX is the smoothed version of DX
        # This is the final trend strength indicator
        # ADX > 25 = strong trend (worth trading)
        # ADX < 20 = weak trend (avoid trend strategies)
        df['adx'] = self.wilder_smoothing(dx, self.adx_smoothing)
        
        # Step 7: Round to 4 decimal places
        df['di_plus'] = df['di_plus'].round(4)
        df['di_minus'] = df['di_minus'].round(4)
        df['adx'] = df['adx'].round(4)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['adx', 'di_plus', 'di_minus']
        """
        return ['adx', 'di_plus', 'di_minus']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/adx.py
    
    This will:
    1. Calculate ADX for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show trend strength analysis
    """
    print("=" * 80)
    print("ADX CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your ADX Settings:")
    print(f"   DI Length: 14 periods")
    print(f"   ADX Smoothing: 14 periods")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings (14, 14)
    calc = ADXCalculator(di_length=14, adx_smoothing=14)
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} ADX values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} ADX values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ ADX CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read ADX Values:")
    print("   ADX > 25: Strong trend (trade with trend)")
    print("   ADX 20-25: Developing trend")
    print("   ADX < 20: Weak trend / consolidation (avoid trends)")
    print("")
    print("   DI+ > DI-: Bullish trend (buyers in control)")
    print("   DI- > DI+: Bearish trend (sellers in control)")
    print("   DI+ crossing DI-: Potential trend reversal")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see ADX data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       i.adx, i.di_plus, i.di_minus,")
    print("       CASE ")
    print("           WHEN i.adx > 25 AND i.di_plus > i.di_minus THEN '🟢 Strong Uptrend'")
    print("           WHEN i.adx > 25 AND i.di_minus > i.di_plus THEN '🔴 Strong Downtrend'")
    print("           WHEN i.adx < 20 THEN '⚪ Consolidation'")
    print("           ELSE '🟡 Developing Trend'")
    print("       END as trend_status")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)