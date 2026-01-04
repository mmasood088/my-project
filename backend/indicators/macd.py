"""
MACD Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate MACD Line, Signal Line, and Histogram

MACD (Moving Average Convergence Divergence) is a trend-following momentum indicator
that shows the relationship between two moving averages of a security's price.

Your Custom Settings (Faster than traditional MACD):
- Fast EMA: 9 periods (vs traditional 12)
- Slow EMA: 21 periods (vs traditional 26)
- Signal EMA: 5 periods (vs traditional 9)
- Type: EMA for both MACD and Signal (vs traditional SMA for signal)

Why these settings are better:
- Faster response to price changes (catches trends earlier)
- Better for crypto markets (more volatile than stocks)
- Reduces lag compared to traditional MACD
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class MACDCalculator(BaseCalculator):
    """
    MACD Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. MACD Line = Fast EMA - Slow EMA
       - Shows momentum direction
       - Positive = bullish, Negative = bearish
    
    2. Signal Line = EMA of MACD Line
       - Smoothed version of MACD
       - Acts as trigger for buy/sell signals
    
    3. Histogram = MACD Line - Signal Line
       - Visual representation of MACD vs Signal
       - Positive = MACD above Signal (bullish)
       - Negative = MACD below Signal (bearish)
    
    Trading Signals:
    - MACD crosses ABOVE Signal = Bullish (potential buy)
    - MACD crosses BELOW Signal = Bearish (potential sell)
    - Histogram increasing = Momentum strengthening
    - Histogram decreasing = Momentum weakening
    """
    
    def __init__(self, fast: int = 9, slow: int = 21, signal: int = 5, 
                 ma_type: str = 'EMA', signal_type: str = 'EMA'):
        """
        Initialize MACD calculator with your TradingView settings
        
        Args:
            fast: Fast moving average period (default 9, matches your Pine Script)
            slow: Slow moving average period (default 21, matches your Pine Script)
            signal: Signal line period (default 5, matches your Pine Script)
            ma_type: Type of MA for MACD calculation ('EMA' or 'SMA')
            signal_type: Type of MA for Signal line ('EMA' or 'SMA')
        
        Note: Your settings (9/21/5) are more responsive than traditional MACD (12/26/9)
        """
        super().__init__("MACD")
        self.fast = fast
        self.slow = slow
        self.signal = signal
        self.ma_type = ma_type
        self.signal_type = signal_type
    
    def calculate_moving_average(self, prices: pd.Series, period: int, ma_type: str) -> pd.Series:
        """
        Calculate moving average (EMA or SMA)
        
        This matches your Pine Script logic:
        float fastMA = macdSourceType == "SMA" ? ta.sma(close, macdFast) : ta.ema(close, macdFast)
        
        Args:
            prices: Series of close prices
            period: Moving average period
            ma_type: 'EMA' (Exponential) or 'SMA' (Simple)
        
        Returns:
            Series of moving average values
            
        How it works:
        - EMA: Exponential Moving Average (more weight to recent prices)
        - SMA: Simple Moving Average (equal weight to all prices)
        - In your case, you use EMA for faster response to price changes
        """
        if ma_type == 'SMA':
            # Simple Moving Average - equal weight to all prices
            return prices.rolling(window=period, min_periods=period).mean()
        else:  # EMA (default)
            # Exponential Moving Average - more weight to recent prices
            return prices.ewm(span=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate MACD components: Line, Signal, and Histogram
        
        This matches your Pine Script function:
        customMACD(src, fast, slow, signal, macdType, signalType) =>
            fastMA = macdType == "SMA" ? ta.sma(src, fast) : ta.ema(src, fast)
            slowMA = macdType == "SMA" ? ta.sma(src, slow) : ta.ema(src, slow)
            macdLine = fastMA - slowMA
            signalLine = signalType == "SMA" ? ta.sma(macdLine, signal) : ta.ema(macdLine, signal)
            histogram = macdLine - signalLine
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: close (price data)
        
        Returns:
            DataFrame with three new columns added:
            - macd_line: MACD Line (Fast EMA - Slow EMA)
            - macd_signal: Signal Line (EMA of MACD Line)
            - macd_histogram: Histogram (MACD Line - Signal Line)
            
        Process:
        1. Calculate Fast EMA (9 periods)
        2. Calculate Slow EMA (21 periods)
        3. MACD Line = Fast EMA - Slow EMA
        4. Signal Line = EMA of MACD Line (5 periods)
        5. Histogram = MACD Line - Signal Line
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.slow + self.signal + 5
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for MACD calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate Fast Moving Average (9 periods)
        fast_ma = self.calculate_moving_average(df['close'], self.fast, self.ma_type)
        
        # Step 2: Calculate Slow Moving Average (21 periods)
        slow_ma = self.calculate_moving_average(df['close'], self.slow, self.ma_type)
        
        # Step 3: Calculate MACD Line (difference between fast and slow)
        # When MACD > 0: Fast MA is above Slow MA (bullish)
        # When MACD < 0: Fast MA is below Slow MA (bearish)
        df['macd_line'] = fast_ma - slow_ma
        
        # Step 4: Calculate Signal Line (smoothed MACD)
        # This is the trigger line for buy/sell signals
        df['macd_signal'] = self.calculate_moving_average(
            df['macd_line'], 
            self.signal, 
            self.signal_type
        )
        
        # Step 5: Calculate Histogram (visual representation of MACD vs Signal)
        # When Histogram > 0: MACD is above Signal (bullish momentum)
        # When Histogram < 0: MACD is below Signal (bearish momentum)
        # Increasing histogram = momentum strengthening
        # Decreasing histogram = momentum weakening
        df['macd_histogram'] = df['macd_line'] - df['macd_signal']
        
        # Step 6: Round to 8 decimal places (crypto prices can be small)
        df['macd_line'] = df['macd_line'].round(8)
        df['macd_signal'] = df['macd_signal'].round(8)
        df['macd_histogram'] = df['macd_histogram'].round(8)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['macd_line', 'macd_signal', 'macd_histogram']
        """
        return ['macd_line', 'macd_signal', 'macd_histogram']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/macd.py
    
    This will:
    1. Calculate MACD for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show summary statistics
    """
    print("=" * 70)
    print("MACD CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 70)
    print("\n⚙️  Your Custom MACD Settings:")
    print(f"   Fast EMA: 9 periods (vs traditional 12)")
    print(f"   Slow EMA: 21 periods (vs traditional 26)")
    print(f"   Signal: 5 periods (vs traditional 9)")
    print(f"   Type: EMA for both MACD and Signal")
    print(f"   (Faster response, better for crypto)")
    
    # Initialize calculator with YOUR settings (9, 21, 5, EMA, EMA)
    calc = MACDCalculator(fast=9, slow=21, signal=5, ma_type='EMA', signal_type='EMA')
    
    # Process BTC/USDT
    print("\n" + "─" * 70)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_btc} MACD values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 70)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_eth} MACD values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ MACD CALCULATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read MACD Values:")
    print("   MACD Line > 0: Bullish (Fast EMA above Slow EMA)")
    print("   MACD Line < 0: Bearish (Fast EMA below Slow EMA)")
    print("   Histogram > 0: MACD above Signal (bullish momentum)")
    print("   Histogram < 0: MACD below Signal (bearish momentum)")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Query 'indicators' table to see MACD values")
    print("   3. Run this query to verify:")
    print("\n" + "─" * 70)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       i.macd_line, i.macd_signal, i.macd_histogram,")
    print("       CASE WHEN i.macd_histogram > 0 THEN 'Bullish'")
    print("            ELSE 'Bearish' END as signal")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 10;")
    print("─" * 70)