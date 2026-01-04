"""
Bollinger Bands Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate Bollinger Bands with squeeze detection and position tracking

Bollinger Bands show price volatility using standard deviation bands around a moving average.
When bands narrow = low volatility (squeeze) = potential breakout coming
When bands widen = high volatility = strong trend

Your Custom BB System:
- BB Basis: 20-period SMA (middle line)
- BB Band 1: ±1.0 standard deviations (inner band)
- BB Band 2: ±2.0 standard deviations (middle band) - STANDARD
- BB Band 3: ±3.0 standard deviations (outer band)
- BB Squeeze: Width < 4.0% of price
- BB Position: 7-zone system (BB3↓, BB2↓, BB1↓, BB~, BB1↑, BB2↑, BB3↑)

Why 3 bands instead of standard 2?
- More granular position tracking
- Better squeeze detection
- More precise entry/exit zones
- Matches institutional trading levels
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class BollingerBandsCalculator(BaseCalculator):
    """
    Bollinger Bands Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. BB Basis (Middle Line): 20-period SMA of close price
    2. BB Upper Bands: Basis + (StdDev × Multiplier) for 1.0, 2.0, 3.0
    3. BB Lower Bands: Basis - (StdDev × Multiplier) for 1.0, 2.0, 3.0
    4. BB Width: ((Upper2 - Lower2) / Basis) × 100
    5. BB Squeeze: Boolean (Width < 4.0%)
    6. BB Position: Where price is relative to bands
    
    BB Position Labels (from your Pine Script):
    - BB3↓: Price below Lower Band 3 (extreme oversold)
    - BB2↓: Price between Lower Band 2 and 3 (oversold)
    - BB1↓: Price between Lower Band 1 and 2 (slightly oversold)
    - BB~: Price between Lower Band 1 and Upper Band 1 (neutral)
    - BB1↑: Price between Upper Band 1 and 2 (slightly overbought)
    - BB2↑: Price between Upper Band 2 and 3 (overbought)
    - BB3↑: Price above Upper Band 3 (extreme overbought)
    
    Trading Signals (from your dashboard logic):
    - BB Squeeze = true: Consolidation, breakout imminent
    - Price at BB3↓: Strong buy opportunity (extreme deviation)
    - Price at BB3↑: Strong sell signal (extreme deviation)
    - Price bouncing from Lower Band 2: Bullish reversal
    - Price rejecting Upper Band 2: Bearish reversal
    """
    
    def __init__(self, length: int = 20, mult_1: float = 1.0, 
                 mult_2: float = 2.0, mult_3: float = 3.0, 
                 squeeze_threshold: float = 4.0):
        """
        Initialize Bollinger Bands calculator with your TradingView settings
        
        Args:
            length: Period for SMA and StdDev (default 20, matches your Pine Script)
            mult_1: Multiplier for inner band (default 1.0)
            mult_2: Multiplier for middle band (default 2.0) - STANDARD
            mult_3: Multiplier for outer band (default 3.0)
            squeeze_threshold: BB width % threshold for squeeze (default 4.0%)
        
        Note: These are your exact TradingView settings
        """
        super().__init__("Bollinger Bands")
        self.length = length
        self.mult_1 = mult_1
        self.mult_2 = mult_2
        self.mult_3 = mult_3
        self.squeeze_threshold = squeeze_threshold
    
    def calculate_sma(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average (BB Basis)
        
        This matches Pine Script ta.sma() function
        
        Args:
            prices: Series of close prices
            period: SMA period (20 in your case)
        
        Returns:
            Series of SMA values (BB Basis / middle line)
            
        How it works:
        - Sum of last N prices / N
        - Equal weight to all prices in window
        - Used as centerline for BB calculation
        """
        return prices.rolling(window=period, min_periods=period).mean()
    
    def calculate_stdev(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calculate Standard Deviation (measure of volatility)
        
        This matches Pine Script ta.stdev() function
        
        Args:
            prices: Series of close prices
            period: StdDev period (20 in your case)
        
        Returns:
            Series of standard deviation values
            
        How it works:
        - Measures how much price deviates from average
        - High StdDev = high volatility = wide bands
        - Low StdDev = low volatility = narrow bands (squeeze)
        - Formula: sqrt(sum((price - mean)²) / N)
        """
        return prices.rolling(window=period, min_periods=period).std()
    
    def get_bb_position(self, price: float, upper_1: float, upper_2: float, upper_3: float,
                       lower_1: float, lower_2: float, lower_3: float) -> str:
        """
        Determine which BB zone the price is in
        
        This matches your Pine Script BB position logic
        
        Args:
            price: Current close price
            upper_1/2/3: Upper band values
            lower_1/2/3: Lower band values
        
        Returns:
            String: BB3↓, BB2↓, BB1↓, BB~, BB1↑, BB2↑, or BB3↑
            
        Zone Logic (from bottom to top):
        1. Below Lower3 = BB3↓ (extreme oversold, rare)
        2. Between Lower2 and Lower3 = BB2↓ (oversold)
        3. Between Lower1 and Lower2 = BB1↓ (slightly oversold)
        4. Between Lower1 and Upper1 = BB~ (neutral zone)
        5. Between Upper1 and Upper2 = BB1↑ (slightly overbought)
        6. Between Upper2 and Upper3 = BB2↑ (overbought)
        7. Above Upper3 = BB3↑ (extreme overbought, rare)
        """
        # Check from extreme to neutral
        if price < lower_3:
            return "BB3↓"
        elif price < lower_2:
            return "BB2↓"
        elif price < lower_1:
            return "BB1↓"
        elif price <= upper_1:
            return "BB~"
        elif price <= upper_2:
            return "BB1↑"
        elif price <= upper_3:
            return "BB2↑"
        else:
            return "BB3↑"
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all Bollinger Bands components
        
        This matches your Pine Script BB calculation exactly
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: close (price data)
        
        Returns:
            DataFrame with 11 new columns added:
            - bb_basis: Middle line (20-period SMA)
            - bb_upper_1/2/3: Upper bands (1σ, 2σ, 3σ)
            - bb_lower_1/2/3: Lower bands (1σ, 2σ, 3σ)
            - bb_width: Band width as % of price
            - bb_squeeze: Boolean (True if width < 4%)
            - bb_position: Position label (BB3↓ to BB3↑)
            
        Process:
        1. Calculate BB Basis (20-period SMA)
        2. Calculate Standard Deviation (20-period)
        3. Calculate 6 bands (3 upper, 3 lower)
        4. Calculate width percentage
        5. Detect squeeze condition
        6. Determine price position
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.length + 10
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for BB calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate BB Basis (middle line / 20-period SMA)
        # This is the centerline around which bands are drawn
        df['bb_basis'] = self.calculate_sma(df['close'], self.length)
        
        # Step 2: Calculate Standard Deviation (volatility measure)
        # Higher StdDev = wider bands = higher volatility
        # Lower StdDev = narrower bands = lower volatility
        stdev = self.calculate_stdev(df['close'], self.length)
        
        # Step 3: Calculate Upper Bands (Basis + StdDev × Multiplier)
        # Band 1 (±1σ): Inner band, catches ~68% of price action
        df['bb_upper_1'] = df['bb_basis'] + (stdev * self.mult_1)
        df['bb_lower_1'] = df['bb_basis'] - (stdev * self.mult_1)
        
        # Band 2 (±2σ): Standard BB, catches ~95% of price action
        df['bb_upper_2'] = df['bb_basis'] + (stdev * self.mult_2)
        df['bb_lower_2'] = df['bb_basis'] - (stdev * self.mult_2)
        
        # Band 3 (±3σ): Outer band, catches ~99.7% of price action
        # Price beyond this = extreme deviation, strong reversal signal
        df['bb_upper_3'] = df['bb_basis'] + (stdev * self.mult_3)
        df['bb_lower_3'] = df['bb_basis'] - (stdev * self.mult_3)
        
        # Step 4: Calculate BB Width (as % of price)
        # Width = ((Upper2 - Lower2) / Basis) × 100
        # This measures volatility as a percentage
        # Example: Width = 8% means bands span 8% of price
        df['bb_width'] = ((df['bb_upper_2'] - df['bb_lower_2']) / df['bb_basis']) * 100
        
        # Step 5: Detect BB Squeeze (width < threshold)
        # Squeeze = Low volatility = Consolidation
        # Often precedes strong breakout (up or down)
        # Your threshold: 4.0% (tighter than typical 3.0%)
        # Convert to Python bool (True/False) instead of numpy bool
        df['bb_squeeze'] = (df['bb_width'] < self.squeeze_threshold).astype(bool)
        
        # Step 6: Determine BB Position for each candle
        # This tells us which zone price is in (7 possible zones)
        df['bb_position'] = df.apply(
            lambda row: self.get_bb_position(
                row['close'],
                row['bb_upper_1'], row['bb_upper_2'], row['bb_upper_3'],
                row['bb_lower_1'], row['bb_lower_2'], row['bb_lower_3']
            ) if pd.notna(row['bb_basis']) else None,
            axis=1
        )
        
        # Step 7: Round values to appropriate precision
        # BB bands: 8 decimals (price precision)
        # BB width: 4 decimals (percentage)
        df['bb_basis'] = df['bb_basis'].round(8)
        df['bb_upper_1'] = df['bb_upper_1'].round(8)
        df['bb_lower_1'] = df['bb_lower_1'].round(8)
        df['bb_upper_2'] = df['bb_upper_2'].round(8)
        df['bb_lower_2'] = df['bb_lower_2'].round(8)
        df['bb_upper_3'] = df['bb_upper_3'].round(8)
        df['bb_lower_3'] = df['bb_lower_3'].round(8)
        df['bb_width'] = df['bb_width'].round(4)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of 9 column names for all BB components
            
        Note: bb_width is NOT stored (calculated on-the-fly when needed)
        """
        return [
            'bb_basis',      # Middle line (SMA)
            'bb_upper_1',    # Upper band 1σ
            'bb_lower_1',    # Lower band 1σ
            'bb_upper_2',    # Upper band 2σ (standard)
            'bb_lower_2',    # Lower band 2σ (standard)
            'bb_upper_3',    # Upper band 3σ
            'bb_lower_3',    # Lower band 3σ
            'bb_squeeze',    # Boolean: Is squeeze active?
            'bb_position'    # Position label (BB3↓ to BB3↑)
        ]

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/bollinger_bands.py
    
    This will:
    1. Calculate BB for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show squeeze detection and position distribution
    """
    print("=" * 80)
    print("BOLLINGER BANDS CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your BB Settings:")
    print(f"   BB Length: 20 periods (SMA + StdDev)")
    print(f"   Band Multipliers: 1.0σ, 2.0σ, 3.0σ")
    print(f"   Squeeze Threshold: 4.0% width")
    print(f"   Position Zones: 7 levels (BB3↓ to BB3↑)")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings
    calc = BollingerBandsCalculator(
        length=20,
        mult_1=1.0,
        mult_2=2.0,
        mult_3=3.0,
        squeeze_threshold=4.0
    )
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} BB values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} BB values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ BOLLINGER BANDS CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read BB Values:")
    print("   BB Squeeze = true: Low volatility, breakout coming")
    print("   BB3↓: Extreme oversold (price < lower band 3)")
    print("   BB2↓: Oversold (price between lower bands 2-3)")
    print("   BB~: Neutral (price between ±1σ bands)")
    print("   BB2↑: Overbought (price between upper bands 2-3)")
    print("   BB3↑: Extreme overbought (price > upper band 3)")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see BB data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       i.bb_basis, i.bb_upper_2, i.bb_lower_2,")
    print("       i.bb_width, i.bb_squeeze, i.bb_position")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)