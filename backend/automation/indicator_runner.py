"""
Indicator Runner
Automatically calculate indicators for new candles
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import text
from typing import List, Dict, Optional
import pandas as pd

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

# Import all individual indicator calculators
from indicators import (
    RSICalculator,
    MACDCalculator,
    EMACalculator,
    BollingerBandsCalculator,
    ADXCalculator,
    VolumeAnalyzer,
    ATRCalculator,
    OBVCalculator,
    VWAPCalculator,
    SuperTrendCalculator
)


class IndicatorRunner:
    """
    Calculate and store technical indicators for candles
    """
    
    def __init__(self):
        self.engine = engine
        # Initialize all indicator calculators
        self.calculators = {
            'rsi': RSICalculator(),
            'macd': MACDCalculator(),
            'ema': EMACalculator(),
            'bb': BollingerBandsCalculator(),
            'adx': ADXCalculator(),
            'volume': VolumeAnalyzer(),
            'atr': ATRCalculator(),
            'obv': OBVCalculator(),
            'vwap': VWAPCalculator(),
            'supertrend': SuperTrendCalculator()
        }
        print("✓ Indicator Runner initialized with 10 calculators")
    
    def get_candles_without_indicators(self, symbol: str, timeframe: str, 
                                      limit: int = 100) -> List[Dict]:
        """
        Find candles that don't have indicators calculated yet
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
            limit: Maximum candles to return
        
        Returns:
            List of candle dicts that need indicators
        """
        try:
            with self.engine.connect() as conn:
                # Find candles without indicators
                query = text("""
                    SELECT c.id, c.symbol, c.timeframe, c.datetime,
                           c.open, c.high, c.low, c.close, c.volume
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.symbol = :symbol
                      AND c.timeframe = :timeframe
                      AND i.id IS NULL
                    ORDER BY c.datetime ASC
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'limit': limit
                }).fetchall()
                
                candles = []
                for row in result:
                    candles.append({
                        'id': row[0],
                        'symbol': row[1],
                        'timeframe': row[2],
                        'datetime': row[3],
                        'open': float(row[4]),
                        'high': float(row[5]),
                        'low': float(row[6]),
                        'close': float(row[7]),
                        'volume': float(row[8])
                    })
                
                return candles
        
        except Exception as e:
            print(f"  ✗ Error finding candles without indicators: {e}")
            return []
    
    def get_historical_candles(self, symbol: str, timeframe: str, 
                              before_datetime: datetime, limit: int = 250) -> pd.DataFrame:
        """
        Get historical candles needed for indicator calculation
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            before_datetime: Get candles before this datetime
            limit: Number of historical candles
        
        Returns:
            DataFrame with OHLCV data
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT datetime, open, high, low, close, volume
                    FROM candles
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                      AND datetime < :before_datetime
                    ORDER BY datetime DESC
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'before_datetime': before_datetime,
                    'limit': limit
                }).fetchall()
                
                if not result:
                    return pd.DataFrame()
                
                # Convert to DataFrame
                df = pd.DataFrame(result, columns=['datetime', 'open', 'high', 'low', 'close', 'volume'])
                
                # Sort chronologically (oldest first)
                df = df.sort_values('datetime').reset_index(drop=True)
                
                # Convert to float
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                return df
        
        except Exception as e:
            print(f"  ✗ Error getting historical candles: {e}")
            return pd.DataFrame()
    
    def calculate_indicators_for_candle(self, candle: Dict, 
                                   historical_df: pd.DataFrame) -> Optional[Dict]:
        """
        Calculate all indicators for a single candle
        
        Args:
            candle: Candle dict with OHLCV data
            historical_df: Historical candles DataFrame
        
        Returns:
            Dict with all indicator values, or None if failed
        """
        try:
            # Append current candle to historical data
            current_row = pd.DataFrame([{
                'datetime': candle['datetime'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume']
            }])
            
            df = pd.concat([historical_df, current_row], ignore_index=True)
            
            if len(df) < 250:
                print(f"    ⚠️  Only {len(df)} historical candles, need 250+ for accurate indicators")
                return None
            
            # Calculate all indicators using individual calculators
            results = {}
            
            # RSI
            rsi_df = self.calculators['rsi'].calculate(df)
            if not rsi_df.empty and 'rsi' in rsi_df.columns:
                results['rsi'] = float(rsi_df['rsi'].iloc[-1])
                results['rsi_ema'] = float(rsi_df['rsi_ema'].iloc[-1]) if 'rsi_ema' in rsi_df.columns else None
            else:
                results['rsi'] = results['rsi_ema'] = None
            
            # MACD
            macd_df = self.calculators['macd'].calculate(df)
            if not macd_df.empty and 'macd_line' in macd_df.columns:
                results['macd_line'] = float(macd_df['macd_line'].iloc[-1])
                results['macd_signal'] = float(macd_df['macd_signal'].iloc[-1])
                results['macd_histogram'] = float(macd_df['macd_histogram'].iloc[-1])
            else:
                results['macd_line'] = results['macd_signal'] = results['macd_histogram'] = None
            
            # EMA Stack
            ema_df = self.calculators['ema'].calculate(df)
            if not ema_df.empty and 'ema_44' in ema_df.columns:
                results['ema_44'] = float(ema_df['ema_44'].iloc[-1])
                results['ema_100'] = float(ema_df['ema_100'].iloc[-1])
                results['ema_200'] = float(ema_df['ema_200'].iloc[-1])
            else:
                results['ema_44'] = results['ema_100'] = results['ema_200'] = None
            
            # Bollinger Bands
            bb_df = self.calculators['bb'].calculate(df)
            if not bb_df.empty and 'bb_basis' in bb_df.columns:
                results['bb_basis'] = float(bb_df['bb_basis'].iloc[-1])
                results['bb_upper_1'] = float(bb_df['bb_upper_1'].iloc[-1])
                results['bb_lower_1'] = float(bb_df['bb_lower_1'].iloc[-1])
                results['bb_upper_2'] = float(bb_df['bb_upper_2'].iloc[-1])
                results['bb_lower_2'] = float(bb_df['bb_lower_2'].iloc[-1])
                results['bb_upper_3'] = float(bb_df['bb_upper_3'].iloc[-1]) if 'bb_upper_3' in bb_df.columns else None
                results['bb_lower_3'] = float(bb_df['bb_lower_3'].iloc[-1]) if 'bb_lower_3' in bb_df.columns else None
                
                # Calculate BB squeeze and position (not provided by calculator)
                bb_width = (results['bb_upper_1'] - results['bb_lower_1']) / results['bb_basis'] * 100
                results['bb_squeeze'] = True if bb_width < 2.0 else False  # Boolean for database
                
                # BB position: where price is relative to bands
                close_price = candle['close']
                if close_price > results['bb_upper_1']:
                    results['bb_position'] = 1  # Above upper band
                elif close_price < results['bb_lower_1']:
                    results['bb_position'] = -1  # Below lower band
                else:
                    results['bb_position'] = 0  # Between bands
            else:
                results['bb_basis'] = results['bb_upper_1'] = results['bb_lower_1'] = None
                results['bb_upper_2'] = results['bb_lower_2'] = None
                results['bb_upper_3'] = results['bb_lower_3'] = None
                results['bb_squeeze'] = results['bb_position'] = None
            
            # ADX
            adx_df = self.calculators['adx'].calculate(df)
            if not adx_df.empty and 'adx' in adx_df.columns:
                results['adx'] = float(adx_df['adx'].iloc[-1])
                results['di_plus'] = float(adx_df['di_plus'].iloc[-1])
                results['di_minus'] = float(adx_df['di_minus'].iloc[-1])
            else:
                results['adx'] = results['di_plus'] = results['di_minus'] = None
            
            # ATR (needed for SuperTrend)
            atr_df = self.calculators['atr'].calculate(df)
            if not atr_df.empty and 'atr' in atr_df.columns:
                results['atr'] = float(atr_df['atr'].iloc[-1])
                # Add ATR to df for SuperTrend calculation
                df['atr'] = atr_df['atr']
            else:
                results['atr'] = None
            
            # Volume Analysis
            vol_df = self.calculators['volume'].calculate(df)
            if not vol_df.empty and 'volume_avg' in vol_df.columns and 'volume_signal' in vol_df.columns:
                results['volume_avg'] = float(vol_df['volume_avg'].iloc[-1])
                # Volume signal: H/N/L (matches TradingView exactly)
                results['volume_signal'] = str(vol_df['volume_signal'].iloc[-1])
            else:
                results['volume_avg'] = results['volume_signal'] = None
            
            # OBV
            obv_df = self.calculators['obv'].calculate(df)
            if not obv_df.empty and 'obv' in obv_df.columns:
                results['obv'] = float(obv_df['obv'].iloc[-1])
                results['obv_ma'] = float(obv_df['obv_ma'].iloc[-1]) if 'obv_ma' in obv_df.columns else None
            else:
                results['obv'] = results['obv_ma'] = None
            
            # VWAP
            vwap_df = self.calculators['vwap'].calculate(df)
            if not vwap_df.empty and 'vwap' in vwap_df.columns:
                results['vwap'] = float(vwap_df['vwap'].iloc[-1])
            else:
                results['vwap'] = None
            
            # SuperTrend (requires ATR to be already calculated)
            if results['atr'] is not None:
                st_df = self.calculators['supertrend'].calculate(df)
                if not st_df.empty and 'supertrend_1' in st_df.columns:
                    results['supertrend_1'] = float(st_df['supertrend_1'].iloc[-1])
                    results['supertrend_2'] = float(st_df['supertrend_2'].iloc[-1])
                    
                    # Calculate direction: 1 if price > supertrend (uptrend), -1 if below (downtrend)
                    close_price = candle['close']
                    results['supertrend_1_direction'] = 1 if close_price > results['supertrend_1'] else -1
                    results['supertrend_2_direction'] = 1 if close_price > results['supertrend_2'] else -1
                else:
                    results['supertrend_1'] = results['supertrend_1_direction'] = None
                    results['supertrend_2'] = results['supertrend_2_direction'] = None
            else:
                results['supertrend_1'] = results['supertrend_1_direction'] = None
                results['supertrend_2'] = results['supertrend_2_direction'] = None
            
            return results
        
        except Exception as e:
            print(f"  ✗ Error calculating indicators: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def store_indicators(self, candle_id: int, indicators: Dict) -> bool:
        """
        Store calculated indicators in database
        
        Args:
            candle_id: ID of the candle
            indicators: Dict of indicator values
        
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.engine.connect() as conn:
                # Check if indicators already exist
                check_query = text("""
                    SELECT id FROM indicators WHERE candle_id = :candle_id
                """)
                
                existing = conn.execute(check_query, {'candle_id': candle_id}).fetchone()
                
                if existing:
                    # Update existing
                    update_query = text("""
                        UPDATE indicators SET
                            rsi = :rsi,
                            rsi_ema = :rsi_ema,
                            macd_line = :macd_line,
                            macd_signal = :macd_signal,
                            macd_histogram = :macd_histogram,
                            ema_44 = :ema_44,
                            ema_100 = :ema_100,
                            ema_200 = :ema_200,
                            bb_basis = :bb_basis,
                            bb_upper_1 = :bb_upper_1,
                            bb_lower_1 = :bb_lower_1,
                            bb_upper_2 = :bb_upper_2,
                            bb_lower_2 = :bb_lower_2,
                            bb_upper_3 = :bb_upper_3,
                            bb_lower_3 = :bb_lower_3,
                            bb_squeeze = :bb_squeeze,
                            bb_position = :bb_position,
                            adx = :adx,
                            di_plus = :di_plus,
                            di_minus = :di_minus,
                            atr = :atr,
                            obv = :obv,
                            obv_ma = :obv_ma,
                            vwap = :vwap,
                            volume_avg = :volume_avg,
                            volume_signal = :volume_signal,
                            supertrend_1 = :supertrend_1,
                            supertrend_1_direction = :supertrend_1_direction,
                            supertrend_2 = :supertrend_2,
                            supertrend_2_direction = :supertrend_2_direction,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE candle_id = :candle_id
                    """)
                    
                    conn.execute(update_query, {
                        'candle_id': candle_id,
                        **indicators
                    })
                else:
                    # Insert new
                    insert_query = text("""
                        INSERT INTO indicators (
                            candle_id,
                            rsi, rsi_ema,
                            macd_line, macd_signal, macd_histogram,
                            ema_44, ema_100, ema_200,
                            bb_basis, bb_upper_1, bb_lower_1, bb_upper_2, bb_lower_2,
                            bb_upper_3, bb_lower_3, bb_squeeze, bb_position,
                            adx, di_plus, di_minus,
                            atr, obv, obv_ma, vwap,
                            volume_avg, volume_signal,
                            supertrend_1, supertrend_1_direction,
                            supertrend_2, supertrend_2_direction
                        ) VALUES (
                            :candle_id,
                            :rsi, :rsi_ema,
                            :macd_line, :macd_signal, :macd_histogram,
                            :ema_44, :ema_100, :ema_200,
                            :bb_basis, :bb_upper_1, :bb_lower_1, :bb_upper_2, :bb_lower_2,
                            :bb_upper_3, :bb_lower_3, :bb_squeeze, :bb_position,
                            :adx, :di_plus, :di_minus,
                            :atr, :obv, :obv_ma, :vwap,
                            :volume_avg, :volume_signal,
                            :supertrend_1, :supertrend_1_direction,
                            :supertrend_2, :supertrend_2_direction
                        )
                    """)
                    
                    conn.execute(insert_query, {
                        'candle_id': candle_id,
                        **indicators
                    })
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"  ✗ Error storing indicators: {e}")
            import traceback
            traceback.print_exc()
            return False


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("INDICATOR RUNNER TEST")
    print("=" * 80)
    
    runner = IndicatorRunner()
    
    # Test finding candles without indicators
    print("\nTest 1: Find candles without indicators")
    print("-" * 80)
    
    candles = runner.get_candles_without_indicators('BTC/USDT', '1h', limit=5)
    print(f"Found {len(candles)} candles without indicators\n")
    
    if not candles:
        print("  ✓ All candles have indicators!")
    else:
        # Test calculating indicators for first candle
        print("\nTest 2: Calculate indicators for first candle")
        print("-" * 80)
        
        test_candle = candles[0]
        print(f"Processing Candle #{test_candle['id']}: {test_candle['datetime']}")
        
        # Get historical data
        historical_df = runner.get_historical_candles(
            test_candle['symbol'],
            test_candle['timeframe'],
            test_candle['datetime'],
            limit=250
        )
        
        print(f"  → Loaded {len(historical_df)} historical candles")
        
        if len(historical_df) >= 250:
            # Calculate indicators
            indicators = runner.calculate_indicators_for_candle(test_candle, historical_df)
            
            if indicators:
                print(f"  ✓ Calculated indicators:")
                print(f"    RSI: {indicators.get('rsi', 'N/A')}")
                print(f"    MACD Line: {indicators.get('macd_line', 'N/A')}")
                print(f"    MACD Signal: {indicators.get('macd_signal', 'N/A')}")
                print(f"    EMA 44: {indicators.get('ema_44', 'N/A')}")
                print(f"    EMA 100: {indicators.get('ema_100', 'N/A')}")
                print(f"    BB Upper 1: {indicators.get('bb_upper_1', 'N/A')}")
                print(f"    BB Basis: {indicators.get('bb_basis', 'N/A')}")
                print(f"    ADX: {indicators.get('adx', 'N/A')}")
                print(f"    ATR: {indicators.get('atr', 'N/A')}")
                print(f"    SuperTrend 1: {indicators.get('supertrend_1', 'N/A')}")
                print(f"    SuperTrend 2: {indicators.get('supertrend_2', 'N/A')}")
                
                # Test storing indicators
                print("\nTest 3: Store indicators in database")
                print("-" * 80)
                
                success = runner.store_indicators(test_candle['id'], indicators)
                
                if success:
                    print(f"  ✓ Successfully stored indicators for Candle #{test_candle['id']}")
                else:
                    print(f"  ✗ Failed to store indicators")
            else:
                print("  ✗ Failed to calculate indicators")
        else:
            print(f"  ⚠️  Not enough historical data ({len(historical_df)} candles)")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


