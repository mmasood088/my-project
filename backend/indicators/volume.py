"""
Volume Analyzer - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Analyze volume to confirm price movements and detect accumulation/distribution

Volume is the number of shares/contracts traded during a period.
High volume = strong conviction in price movement
Low volume = weak conviction, possible reversal

Your Volume Classification System:
- High Volume (H): Volume > 1.5× average (strong conviction)
- Normal Volume (N): Volume between 0.5× and 1.5× average (standard)
- Low Volume (L): Volume < 0.5× average (weak, cautious)

Why Volume Matters:
1. Confirmation: High volume confirms trend validity
2. Divergence: Price up + low volume = weak, likely reversal
3. Accumulation: High volume at support = smart money buying
4. Distribution: High volume at resistance = smart money selling

Your Settings:
- Volume Average Length: 20 periods (SMA of volume)
- High Threshold: 1.5× average (50% above normal)
- Low Threshold: 0.5× average (50% below normal)

Trading Logic (from your Pine Script):
- BUY signal + High volume (H): +1.5 points (strong confirmation)
- BUY signal + Normal volume (N): 0 points (neutral)
- BUY signal + Low volume (L): -1.0 points (weak signal, caution)

Scoring Impact (from your dashboard):
Intraday:
- High volume during signal: +1.5 points
- Low volume during signal: -1.0 points

Swing:
- High volume during signal: +2.0 points (more important)
- Low volume during signal: -1.5 points
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class VolumeAnalyzer(BaseCalculator):
    """
    Volume Analyzer - Exactly matches your TradingView Pine Script
    
    Components:
    1. Volume Average: 20-period SMA of volume
       - This is the baseline "normal" volume
       - Calculated same as price SMA
    
    2. Volume Ratio: Current Volume / Average Volume
       - Ratio > 1.5: High volume (50% above average)
       - Ratio 0.5-1.5: Normal volume
       - Ratio < 0.5: Low volume (50% below average)
    
    3. Volume Signal: Classification (H/N/L)
       - H: High volume (strong conviction)
       - N: Normal volume (standard activity)
       - L: Low volume (weak, cautious)
    
    How to Use Volume Signals:
    - Price breakout + H volume = Valid breakout (trade it)
    - Price breakout + L volume = False breakout (avoid)
    - Uptrend + H volume = Strong trend (stay in)
    - Uptrend + L volume = Weakening trend (prepare exit)
    - Price at support + H volume = Accumulation (bullish)
    - Price at resistance + H volume = Distribution (bearish)
    """
    
    def __init__(self, avg_length: int = 20, high_threshold: float = 1.5, low_threshold: float = 0.5):
        """
        Initialize Volume Analyzer with your TradingView settings
        
        Args:
            avg_length: Period for volume average (default 20, matches your Pine Script)
            high_threshold: Multiplier for high volume (default 1.5 = 150% of average)
            low_threshold: Multiplier for low volume (default 0.5 = 50% of average)
        
        Note: These are your exact TradingView settings
        """
        super().__init__("Volume")
        self.avg_length = avg_length
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold
    
    def calculate_volume_average(self, volume: pd.Series, period: int) -> pd.Series:
        """
        Calculate Simple Moving Average of volume
        
        This matches Pine Script ta.sma(volume, length)
        
        Args:
            volume: Series of volume values
            period: SMA period (20 in your case)
        
        Returns:
            Series of volume average values
            
        How it works:
        - Same as price SMA, but applied to volume
        - Gives the "typical" volume over last 20 periods
        - Used as baseline to compare current volume
        
        Example:
        Last 20 volumes: [100K, 120K, 90K, ..., 110K]
        Average: 105K
        Today's volume: 180K
        Ratio: 180K / 105K = 1.71 (High volume - 71% above average)
        """
        return volume.rolling(window=period, min_periods=period).mean()
    
    def classify_volume(self, volume: float, avg_volume: float) -> str:
        """
        Classify volume as High, Normal, or Low
        
        This matches your Pine Script volume classification logic
        
        Args:
            volume: Current volume
            avg_volume: Average volume (20-period SMA)
        
        Returns:
            String: 'H', 'N', or 'L'
            
        Classification Logic:
        - H (High): Volume > 1.5× average
          Example: Volume=180K, Avg=100K, Ratio=1.8 → H
        
        - L (Low): Volume < 0.5× average
          Example: Volume=40K, Avg=100K, Ratio=0.4 → L
        
        - N (Normal): Everything else
          Example: Volume=110K, Avg=100K, Ratio=1.1 → N
        """
        if pd.isna(volume) or pd.isna(avg_volume) or avg_volume == 0:
            return 'N'
        
        # Convert to float to avoid Decimal type issues
        volume = float(volume)
        avg_volume = float(avg_volume)
        
        # Calculate volume ratio
        ratio = volume / avg_volume
        
        # Classify based on thresholds
        if ratio > self.high_threshold:
            return 'H'  # High volume (strong conviction)
        elif ratio < self.low_threshold:
            return 'L'  # Low volume (weak, cautious)
        else:
            return 'N'  # Normal volume (standard activity)
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate volume average and classification
        
        This matches your Pine Script volume analysis exactly
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: volume
        
        Returns:
            DataFrame with two new columns added:
            - volume_avg: 20-period SMA of volume (baseline)
            - volume_signal: Classification (H/N/L)
            
        Process:
        1. Calculate volume average (20-period SMA)
        2. For each candle, classify volume as H/N/L
        3. Store both average and classification
        
        Example Output:
        datetime            | volume  | volume_avg | volume_signal
        --------------------|---------|------------|---------------
        2024-12-26 10:00:00 | 180,000 | 105,000    | H  (High)
        2024-12-26 11:00:00 | 95,000  | 106,000    | N  (Normal)
        2024-12-26 12:00:00 | 42,000  | 104,000    | L  (Low)
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.avg_length + 10
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for Volume calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate volume average (20-period SMA)
        # This is the baseline "normal" volume
        # Used to compare current volume against
        df['volume_avg'] = self.calculate_volume_average(df['volume'], self.avg_length)
        
        # Step 2: Classify each candle's volume
        # Compare current volume to average
        # Assign H/N/L based on ratio
        df['volume_signal'] = df.apply(
            lambda row: self.classify_volume(row['volume'], row['volume_avg'])
            if pd.notna(row['volume_avg']) else 'N',
            axis=1
        )
        
        # Step 3: Round volume average to 2 decimal places
        # (Volume can be fractional in crypto)
        df['volume_avg'] = df['volume_avg'].round(2)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['volume_avg', 'volume_signal']
        """
        return ['volume_avg', 'volume_signal']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/volume.py
    
    This will:
    1. Calculate Volume analysis for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show volume distribution statistics
    """
    print("=" * 80)
    print("VOLUME ANALYZER TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your Volume Settings:")
    print(f"   Volume Average Length: 20 periods (SMA)")
    print(f"   High Volume Threshold: 1.5× average (150%)")
    print(f"   Low Volume Threshold: 0.5× average (50%)")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize analyzer with YOUR settings (20, 1.5, 0.5)
    calc = VolumeAnalyzer(avg_length=20, high_threshold=1.5, low_threshold=0.5)
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} Volume values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} Volume values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ VOLUME ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read Volume Signals:")
    print("   H (High): Volume > 1.5× average → Strong conviction")
    print("   N (Normal): Volume 0.5-1.5× average → Standard activity")
    print("   L (Low): Volume < 0.5× average → Weak, cautious")
    print("")
    print("   Trading Tips:")
    print("   • Breakout + H volume = Valid (trade it)")
    print("   • Breakout + L volume = False breakout (avoid)")
    print("   • BUY signal + H volume = Strong confirmation (+1.5 pts)")
    print("   • BUY signal + L volume = Weak signal (-1.0 pts)")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see Volume data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       c.volume,")
    print("       ROUND(i.volume_avg::numeric, 0) as avg_volume,")
    print("       ROUND((c.volume / i.volume_avg)::numeric, 2) as volume_ratio,")
    print("       i.volume_signal,")
    print("       CASE ")
    print("           WHEN i.volume_signal = 'H' THEN '🔴 High - Strong Conviction'")
    print("           WHEN i.volume_signal = 'L' THEN '🔵 Low - Weak Signal'")
    print("           ELSE '⚪ Normal - Standard'")
    print("       END as interpretation")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)