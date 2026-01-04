"""
RSI Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate RSI and RSI-EMA exactly as in Pine Script
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class RSICalculator(BaseCalculator):
    """
    RSI (Relative Strength Index) Calculator
    
    Matches TradingView Pine Script settings:
    - RSI Length: 14 (customizable via rsiLength parameter)
    - RSI-EMA Length: 21 (customizable via rsiEmaLength parameter)
    - Crossover Lookback: 5 bars (for detecting bullish/bearish crosses)
    
    Calculation Method:
    1. Calculate price changes (delta = current close - previous close)
    2. Separate gains (positive changes) and losses (negative changes)
    3. Apply Wilder's smoothing (exponential moving average with alpha = 1/period)
    4. Calculate RS (Relative Strength) = avg_gain / avg_loss
    5. Calculate RSI = 100 - (100 / (1 + RS))
    6. Apply EMA to RSI values to get RSI-EMA (smoothed trend)
    
    Output Columns:
    - rsi: Raw RSI value (0-100)
    - rsi_ema: Exponential moving average of RSI (trend indicator)
    
    Usage in TradingView Dashboard:
    - RSI > 70: Overbought (potential sell signal)
    - RSI < 30: Oversold (potential buy signal)
    - RSI crossing above RSI-EMA: Bullish momentum
    - RSI crossing below RSI-EMA: Bearish momentum
    """
    
    def __init__(self, rsi_length: int = 14, rsi_ema_length: int = 21):
        """
        Initialize RSI calculator with your TradingView settings
        
        Args:
            rsi_length: Period for RSI calculation (default 14, matches Pine Script)
            rsi_ema_length: Period for EMA applied to RSI (default 21, matches Pine Script)
        
        Note: These defaults match your TradingView dashboard settings
        """
        super().__init__("RSI")
        self.rsi_length = rsi_length
        self.rsi_ema_length = rsi_ema_length
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """
        Calculate RSI using Wilder's smoothing method (same as Pine Script ta.rsi())
        
        This matches the Pine Script function:
        customRSI(float src, int length) =>
            float change = ta.change(src)
            float up = ta.rma(math.max(change, 0), length)
            float down = ta.rma(-math.min(change, 0), length)
            float rsi = down == 0 ? 100 : up == 0 ? 0 : 100 - (100 / (1 + up / down))
        
        Args:
            prices: Series of close prices
            period: RSI period (default 14)
        
        Returns:
            Series of RSI values (0-100)
            
        How it works:
        1. Calculate price change (today's close - yesterday's close)
        2. Split into gains (positive changes) and losses (negative changes)
        3. Calculate average gain and average loss using exponential smoothing
        4. RSI = 100 - (100 / (1 + avg_gain/avg_loss))
        """
        # Step 1: Calculate price changes
        delta = prices.diff()
        
        # Step 2: Separate gains and losses
        # Gains: Keep positive changes, set negative changes to 0
        gain = delta.where(delta > 0, 0)
        
        # Losses: Keep negative changes (as positive values), set positive changes to 0
        loss = -delta.where(delta < 0, 0)
        
        # Step 3: Calculate Wilder's smoothed averages (same as Pine Script ta.rma)
        # alpha = 1/period gives us Wilder's smoothing method
        avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
        
        # Step 4: Calculate Relative Strength (RS)
        rs = avg_gain / avg_loss
        
        # Step 5: Calculate RSI
        # Formula: RSI = 100 - (100 / (1 + RS))
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def calculate_ema(self, values: pd.Series, period: int) -> pd.Series:
        """
        Calculate Exponential Moving Average (same as Pine Script ta.ema())
        
        Args:
            values: Series of values (in our case, RSI values)
            period: EMA period (21 in your TradingView dashboard)
        
        Returns:
            Series of EMA values
            
        How it works:
        - More weight to recent values
        - Smooths out RSI oscillations to show trend
        - In TradingView, you use this to detect RSI crossovers
        """
        return values.ewm(span=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Main calculation function - processes OHLCV data and adds RSI columns
        
        Args:
            df: DataFrame with OHLCV data (from candles table)
                Required columns: close (price data)
        
        Returns:
            DataFrame with two new columns added:
            - rsi: Raw RSI values
            - rsi_ema: EMA-smoothed RSI values
            
        Process:
        1. Check if we have enough data (need at least RSI length + 5 candles)
        2. Calculate RSI from close prices
        3. Calculate EMA of RSI values
        4. Round to 4 decimal places (matches TradingView precision)
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.rsi_length + 5
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for RSI calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate RSI from close prices
        df['rsi'] = self.calculate_rsi(df['close'], self.rsi_length)
        
        # Step 2: Calculate RSI-EMA (smoothed RSI trend)
        df['rsi_ema'] = self.calculate_ema(df['rsi'], self.rsi_ema_length)
        
        # Step 3: Round to 4 decimal places (same as TradingView display)
        df['rsi'] = df['rsi'].round(4)
        df['rsi_ema'] = df['rsi_ema'].round(4)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['rsi', 'rsi_ema']
        """
        return ['rsi', 'rsi_ema']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/rsi.py
    
    This will:
    1. Calculate RSI for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show summary statistics
    """
    print("=" * 70)
    print("RSI CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 70)
    print("\n⚙️  Settings:")
    print(f"   RSI Length: 14 periods")
    print(f"   RSI-EMA Length: 21 periods")
    print(f"   (Matches your TradingView dashboard)")
    
    # Initialize calculator with YOUR settings (14, 21)
    calc = RSICalculator(rsi_length=14, rsi_ema_length=21)
    
    # Process BTC/USDT
    print("\n" + "─" * 70)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_btc} RSI values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 70)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=500)
    print(f"✅ Stored {stored_eth} RSI values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ RSI CALCULATION COMPLETE!")
    print("=" * 70)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Query 'indicators' table to see RSI values")
    print("   3. Run this query to verify:")
    print("\n" + "─" * 70)
    print("SELECT c.symbol, c.datetime, c.close, i.rsi, i.rsi_ema")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 10;")
    print("─" * 70)