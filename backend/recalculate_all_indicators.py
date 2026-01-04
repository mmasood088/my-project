"""
Recalculate ALL Indicators - Complete Rebuild
Purpose: Recalculate all 11 indicators in correct order with dependencies

This script ensures:
1. All indicators are calculated in proper order
2. Dependencies are available (e.g., ATR before SuperTrend)
3. All values are stored correctly in database

Run this whenever you need to rebuild all indicator data.
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators.rsi import RSICalculator
from indicators.macd import MACDCalculator
from indicators.ema import EMACalculator
from indicators.bollinger_bands import BollingerBandsCalculator
from indicators.adx import ADXCalculator
from indicators.volume import VolumeAnalyzer
from indicators.atr import ATRCalculator
from indicators.obv import OBVCalculator
from indicators.vwap import VWAPCalculator
from indicators.supertrend import SuperTrendCalculator

def recalculate_all(symbols=['BTC/USDT', 'ETH/USDT'], timeframes=['1h']):
    """
    Recalculate all indicators for given symbols and timeframes
    
    Args:
        symbols: List of trading pairs
        timeframes: List of timeframes
    """
    print("=" * 80)
    print("RECALCULATING ALL INDICATORS")
    print("=" * 80)
    print(f"\nSymbols: {', '.join(symbols)}")
    print(f"Timeframes: {', '.join(timeframes)}")
    
    # Initialize all calculators with YOUR exact settings
    calculators = [
        ('RSI', RSICalculator(rsi_length=14, rsi_ema_length=21)),
        ('MACD', MACDCalculator(fast=9, slow=21, signal=5, ma_type='EMA', signal_type='EMA')),
        ('EMA', EMACalculator(ema_44=44, ema_100=100, ema_200=200)),
        ('Bollinger Bands', BollingerBandsCalculator(length=20, mult_1=1.0, mult_2=2.0, mult_3=3.0, squeeze_threshold=4.0)),
        ('ADX', ADXCalculator(di_length=14, adx_smoothing=14)),
        ('Volume', VolumeAnalyzer(avg_length=20, high_threshold=1.5, low_threshold=0.5)),
        ('ATR', ATRCalculator(length=14)),  # CRITICAL: Must run before SuperTrend
        ('OBV', OBVCalculator(ma_length=21, ma_type='EMA')),
        ('VWAP', VWAPCalculator(neutral_zone=0.5)),
        ('SuperTrend', SuperTrendCalculator(st1_atr=5, st1_factor=1.0, st2_atr=8, st2_factor=2.0)),  # MUST be last
    ]
    
    total_indicators_calculated = 0
    
    for symbol in symbols:
        for timeframe in timeframes:
            print("\n" + "=" * 80)
            print(f"PROCESSING: {symbol} {timeframe}")
            print("=" * 80)
            
            for name, calc in calculators:
                print(f"\n{name}...", end=' ')
                try:
                    stored = calc.run(symbol, timeframe, limit=3000)
                    print(f"✓ {stored} values")
                    total_indicators_calculated += stored
                except Exception as e:
                    print(f"✗ Error: {e}")
    
    print("\n" + "=" * 80)
    print("✅ RECALCULATION COMPLETE!")
    print("=" * 80)
    print(f"\nTotal indicators calculated: {total_indicators_calculated:,}")
    
    print("\n💡 Verification:")
    print("   Open Navicat and run:")
    print("\n   SELECT COUNT(*) FROM indicators WHERE supertrend_1 IS NOT NULL;")
    print("\n   You should see a count > 0")

if __name__ == "__main__":
    # Recalculate for BTC and ETH on 1h timeframe
    recalculate_all(symbols=['BTC/USDT', 'ETH/USDT'], timeframes=['1h'])