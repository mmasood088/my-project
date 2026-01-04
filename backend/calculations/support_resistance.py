"""
Support/Resistance Calculator
Matches TradingView Auto S/R Logic

Auto S/R Calculation:
- Support = Lowest low of previous 30 days
- Resistance = Highest high of previous 30 days

Manual Override:
- If manual_support > 0, use manual value
- If manual_support = 0, use auto-calculated value
"""

import pandas as pd
from sqlalchemy import text
from typing import Dict, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

class SupportResistanceCalculator:
    """
    Calculate and manage Support/Resistance levels
    
    Features:
    - Auto-calculate from previous 30-day high/low
    - Manual override support
    - Store in database
    """
    
    def __init__(self):
        self.engine = engine
    
    def calculate_auto_sr(self, symbol: str, timeframe: str = '1d', lookback: int = 30) -> Dict[str, float]:
        """
        Calculate auto S/R from previous month high/low
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe for calculation (default '1d' for daily)
            lookback: Number of periods to look back (default 30)
        
        Returns:
            {'support': float, 'resistance': float}
        """
        try:
            with self.engine.connect() as conn:
                # First, check what timeframes exist for this symbol
                check_query = text("""
                    SELECT DISTINCT timeframe
                    FROM candles
                    WHERE symbol = :symbol
                    ORDER BY timeframe
                """)
                
                available_tfs = conn.execute(check_query, {'symbol': symbol}).fetchall()
                available_tfs_list = [row[0] for row in available_tfs]
                
                # Use daily data if available, otherwise use 1h
                calc_timeframe = '1d' if '1d' in available_tfs_list else '1h'
                
                # Adjust lookback based on timeframe
                if calc_timeframe == '1h':
                    lookback = 30 * 24  # 30 days worth of 1h candles
                elif calc_timeframe == '15m':
                    lookback = 30 * 24 * 4  # 30 days worth of 15m candles
                else:  # 1d
                    lookback = 30  # 30 days
                
                # Fetch last N candles
                query = text("""
                    SELECT high, low
                    FROM candles
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                    ORDER BY datetime DESC
                    LIMIT :lookback
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': calc_timeframe,
                    'lookback': lookback
                })
                
                df = pd.DataFrame(result.fetchall(), columns=['high', 'low'])
                
                if df.empty:
                    print(f"  ⚠️  No candles found for {symbol} {calc_timeframe}")
                    return {'support': 0.0, 'resistance': 0.0}
                
                # Convert to float
                df['high'] = pd.to_numeric(df['high'], errors='coerce')
                df['low'] = pd.to_numeric(df['low'], errors='coerce')
                
                # Calculate
                resistance = float(df['high'].max())
                support = float(df['low'].min())
                
                print(f"  📊 Auto S/R calculated from {len(df)} {calc_timeframe} candles")
                
                return {
                    'support': support,
                    'resistance': resistance
                }
        
        except Exception as e:
            print(f"  ✗ Error calculating auto S/R for {symbol}: {e}")
            import traceback
            traceback.print_exc()
            return {'support': 0.0, 'resistance': 0.0}
    
    def get_manual_sr(self, symbol: str, timeframe: str) -> Dict[str, float]:
        """
        Get manual S/R levels from database
        
        Returns:
            {'support': float, 'resistance': float}
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT manual_support, manual_resistance
                    FROM support_resistance
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()
                
                if result:
                    return {
                        'support': float(result[0]) if result[0] else 0.0,
                        'resistance': float(result[1]) if result[1] else 0.0
                    }
                else:
                    return {'support': 0.0, 'resistance': 0.0}
        
        except Exception as e:
            print(f"Error getting manual S/R for {symbol}: {e}")
            return {'support': 0.0, 'resistance': 0.0}
    
    def get_effective_sr(self, symbol: str, timeframe: str, auto_sr_mode: str = 'Enabled') -> Dict[str, float]:
        """
        Get effective S/R levels (manual if set, else auto)
        
        Logic from Pine Script:
        - If manual = 0 and auto_sr_mode = Enabled → Use auto
        - If manual > 0 → Use manual
        
        Returns:
            {'support': float, 'resistance': float}
        """
        # Get manual levels
        manual = self.get_manual_sr(symbol, timeframe)
        
        # Get auto levels
        auto = self.calculate_auto_sr(symbol, timeframe='1d', lookback=30)
        
        # Determine effective levels
        effective_support = manual['support'] if manual['support'] > 0 else (auto['support'] if auto_sr_mode == 'Enabled' else 0.0)
        effective_resistance = manual['resistance'] if manual['resistance'] > 0 else (auto['resistance'] if auto_sr_mode == 'Enabled' else 0.0)
        
        return {
            'support': effective_support,
            'resistance': effective_resistance
        }
    
    def update_sr(self, symbol: str, timeframe: str, 
                  manual_support: Optional[float] = None,
                  manual_resistance: Optional[float] = None,
                  auto_sr_mode: str = 'Enabled'):
        """
        Update S/R levels in database
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            manual_support: Manual support level (None = don't update)
            manual_resistance: Manual resistance level (None = don't update)
            auto_sr_mode: Auto S/R mode ('Enabled' or 'Disabled')
        """
        try:
            # Calculate auto levels
            auto = self.calculate_auto_sr(symbol, timeframe='1d', lookback=30)
            
            # Get current manual levels if not provided
            if manual_support is None or manual_resistance is None:
                current_manual = self.get_manual_sr(symbol, timeframe)
                if manual_support is None:
                    manual_support = current_manual['support']
                if manual_resistance is None:
                    manual_resistance = current_manual['resistance']
            
            # Calculate effective levels
            effective_support = manual_support if manual_support > 0 else (auto['support'] if auto_sr_mode == 'Enabled' else 0.0)
            effective_resistance = manual_resistance if manual_resistance > 0 else (auto['resistance'] if auto_sr_mode == 'Enabled' else 0.0)
            
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO support_resistance 
                        (symbol, timeframe, manual_support, manual_resistance, 
                         auto_support, auto_resistance, effective_support, effective_resistance,
                         auto_sr_enabled, updated_at)
                    VALUES 
                        (:symbol, :timeframe, :manual_support, :manual_resistance,
                         :auto_support, :auto_resistance, :effective_support, :effective_resistance,
                         :auto_sr_enabled, CURRENT_TIMESTAMP)
                    ON CONFLICT (symbol, timeframe)
                    DO UPDATE SET
                        manual_support = EXCLUDED.manual_support,
                        manual_resistance = EXCLUDED.manual_resistance,
                        auto_support = EXCLUDED.auto_support,
                        auto_resistance = EXCLUDED.auto_resistance,
                        effective_support = EXCLUDED.effective_support,
                        effective_resistance = EXCLUDED.effective_resistance,
                        auto_sr_enabled = EXCLUDED.auto_sr_enabled,
                        updated_at = CURRENT_TIMESTAMP
                """)
                
                conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'manual_support': manual_support,
                    'manual_resistance': manual_resistance,
                    'auto_support': auto['support'],
                    'auto_resistance': auto['resistance'],
                    'effective_support': effective_support,
                    'effective_resistance': effective_resistance,
                    'auto_sr_enabled': auto_sr_mode == 'Enabled'
                })
                
                conn.commit()
                
                print(f"✓ Updated S/R for {symbol} {timeframe}")
                print(f"  Manual: S={manual_support:.2f}, R={manual_resistance:.2f}")
                print(f"  Auto: S={auto['support']:.2f}, R={auto['resistance']:.2f}")
                print(f"  Effective: S={effective_support:.2f}, R={effective_resistance:.2f}")
        
        except Exception as e:
            print(f"✗ Error updating S/R: {e}")

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("SUPPORT/RESISTANCE CALCULATOR TEST")
    print("=" * 80)
    
    calc = SupportResistanceCalculator()
    
    # Test for BTC/USDT and ETH/USDT
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['15m', '1h', '1d']
    
    for symbol in symbols:
        print(f"\n{'─' * 80}")
        print(f"📊 Processing {symbol}")
        print('─' * 80)
        
        for tf in timeframes:
            print(f"\n  Timeframe: {tf}")
            
            # Calculate and store S/R
            calc.update_sr(symbol, tf, manual_support=0, manual_resistance=0, auto_sr_mode='Enabled')
    
    print("\n" + "=" * 80)
    print("✅ S/R CALCULATION COMPLETE!")
    print("=" * 80)
    print("\n💡 Verify in Navicat:")
    print("   SELECT * FROM support_resistance ORDER BY symbol, timeframe;")