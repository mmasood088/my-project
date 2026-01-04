"""
Base Calculator Class
All indicator calculators inherit from this
"""

import pandas as pd
import numpy as np
from sqlalchemy import text
from typing import List, Dict, Any
import sys
import os

# Add parent directory to path to import database module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

class BaseCalculator:
    """
    Base class for all indicator calculators
    
    Provides common functionality:
    - Fetching candles from database
    - Storing indicator values
    - Error handling
    """
    
    def __init__(self, indicator_name: str):
        """
        Initialize calculator
        
        Args:
            indicator_name: Name of the indicator (e.g., 'RSI', 'MACD')
        """
        self.indicator_name = indicator_name
        self.engine = engine
    
    def fetch_candles(self, symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
        """
        Fetch candles from database for calculation
        Also fetches existing indicator values (like ATR for SuperTrend)
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
            limit: Number of candles to fetch
        
        Returns:
            DataFrame with OHLCV data and existing indicator values
        """
        try:
            with engine.connect() as connection:
                # Fetch candles WITH existing indicator values (LEFT JOIN)
                # This allows SuperTrend to access ATR, and other indicators
                # to build on previous calculations
                query = text("""
                    SELECT 
                        c.id,
                        c.symbol,
                        c.timeframe,
                        c.timestamp,
                        c.datetime,
                        c.open,
                        c.high,
                        c.low,
                        c.close,
                        c.volume,
                        i.rsi,
                        i.rsi_ema,
                        i.macd_line,
                        i.macd_signal,
                        i.macd_histogram,
                        i.adx,
                        i.di_plus,
                        i.di_minus,
                        i.obv,
                        i.obv_ma,
                        i.ema_44,
                        i.ema_100,
                        i.ema_200,
                        i.bb_basis,
                        i.bb_upper_1,
                        i.bb_lower_1,
                        i.bb_upper_2,
                        i.bb_lower_2,
                        i.bb_upper_3,
                        i.bb_lower_3,
                        i.bb_squeeze,
                        i.bb_position,
                        i.vwap,
                        i.atr,
                        i.volume_avg,
                        i.volume_signal,
                        i.supertrend_1,
                        i.supertrend_2
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.symbol = :symbol 
                      AND c.timeframe = :timeframe
                    ORDER BY c.datetime ASC
                    LIMIT :limit
                """)
                
                result = connection.execute(
                    query, 
                    {'symbol': symbol, 'timeframe': timeframe, 'limit': limit}
                )
                
                # Convert to DataFrame
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                
                if df.empty:
                    print(f"  ⚠️  No candles found for {symbol} {timeframe}")
                    return df
                
                return df
                
        except Exception as e:
            print(f"  ✗ Error fetching candles: {e}")
            return pd.DataFrame()
    
    def calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate indicator values
        Must be implemented by child classes
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with indicator values added
        """
        raise NotImplementedError("Child class must implement calculate() method")
    
    def store_indicators(self, df: pd.DataFrame, indicator_columns: List[str]) -> int:
        """
        Store calculated indicator values in database
        
        Args:
            df: DataFrame with calculated indicators
            indicator_columns: List of column names to store
        
        Returns:
            Number of rows inserted/updated
        """
        if df is None or len(df) == 0:
            print(f"✗ No data to store for {self.indicator_name}")
            return 0
        
        try:
            stored_count = 0
            
            with self.engine.connect() as connection:
                for idx, row in df.iterrows():
                    try:
                        # Build dynamic column list for indicators
                        columns = ['candle_id'] + indicator_columns
                        placeholders = ', '.join([f':{col}' for col in columns])
                        update_set = ', '.join([f'{col} = EXCLUDED.{col}' for col in indicator_columns])
                        
                        # Prepare values dictionary with proper type conversion
                        candle_id = int(row['id'])
                        values = {'candle_id': candle_id}
                        
                        for col in indicator_columns:
                            if col in row and pd.notna(row[col]):
                                # Handle different data types appropriately
                                if isinstance(row[col], (bool, np.bool_)):
                                    # Boolean columns (like bb_squeeze)
                                    values[col] = bool(row[col])
                                elif isinstance(row[col], str):
                                    # String columns (like bb_position, volume_signal)
                                    # Don't convert None string to actual None
                                    if row[col] == 'None' or row[col] == 'none':
                                        values[col] = None
                                    else:
                                        values[col] = str(row[col])
                                else:
                                    # Numeric columns (floats, decimals)
                                    values[col] = float(row[col])
                            else:
                                values[col] = None
                        
                        # DEBUG: Print SuperTrend values being stored (first 3 only)
                        if 'supertrend_1' in indicator_columns and stored_count < 3:
                            print(f"  🔍 DEBUG - Row {idx} - Candle ID {candle_id}:")
                            print(f"     supertrend_1 in row: {'supertrend_1' in row}")
                            print(f"     supertrend_1 value: {row.get('supertrend_1', 'NOT FOUND')}")
                            print(f"     supertrend_1 in values dict: {values.get('supertrend_1', 'NOT SET')}")
                            print(f"     supertrend_2 in values dict: {values.get('supertrend_2', 'NOT SET')}")
                            print(f"     All indicator columns: {indicator_columns}")
                        
                        # Build query
                        query = text(f"""
                            INSERT INTO indicators ({', '.join(columns)})
                            VALUES ({placeholders})
                            ON CONFLICT (candle_id)
                            DO UPDATE SET {update_set}
                        """)
                        
                        connection.execute(query, values)
                        stored_count += 1
                    
                    except Exception as e:
                        print(f"  ✗ Error storing indicator for candle {row.get('id', 'unknown')}: {e}")
                        # Print more details about the error
                        if 'supertrend' in str(e).lower():
                            print(f"     Candle ID: {row.get('id')}")
                            print(f"     Indicator columns: {indicator_columns}")
                            print(f"     Values dict keys: {list(values.keys())}")
                
                connection.commit()
            
            return stored_count
        
        except Exception as e:
            print(f"✗ Database error storing {self.indicator_name}: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def run(self, symbol: str, timeframe: str, limit: int = 500) -> int:
        """
        Complete workflow: fetch → calculate → store
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            limit: Number of candles
        
        Returns:
            Number of indicators stored
        """
        print(f"\n🔧 Calculating {self.indicator_name} for {symbol} {timeframe}...")
        
        # Fetch candles
        df = self.fetch_candles(symbol, timeframe, limit)
        
        if df.empty:
            print(f"✗ No candles found for {symbol} {timeframe}")
            return 0
        
        print(f"  📊 Fetched {len(df)} candles")
        
        # Calculate indicators
        df = self.calculate(df)
        
        if df.empty:
            print(f"✗ Calculation failed for {self.indicator_name}")
            return 0
        
        print(f"  ✓ Calculated {self.indicator_name}")
        
        # Store in database
        indicator_cols = self.get_indicator_columns()
        stored = self.store_indicators(df, indicator_cols)
        
        print(f"  ✓ Stored {stored} {self.indicator_name} values")
        
        return stored
    
    def get_indicator_columns(self) -> List[str]:
        """
        Return list of column names for this indicator
        Must be implemented by child classes
        """
        raise NotImplementedError("Child class must implement get_indicator_columns() method")