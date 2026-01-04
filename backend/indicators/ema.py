"""
EMA Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate EMA 44, 100, 200 for trend analysis

EMA (Exponential Moving Average) is a trend-following indicator that gives more
weight to recent prices. Faster response to price changes than Simple Moving Average.

Your EMA Stack:
- EMA 44: Short-term trend (faster response)
- EMA 100: Medium-term trend (market direction)
- EMA 200: Long-term trend (major support/resistance)

Why these periods:
- EMA 44: Catches trend changes early
- EMA 100: Classic medium-term trend indicator
- EMA 200: Most watched long-term trend line (institutional level)

EMA Stack Alignment (Bullish):
Price > EMA 44 > EMA 100 > EMA 200 = Strong uptrend
All EMAs sloping up = Momentum confirmed

EMA Stack Alignment (Bearish):
Price < EMA 44 < EMA 100 < EMA 200 = Strong downtrend
All EMAs sloping down = Downtrend confirmed
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class EMACalculator(BaseCalculator):
    """
    EMA Stack Calculator - Exactly matches your TradingView Pine Script
    
    Calculates three EMAs:
    1. EMA 44 (Short-term): Quick trend changes
    2. EMA 100 (Medium-term): Market direction
    3. EMA 200 (Long-term): Major trend
    
    Trading Logic (from your Pine Script):
    - Price > EMA = Bullish (e4Status = "↑")
    - Price < EMA = Bearish (e4Status = "↓")
    - All 3 EMAs bullish = Strong uptrend (emaStackAligned = true)
    
    Scoring Impact (from your dashboard):
    Intraday:
    - EMA 44 bullish: +2.5 points
    - EMA 100 bullish: +2.5 points
    - EMA 200 bullish: +2.0 points
    - All aligned: +1.0 bonus
    
    Swing:
    - EMA 200 bullish: +5.0 points (most important)
    - EMA 100 bullish: +4.0 points
    - EMA 44 bullish: +1.5 points
    - All aligned: +3.0 bonus
    """
    
    def __init__(self, ema_44: int = 44, ema_100: int = 100, ema_200: int = 200):
        """
        Initialize EMA calculator with your TradingView settings
        
        Args:
            ema_44: Short-term EMA period (default 44, matches your Pine Script)
            ema_100: Medium-term EMA period (default 100, matches your Pine Script)
            ema_200: Long-term EMA period (default 200, matches your Pine Script)
        
        Note: These are your exact TradingView settings
        """
        super().__init__("EMA")
        self.ema_44 = ema_44
        self.ema_100 = ema_100
        self.ema_200 = ema_200
    
    def calculate_ema(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average
        
        This matches Pine Script ta.ema() function exactly
        
        Args:
            prices: Series of close prices
            period: EMA period (44, 100, or 200)
        
        Returns:
            Series of EMA values
            
        How EMA works:
        1. Gives more weight to recent prices (exponential weighting)
        2. Responds faster to price changes than SMA
        3. Formula: EMA = Price(today) * k + EMA(yesterday) * (1 - k)
           where k = 2 / (period + 1)
        
        Example for EMA 44:
        - k = 2 / (44 + 1) = 0.0444 (4.44% weight to today's price)
        - Recent prices matter more than old prices
        """
        return prices.ewm(span=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all three EMAs: 44, 100, and 200
        
        This matches your Pine Script:
        ta.ema(close, ema4Period)  // EMA 44
        ta.ema(close, ema5Period)  // EMA 100
        ta.ema(close, ema6Period)  // EMA 200
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: close (price data)
        
        Returns:
            DataFrame with three new columns added:
            - ema_44: Short-term EMA (44 periods)
            - ema_100: Medium-term EMA (100 periods)
            - ema_200: Long-term EMA (200 periods)
            
        Process:
        1. Calculate EMA 44 from close prices
        2. Calculate EMA 100 from close prices
        3. Calculate EMA 200 from close prices
        4. Round to 8 decimal places
        
        Note: All three EMAs are independent - each only looks at price,
              not at other EMAs (unlike some indicators that build on each other)
        """
        # Validation: Check if we have enough data
        # Need at least EMA 200 + buffer for accurate calculation
        min_candles_needed = self.ema_200 + 50
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for EMA calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate EMA 44 (Short-term trend)
        # This EMA responds quickly to price changes
        # Used for catching early trend reversals
        df['ema_44'] = self.calculate_ema(df['close'], self.ema_44)
        
        # Step 2: Calculate EMA 100 (Medium-term trend)
        # This EMA shows the overall market direction
        # Acts as dynamic support/resistance
        df['ema_100'] = self.calculate_ema(df['close'], self.ema_100)
        
        # Step 3: Calculate EMA 200 (Long-term trend)
        # This is the most important EMA (watched by institutions)
        # Major support/resistance level
        # Strong signal when price crosses this line
        df['ema_200'] = self.calculate_ema(df['close'], self.ema_200)
        
        # Step 4: Round to 8 decimal places (matches price precision)
        df['ema_44'] = df['ema_44'].round(8)
        df['ema_100'] = df['ema_100'].round(8)
        df['ema_200'] = df['ema_200'].round(8)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['ema_44', 'ema_100', 'ema_200']
        """
        return ['ema_44', 'ema_100', 'ema_200']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/ema.py
    
    This will:
    1. Calculate EMA 44, 100, 200 for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show summary with EMA alignment analysis
    """
    print("=" * 70)
    print("EMA STACK CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 70)
    print("\n⚙️  Your EMA Stack Settings:")
    print(f"   EMA 44: Short-term trend (fast response)")
    print(f"   EMA 100: Medium-term trend (direction)")
    print(f"   EMA 200: Long-term trend (major support/resistance)")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings (44, 100, 200)
    calc = EMACalculator(ema_44=44, ema_100=100, ema_200=200)
    
    # Process BTC/USDT
    print("\n" + "─" * 70)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_btc} EMA values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 70)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_eth} EMA values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ EMA CALCULATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read EMA Values:")
    print("   Price > EMA 44 > EMA 100 > EMA 200: 🟢 Strong Uptrend")
    print("   Price > EMA 200: Bullish (above major support)")
    print("   Price < EMA 200: Bearish (below major resistance)")
    print("   EMA 44 crossing EMA 100: Trend change signal")
    print("   All EMAs sloping up: Momentum building")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Query 'indicators' table to see EMA values")
    print("   3. Run this query to see EMA alignment:")
    print("\n" + "─" * 70)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       i.ema_44, i.ema_100, i.ema_200,")
    print("       CASE ")
    print("           WHEN c.close > i.ema_44 AND c.close > i.ema_100 AND c.close > i.ema_200")
    print("               THEN '🟢 Strong Uptrend'")
    print("           WHEN c.close > i.ema_200 THEN '🟡 Above EMA 200'")
    print("           WHEN c.close < i.ema_200 THEN '🔴 Below EMA 200'")
    print("           ELSE '⚪ Neutral'")
    print("       END as trend_status,")
    print("       CASE ")
    print("           WHEN i.ema_44 > i.ema_100 AND i.ema_100 > i.ema_200")
    print("               THEN '✅ Bullish Alignment'")
    print("           WHEN i.ema_44 < i.ema_100 AND i.ema_100 < i.ema_200")
    print("               THEN '❌ Bearish Alignment'")
    print("           ELSE '⚠️ Mixed'")
    print("       END as ema_alignment")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 10;")
    print("─" * 70)