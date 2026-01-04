"""
Signal Runner
Automatically generate signals for candles with indicators
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text
from typing import List, Dict, Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from calculations.signal_generator import SignalGenerator


class SignalRunner:
    """
    Generate and store trading signals for candles
    """
    
    def __init__(self):
        self.engine = engine
        self.signal_generator = SignalGenerator()
        print("✓ Signal Runner initialized")
    
    def get_candles_without_signals(self, symbol: str, timeframe: str, 
                                    limit: int = 100) -> List[Dict]:
        """
        Find candles that have indicators but no signals
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h')
            limit: Maximum candles to return
        
        Returns:
            List of candle dicts that need signals
        """
        try:
            with self.engine.connect() as conn:
                # Find candles with indicators but without signals
                query = text("""
                    SELECT c.id, c.symbol, c.timeframe, c.datetime
                    FROM candles c
                    INNER JOIN indicators i ON c.id = i.candle_id
                    LEFT JOIN signals s ON c.id = s.candle_id
                    WHERE c.symbol = :symbol
                      AND c.timeframe = :timeframe
                      AND i.rsi IS NOT NULL
                      AND s.id IS NULL
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
                        'datetime': row[3]
                    })
                
                return candles
        
        except Exception as e:
            print(f"  ✗ Error finding candles without signals: {e}")
            return []
    
    def generate_signal_for_candle(self, candle: Dict) -> Optional[Dict]:
        """
        Generate signal for a specific candle
        ...
        """
        try:
            # Use the signal generator to create signal for THIS specific candle
            signal_data = self.signal_generator.generate_signal(
                candle['symbol'],
                candle['timeframe'],
                candle_id=candle['id']  # Pass the specific candle ID
            )
            
            return signal_data
        
        except Exception as e:
            print(f"  ✗ Error generating signal for candle {candle['id']}: {e}")
            return None
    
    def store_signal(self, signal_data: Dict) -> bool:
        """
        Store signal in database
        
        Args:
            signal_data: Dict with signal information
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use the signal generator's store method
            self.signal_generator.store_signal(signal_data)
            return True
        
        except Exception as e:
            print(f"  ✗ Error storing signal: {e}")
            return False
    
    def process_symbol_timeframe(self, symbol: str, timeframe: str) -> int:
        """
        Process all pending signals for a symbol/timeframe
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
        
        Returns:
            Number of signals generated
        """
        # Find candles needing signals
        candles = self.get_candles_without_signals(symbol, timeframe, limit=100)
        
        if not candles:
            return 0
        
        print(f"  → Processing {len(candles)} candles...")
        
        generated_count = 0
        for candle in candles:
            signal_data = self.generate_signal_for_candle(candle)
            
            if signal_data:
                if self.store_signal(signal_data):
                    generated_count += 1
        
        return generated_count
    
    def run_for_all_symbols(self, symbols: List[str], timeframes: List[str]):
        """
        Generate signals for all symbols and timeframes
        
        Args:
            symbols: List of trading pairs
            timeframes: List of timeframes
        """
        print("=" * 80)
        print("SIGNAL RUNNER")
        print("=" * 80)
        
        total_generated = 0
        
        for symbol in symbols:
            print(f"\n{'─' * 80}")
            print(f"📊 {symbol}")
            print('─' * 80)
            
            for tf in timeframes:
                print(f"\n  Timeframe: {tf}")
                
                count = self.process_symbol_timeframe(symbol, tf)
                
                if count > 0:
                    print(f"  ✓ Generated {count} signals")
                    total_generated += count
                else:
                    print(f"  → No new signals needed")
        
        print("\n" + "=" * 80)
        print(f"✅ TOTAL SIGNALS GENERATED: {total_generated}")
        print("=" * 80)


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("SIGNAL RUNNER TEST")
    print("=" * 80)
    
    runner = SignalRunner()
    
    # Test finding candles without signals
    print("\nTest 1: Find candles without signals")
    print("-" * 80)
    
    candles = runner.get_candles_without_signals('BTC/USDT', '1h', limit=5)
    print(f"Found {len(candles)} candles without signals")
    
    if candles:
        for candle in candles:
            print(f"  Candle #{candle['id']}: {candle['datetime']}")
        
        # Test generating signal for first candle
        print("\nTest 2: Generate signal for first candle")
        print("-" * 80)
        
        test_candle = candles[0]
        print(f"Processing Candle #{test_candle['id']}: {test_candle['datetime']}")
        
        signal_data = runner.generate_signal_for_candle(test_candle)
        
        if signal_data:
            print(f"  ✓ Generated signal:")
            print(f"    Signal: {signal_data['signal']}")
            print(f"    Score: {signal_data['score_total']:.1f}/{signal_data['max_score']:.0f}")
            print(f"    TF Type: {signal_data['tf_type']}")
            print(f"    Entry: {signal_data.get('entry_price', 'N/A')}")
            print(f"    Stop: {signal_data.get('stop_loss', 'N/A')}")
            print(f"    Target: {signal_data.get('target_price', 'N/A')}")
            
            # Test storing signal
            print("\nTest 3: Store signal in database")
            print("-" * 80)
            
            success = runner.store_signal(signal_data)
            
            if success:
                print(f"  ✓ Successfully stored signal for Candle #{test_candle['id']}")
            else:
                print(f"  ✗ Failed to store signal")
        else:
            print("  ✗ Failed to generate signal")
    else:
        print("  ✓ All candles have signals!")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)
