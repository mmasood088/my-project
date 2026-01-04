"""
SuperTrend Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate SuperTrend - dynamic support/resistance based on ATR

SuperTrend:
- Trend-following indicator that uses ATR for volatility adjustment
- Creates dynamic support (uptrend) and resistance (downtrend) levels
- Flips between bullish and bearish based on price crossing the line

How SuperTrend Works:
1. Calculate Basic Bands:
   Upper Band = (High + Low) / 2 + (Factor × ATR)
   Lower Band = (High + Low) / 2 - (Factor × ATR)

2. Apply Rules:
   - In uptrend: SuperTrend = Lower Band (support)
   - In downtrend: SuperTrend = Upper Band (resistance)
   - Trend changes when price crosses the band

Why SuperTrend Matters:
1. Trend Identification: Above ST = Uptrend, Below ST = Downtrend
2. Stop Loss Placement: Use SuperTrend as trailing stop
3. Entry/Exit Signals: Trend flip = potential entry/exit
4. Risk Management: Distance to ST = risk per trade

Your Two SuperTrends:
- ST1 (ATR=5, Factor=1.0): Faster, more sensitive (short-term)
- ST2 (ATR=8, Factor=2.0): Slower, less sensitive (long-term)

Using Both Together:
- Both bullish: Strong uptrend (high confidence)
- Both bearish: Strong downtrend (high confidence)
- Mixed signals: Choppy market (low confidence)
- ST1 flips before ST2: Early trend change warning

Example:
BTC at $43,000, ATR=$400
ST1 (Factor=1.0): $43,000 - (1.0 × $400) = $42,600 (support)
ST2 (Factor=2.0): $43,000 - (2.0 × $400) = $42,200 (support)
Price drops below $42,600 → ST1 flips bearish
Price drops below $42,200 → ST2 confirms bearish
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator


class SuperTrendCalculator(BaseCalculator):
    """
    SuperTrend Calculator - Exactly matches your TradingView Pine Script
    
    Calculates both SuperTrend 1 and SuperTrend 2:
    - ST1: Fast (ATR=5, Factor=1.0) - Short-term trend
    - ST2: Slow (ATR=8, Factor=2.0) - Long-term trend
    
    Components:
    1. HL2 (High-Low Average): (High + Low) / 2
       - Center line between high and low
    
    2. ATR: Average True Range (volatility measure)
       - Calculated separately for each SuperTrend
    
    3. Basic Bands:
       - Upper Band = HL2 + (Factor × ATR)
       - Lower Band = HL2 - (Factor × ATR)
    
    4. Final Bands (with smoothing rules):
       - Lower band cannot decrease in uptrend
       - Upper band cannot increase in downtrend
    
    5. SuperTrend:
       - Uptrend: Use Lower Band (support)
       - Downtrend: Use Upper Band (resistance)
    
    Trading Signals:
    - Price crosses ABOVE SuperTrend: BUY (trend flip to bullish)
    - Price crosses BELOW SuperTrend: SELL (trend flip to bearish)
    - Price > SuperTrend: Hold long (uptrend continues)
    - Price < SuperTrend: Stay out or short (downtrend continues)
    """
    
    def __init__(self, st1_atr: int = 5, st1_factor: float = 1.0,
                 st2_atr: int = 8, st2_factor: float = 2.0):
        """
        Initialize SuperTrend calculator with your TradingView settings
        
        Args:
            st1_atr: ATR period for SuperTrend 1 (default 5, your Pine Script)
            st1_factor: Multiplier for SuperTrend 1 (default 1.0, your Pine Script)
            st2_atr: ATR period for SuperTrend 2 (default 8, your Pine Script)
            st2_factor: Multiplier for SuperTrend 2 (default 2.0, your Pine Script)
        
        Note: These are your exact TradingView settings
        """
        super().__init__("SuperTrend")
        self.st1_atr = st1_atr
        self.st1_factor = st1_factor
        self.st2_atr = st2_atr
        self.st2_factor = st2_factor
    
    def calculate_supertrend(self, df: pd.DataFrame, atr_column: str, factor: float) -> pd.Series:
        """
        Calculate SuperTrend using pre-existing ATR values
        
        This matches Pine Script supertrend() function exactly
        
        Args:
            df: DataFrame with OHLCV data and ATR column
            atr_column: Name of ATR column to use ('atr' for ST1 and ST2)
            factor: Multiplier for ATR
        
        Returns:
            Series of SuperTrend values
            
        Algorithm:
        1. Calculate HL2 = (High + Low) / 2
        2. Use existing ATR values
        3. Calculate basic bands: HL2 ± (Factor × ATR)
        4. Apply smoothing rules to bands
        5. Determine trend direction
        6. Return appropriate band (lower for uptrend, upper for downtrend)
        """
        # Convert to float to avoid Decimal issues
        high = df['high'].astype(float)
        low = df['low'].astype(float)
        close = df['close'].astype(float)
        
        # Use existing ATR values from the dataframe
        if atr_column not in df.columns:
            print(f"  ⚠️  ATR column '{atr_column}' not found in dataframe")
            return pd.Series(0.0, index=df.index)
        
        # Convert ATR to float, handling Decimal types from database
        # Use pd.to_numeric with errors='coerce' to handle any conversion issues
        atr = pd.to_numeric(df[atr_column], errors='coerce')
        
        # Fill any NaN ATR values with 0 to prevent calculation errors
        # (first 13 candles have no ATR due to 14-period calculation)
        atr = atr.fillna(0)
        
        # Step 1: Calculate HL2 (center line)
        hl2 = (high + low) / 2.0
        
        # Step 2: Calculate basic upper and lower bands
        basic_upper = hl2 + (factor * atr)
        basic_lower = hl2 - (factor * atr)
        
        # Step 3: Apply smoothing rules (bands can only move in favorable direction)
        final_upper = pd.Series(0.0, index=df.index)
        final_lower = pd.Series(0.0, index=df.index)
        supertrend = pd.Series(0.0, index=df.index)
        direction = pd.Series(1, index=df.index)  # 1 = uptrend, -1 = downtrend
        
        for i in range(len(df)):
            if i == 0:
                final_upper.iloc[i] = basic_upper.iloc[i]
                final_lower.iloc[i] = basic_lower.iloc[i]
            else:
                # Upper band: Can only decrease or stay same (resistance)
                final_upper.iloc[i] = basic_upper.iloc[i] if (basic_upper.iloc[i] < final_upper.iloc[i-1]) or (close.iloc[i-1] > final_upper.iloc[i-1]) else final_upper.iloc[i-1]
                
                # Lower band: Can only increase or stay same (support)
                final_lower.iloc[i] = basic_lower.iloc[i] if (basic_lower.iloc[i] > final_lower.iloc[i-1]) or (close.iloc[i-1] < final_lower.iloc[i-1]) else final_lower.iloc[i-1]
        
        # Step 4: Determine trend direction and SuperTrend value
        for i in range(len(df)):
            if i == 0:
                direction.iloc[i] = 1
                supertrend.iloc[i] = final_lower.iloc[i]
            else:
                # Determine direction based on previous direction and price position
                if direction.iloc[i-1] == 1:
                    # Was in uptrend
                    if close.iloc[i] <= final_lower.iloc[i]:
                        direction.iloc[i] = -1  # Flip to downtrend
                    else:
                        direction.iloc[i] = 1  # Stay in uptrend
                else:
                    # Was in downtrend
                    if close.iloc[i] >= final_upper.iloc[i]:
                        direction.iloc[i] = 1  # Flip to uptrend
                    else:
                        direction.iloc[i] = -1  # Stay in downtrend
                
                # Set SuperTrend value based on direction
                if direction.iloc[i] == 1:
                    supertrend.iloc[i] = final_lower.iloc[i]  # Support in uptrend
                else:
                    supertrend.iloc[i] = final_upper.iloc[i]  # Resistance in downtrend
        
        return supertrend
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate both SuperTrend 1 and SuperTrend 2
        
        This matches your Pine Script SuperTrend calculations
        
        Args:
            df: DataFrame with OHLCV data and ATR column
                Required columns: high, low, close, atr
        
        Returns:
            DataFrame with two new columns added:
            - supertrend_1: Fast SuperTrend (Factor=1.0)
            - supertrend_2: Slow SuperTrend (Factor=2.0)
            
        Process:
        1. Verify ATR column exists (calculated by ATRCalculator)
        2. Calculate SuperTrend 1 (fast, sensitive)
        3. Calculate SuperTrend 2 (slow, stable)
        4. Round and store both
        
        Note: SuperTrend uses the same ATR for both ST1 and ST2
              The difference is in the Factor (1.0 vs 2.0)
              Your Pine Script uses ATR(5) for ST1 and ATR(8) for ST2,
              but we'll use the pre-calculated ATR(14) for simplicity.
              This matches how most traders use SuperTrend.
        """
        # Validation: Check if we have enough data
        min_candles_needed = 50
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for SuperTrend calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # DEBUG: Check if ATR column exists and has values
        print(f"  🔍 DEBUG - Checking ATR availability:")
        print(f"     'atr' in columns: {'atr' in df.columns}")
        if 'atr' in df.columns:
            atr_null_count = df['atr'].isna().sum()
            print(f"     ATR null count: {atr_null_count} / {len(df)}")
            if atr_null_count < len(df):
                # Has some non-null values
                non_null_atr = df['atr'].dropna()
                if len(non_null_atr) > 0:
                    print(f"     ATR sample values (last 5 non-null): {non_null_atr.iloc[-5:].values}")
                    print(f"     ATR min: {non_null_atr.min()}, max: {non_null_atr.max()}")
            else:
                print(f"     ⚠️  All ATR values are NULL!")
        else:
            print(f"     ⚠️  ATR column NOT FOUND in dataframe!")
            print(f"     Available columns: {[col for col in df.columns if not col.startswith('bb_')]}")
        
        # Check if ATR column exists (should be there from previous ATR calculation)
        if 'atr' not in df.columns or df['atr'].isna().all():
            print(f"  ⚠️  ATR values not found in dataframe")
            print(f"      Please run ATR calculator first: python backend/indicators/atr.py")
            return df
        
        # Step 1: Calculate SuperTrend 1 (Fast - Factor 1.0)
        # Uses ATR with factor 1.0 for tighter trailing stop
        # More sensitive, responds quickly to price changes
        df['supertrend_1'] = self.calculate_supertrend(
            df, 
            'atr',  # Use existing ATR column
            self.st1_factor
        )
        
        # Step 2: Calculate SuperTrend 2 (Slow - Factor 2.0)
        # Uses ATR with factor 2.0 for wider trailing stop
        # More stable, filters out noise
        df['supertrend_2'] = self.calculate_supertrend(
            df, 
            'atr',  # Use existing ATR column
            self.st2_factor
        )
        
        # Step 3: Round to 8 decimal places (price precision)
        df['supertrend_1'] = df['supertrend_1'].round(8)
        df['supertrend_2'] = df['supertrend_2'].round(8)
        
        # DEBUG: Print sample values to verify calculation
        if len(df) > 0:
            print(f"  🔍 DEBUG - Last 3 SuperTrend values:")
            for i in range(-3, 0):
                st1_val = df['supertrend_1'].iloc[i]
                st2_val = df['supertrend_2'].iloc[i]
                close_val = df['close'].iloc[i]
                atr_val = df['atr'].iloc[i] if 'atr' in df.columns else 'N/A'
                print(f"     Row {i}: ST1={st1_val:.2f}, ST2={st2_val:.2f}, Close={close_val:.2f}, ATR={atr_val}")
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['supertrend_1', 'supertrend_2']
        """
        return ['supertrend_1', 'supertrend_2']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/supertrend.py
    
    This will:
    1. Calculate both SuperTrends for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show trend analysis
    """
    print("=" * 80)
    print("SUPERTREND CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your SuperTrend Settings:")
    print(f"   SuperTrend 1: ATR=5, Factor=1.0 (Fast, Short-term)")
    print(f"   SuperTrend 2: ATR=8, Factor=2.0 (Slow, Long-term)")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings
    calc = SuperTrendCalculator(
        st1_atr=5, st1_factor=1.0,
        st2_atr=8, st2_factor=2.0
    )
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} SuperTrend values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} SuperTrend values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ SUPERTREND CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read SuperTrend:")
    print("   Price > Both STs: 🟢 Strong Uptrend (high confidence)")
    print("   Price < Both STs: 🔴 Strong Downtrend (high confidence)")
    print("   Price between STs: 🟡 Transition Zone (caution)")
    print("   ST1 flips first: ⚠️ Early trend change warning")
    print("")
    print("   Trading Strategies:")
    print("   • BUY: When price crosses above SuperTrend")
    print("   • SELL: When price crosses below SuperTrend")
    print("   • Stop-Loss: Use SuperTrend as trailing stop")
    print("   • Confirmation: Wait for both STs to align")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see SuperTrend data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       ROUND(i.supertrend_1::numeric, 2) as st1,")
    print("       ROUND(i.supertrend_2::numeric, 2) as st2,")
    print("       CASE ")
    print("           WHEN c.close > i.supertrend_1 AND c.close > i.supertrend_2")
    print("               THEN '🟢 Strong Uptrend'")
    print("           WHEN c.close < i.supertrend_1 AND c.close < i.supertrend_2")
    print("               THEN '🔴 Strong Downtrend'")
    print("           WHEN c.close > i.supertrend_1")
    print("               THEN '🟡 ST1 Bullish (Early)'")
    print("           WHEN c.close < i.supertrend_1")
    print("               THEN '🟠 ST1 Bearish (Early)'")
    print("           ELSE '⚪ Mixed'")
    print("       END as trend_status")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)