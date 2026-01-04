"""
OBV Calculator - Matches TradingView Pine Script Logic
Author: Your Trading System
Purpose: Calculate OBV (On-Balance Volume) - tracks volume flow and smart money

OBV (On-Balance Volume):
- Cumulative indicator that adds/subtracts volume based on price direction
- Shows whether volume is flowing INTO or OUT OF an asset
- Detects accumulation (smart money buying) and distribution (smart money selling)

How OBV Works:
- If Close > Previous Close: OBV = Previous OBV + Volume (buying pressure)
- If Close < Previous Close: OBV = Previous OBV - Volume (selling pressure)
- If Close = Previous Close: OBV = Previous OBV (no change)

Why OBV Matters:
1. Volume Confirmation: Price ↑ + OBV ↑ = Healthy uptrend (confirmed)
2. Divergence Detection: Price ↑ + OBV ↓ = Bearish divergence (reversal warning)
3. Accumulation/Distribution: OBV ↑ at support = Smart money accumulating
4. Trend Strength: Rising OBV = Strong trend, Falling OBV = Weak trend

Your Settings:
- OBV-MA Type: EMA (faster response than SMA)
- OBV-MA Length: 21 periods (smooths OBV trend)

Trading Logic (from your Pine Script):
- OBV > OBV-MA: Bullish volume flow (smart money buying)
- OBV < OBV-MA: Bearish volume flow (smart money selling)
- OBV crossing above OBV-MA: Buy signal (volume turning bullish)
- OBV crossing below OBV-MA: Sell signal (volume turning bearish)

Classic OBV Divergences:
1. Bullish Divergence: Price makes lower low, OBV makes higher low → Reversal up
2. Bearish Divergence: Price makes higher high, OBV makes lower high → Reversal down

Example:
BTC price: $40K → $42K → $44K (uptrend)
OBV: 1M → 1.2M → 1.5M (rising OBV confirms uptrend is healthy)

BTC price: $44K → $46K → $48K (still uptrend)
OBV: 1.5M → 1.4M → 1.3M (falling OBV = divergence, uptrend weakening)
"""

import pandas as pd
import numpy as np
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.base import BaseCalculator

class OBVCalculator(BaseCalculator):
    """
    OBV Calculator - Exactly matches your TradingView Pine Script
    
    Components:
    1. OBV (On-Balance Volume):
       - Cumulative sum of signed volume
       - Volume is positive when price closes up
       - Volume is negative when price closes down
       - This matches Pine Script ta.cum() function
    
    2. OBV-MA (OBV Moving Average):
       - EMA of OBV (smoothed trend line)
       - Helps identify OBV direction
       - Used for crossover signals
    
    How to Use OBV:
    - OBV trending up: Accumulation (buying pressure)
    - OBV trending down: Distribution (selling pressure)
    - OBV flat: Consolidation (balanced pressure)
    - OBV divergence from price: Warning of reversal
    
    Trading Signals:
    - Price breakout + OBV breakout = Valid breakout (trade it)
    - Price breakout + OBV flat = False breakout (avoid)
    - OBV > OBV-MA = Bullish volume flow
    - OBV < OBV-MA = Bearish volume flow
    """
    
    def __init__(self, ma_length: int = 21, ma_type: str = 'EMA'):
        """
        Initialize OBV calculator with your TradingView settings
        
        Args:
            ma_length: Period for OBV moving average (default 21, matches your Pine Script)
            ma_type: Type of MA for OBV ('EMA', 'SMA', 'RMA', 'WMA', 'VWMA')
        
        Note: You use EMA with 21 periods (your exact TradingView settings)
        """
        super().__init__("OBV")
        self.ma_length = ma_length
        self.ma_type = ma_type
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.Series:
        """
        Calculate On-Balance Volume
        
        This matches Pine Script:
        obv = ta.cum(math.sign(ta.change(close)) * volume)
        
        Args:
            df: DataFrame with close and volume columns
        
        Returns:
            Series of OBV values
            
        How it works:
        1. Calculate price change (close - previous close)
        2. Get sign of change (+1, 0, -1)
        3. Multiply sign by volume
        4. Cumulative sum = OBV
        
        Example:
        Day 1: Close=$100, Volume=1000 (start)
        Day 2: Close=$102, Volume=1500 → Change=+2 → OBV = 0 + 1500 = 1500
        Day 3: Close=$101, Volume=1200 → Change=-1 → OBV = 1500 - 1200 = 300
        Day 4: Close=$103, Volume=1800 → Change=+2 → OBV = 300 + 1800 = 2100
        
        Rising OBV = More volume on up days (bullish)
        Falling OBV = More volume on down days (bearish)
        """
        # Calculate price change (convert to float to avoid Decimal issues)
        price_change = df['close'].astype(float).diff()
        
        # Get sign of price change (+1, 0, -1)
        # Using pandas where() instead of np.sign() to handle types better
        sign = pd.Series(0, index=df.index)
        sign[price_change > 0] = 1
        sign[price_change < 0] = -1
        
        # Convert volume to float to avoid Decimal issues
        volume = df['volume'].astype(float)
        
        # Multiply sign by volume
        # Positive volume when price up, negative when price down
        signed_volume = sign * volume
        
        # Cumulative sum = OBV
        # This accumulates all the signed volume over time
        obv = signed_volume.cumsum()
        
        return obv
    
    def calculate_moving_average(self, series: pd.Series, period: int, ma_type: str) -> pd.Series:
        """
        Calculate moving average of OBV
        
        This matches your Pine Script OBV-MA calculation
        
        Args:
            series: OBV values
            period: MA period (21 in your case)
            ma_type: Type of MA ('EMA', 'SMA', 'RMA', 'WMA', 'VWMA')
        
        Returns:
            Series of OBV-MA values
            
        MA Types:
        - EMA: Fast response (your choice)
        - SMA: Simple average
        - RMA: Wilder's smoothing (slowest)
        - WMA: Weighted (more weight to recent)
        - VWMA: Volume-weighted
        """
        if ma_type == 'SMA':
            # Simple Moving Average
            return series.rolling(window=period, min_periods=period).mean()
        
        elif ma_type == 'RMA':
            # Wilder's Smoothing (RMA)
            alpha = 1.0 / period
            return series.ewm(alpha=alpha, min_periods=period, adjust=False).mean()
        
        elif ma_type == 'WMA':
            # Weighted Moving Average
            weights = np.arange(1, period + 1)
            return series.rolling(window=period).apply(
                lambda x: np.dot(x, weights) / weights.sum(), raw=True
            )
        
        else:  # EMA (default - your choice)
            # Exponential Moving Average
            return series.ewm(span=period, min_periods=period, adjust=False).mean()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate OBV and OBV-MA
        
        This matches your Pine Script OBV calculation exactly
        
        Args:
            df: DataFrame with OHLCV data
                Required columns: close, volume
        
        Returns:
            DataFrame with two new columns added:
            - obv: On-Balance Volume (cumulative volume flow)
            - obv_ma: Moving average of OBV (21-period EMA)
            
        Process:
        1. Calculate OBV (cumulative signed volume)
        2. Calculate OBV-MA (EMA of OBV)
        3. Store both values
        
        Interpretation:
        - OBV > OBV-MA: Bullish (volume flowing in)
        - OBV < OBV-MA: Bearish (volume flowing out)
        - OBV rising: Accumulation phase
        - OBV falling: Distribution phase
        """
        # Validation: Check if we have enough data
        min_candles_needed = self.ma_length + 10
        if df.empty or len(df) < min_candles_needed:
            print(f"  ⚠️  Not enough data for OBV calculation")
            print(f"      Need: {min_candles_needed} candles, Got: {len(df)} candles")
            return df
        
        # Step 1: Calculate OBV (cumulative volume flow)
        # OBV adds volume on up days, subtracts on down days
        # This shows whether smart money is accumulating or distributing
        df['obv'] = self.calculate_obv(df)
        
        # Step 2: Calculate OBV-MA (smoothed OBV trend)
        # This is the signal line for OBV
        # OBV crossing above OBV-MA = Bullish signal
        # OBV crossing below OBV-MA = Bearish signal
        df['obv_ma'] = self.calculate_moving_average(
            df['obv'], 
            self.ma_length, 
            self.ma_type
        )
        
        # Step 3: Round to 2 decimal places (OBV can be large numbers)
        df['obv'] = df['obv'].round(2)
        df['obv_ma'] = df['obv_ma'].round(2)
        
        return df
    
    def get_indicator_columns(self) -> list:
        """
        Return list of column names this calculator produces
        
        These columns will be stored in the 'indicators' table in PostgreSQL
        
        Returns:
            List of column names: ['obv', 'obv_ma']
        """
        return ['obv', 'obv_ma']

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    """
    Test script - runs when you execute: python backend/indicators/obv.py
    
    This will:
    1. Calculate OBV for BTC/USDT and ETH/USDT (1h timeframe)
    2. Store results in 'indicators' table
    3. Show volume flow analysis
    """
    print("=" * 80)
    print("OBV CALCULATOR TEST - Matching TradingView Settings")
    print("=" * 80)
    print("\n⚙️  Your OBV Settings:")
    print(f"   OBV-MA Type: EMA (faster response)")
    print(f"   OBV-MA Length: 21 periods")
    print(f"   (Matches your TradingView dashboard exactly)")
    
    # Initialize calculator with YOUR settings (21, EMA)
    calc = OBVCalculator(ma_length=21, ma_type='EMA')
    
    # Process BTC/USDT
    print("\n" + "─" * 80)
    print("📊 Processing BTC/USDT 1h...")
    stored_btc = calc.run('BTC/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_btc} OBV values for BTC/USDT")
    
    # Process ETH/USDT
    print("\n" + "─" * 80)
    print("📊 Processing ETH/USDT 1h...")
    stored_eth = calc.run('ETH/USDT', '1h', limit=3000)
    print(f"✅ Stored {stored_eth} OBV values for ETH/USDT")
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ OBV CALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\n📊 Summary:")
    print(f"   Total indicators calculated: {stored_btc + stored_eth}")
    print(f"   BTC/USDT: {stored_btc} candles")
    print(f"   ETH/USDT: {stored_eth} candles")
    
    # Interpretation guide
    print("\n📚 How to Read OBV:")
    print("   OBV > OBV-MA: Bullish volume flow (accumulation)")
    print("   OBV < OBV-MA: Bearish volume flow (distribution)")
    print("   OBV rising: Smart money buying")
    print("   OBV falling: Smart money selling")
    print("")
    print("   Divergence Detection:")
    print("   • Price ↑ + OBV ↓ = Bearish divergence (reversal down)")
    print("   • Price ↓ + OBV ↑ = Bullish divergence (reversal up)")
    print("   • Price + OBV both ↑ = Healthy uptrend (confirmed)")
    print("   • Price + OBV both ↓ = Healthy downtrend (confirmed)")
    
    # Next steps
    print("\n💡 Next Steps:")
    print("   1. Open Navicat")
    print("   2. Run this query to see OBV data:")
    print("\n" + "─" * 80)
    print("SELECT c.symbol, c.datetime, c.close,")
    print("       i.obv,")
    print("       i.obv_ma,")
    print("       CASE ")
    print("           WHEN i.obv > i.obv_ma THEN '🟢 Bullish Flow'")
    print("           WHEN i.obv < i.obv_ma THEN '🔴 Bearish Flow'")
    print("           ELSE '⚪ Neutral'")
    print("       END as volume_flow,")
    print("       CASE ")
    print("           WHEN i.obv > LAG(i.obv, 5) OVER (ORDER BY c.datetime)")
    print("               THEN '📈 Accumulation'")
    print("           WHEN i.obv < LAG(i.obv, 5) OVER (ORDER BY c.datetime)")
    print("               THEN '📉 Distribution'")
    print("           ELSE '➡️ Neutral'")
    print("       END as obv_trend")
    print("FROM candles c JOIN indicators i ON c.id = i.candle_id")
    print("WHERE c.symbol = 'BTC/USDT' AND c.timeframe = '1h'")
    print("ORDER BY c.datetime DESC LIMIT 20;")
    print("─" * 80)