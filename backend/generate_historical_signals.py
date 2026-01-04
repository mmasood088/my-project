"""
Historical Signals Generator
Generate signals for all historical candles to test scoring system

Purpose:
- Validate signal generation across different market conditions
- Find examples of BUY/A-BUY signals
- Analyze signal distribution
- Test scoring accuracy
"""

import sys
import os
from sqlalchemy import text
from collections import defaultdict

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine
from calculations.signal_generator import SignalGenerator

class HistoricalSignalsGenerator:
    """
    Generate signals for all historical candles
    """
    
    def __init__(self):
        self.engine = engine
        self.signal_gen = SignalGenerator()
    
    def get_all_candles_with_indicators(self, symbol: str, timeframe: str):
        """
        Get all candles that have indicator data
        
        Returns:
            List of candle IDs
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT c.id
                    FROM candles c
                    INNER JOIN indicators i ON c.id = i.candle_id
                    WHERE c.symbol = :symbol
                      AND c.timeframe = :timeframe
                      AND i.rsi IS NOT NULL
                    ORDER BY c.datetime ASC
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                })
                
                candle_ids = [row[0] for row in result]
                return candle_ids
        
        except Exception as e:
            print(f"  ✗ Error fetching candles: {e}")
            return []
    
    def generate_signal_for_candle(self, candle_id: int):
        """
        Generate signal for a specific candle ID
        
        Returns:
            Signal data dict or None
        """
        try:
            with self.engine.connect() as conn:
                # Fetch candle data with indicators
                query = text("""
                    SELECT 
                        c.id as candle_id,
                        c.symbol,
                        c.timeframe,
                        c.datetime,
                        c.close as current_price,
                        c.volume as current_volume,
                        i.*
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.id = :candle_id
                """)
                
                result = conn.execute(query, {'candle_id': candle_id}).fetchone()
                
                if result is None:
                    return None
                
                # Convert to dict
                import pandas as pd
                data = pd.Series(dict(result._mapping))
                
                # Convert Decimal to float
                for col in data.index:
                    if pd.notna(data[col]):
                        try:
                            data[col] = float(data[col])
                        except:
                            pass
                
                # Get symbol and timeframe
                symbol = data['symbol']
                timeframe = data['timeframe']
                
                # Classify timeframe
                tf_type, max_score = self.signal_gen.classify_timeframe(timeframe)
                
                # Get S/R levels
                auto_sr_mode = self.signal_gen.settings.get('auto_sr_mode', 'Enabled')
                sr = self.signal_gen.sr_calc.get_effective_sr(symbol, timeframe, auto_sr_mode)
                
                # Get Magic Line
                magic_line = self.signal_gen.ml_manager.get_magic_line(symbol)
                
                # Calculate score components
                scores = self.signal_gen.calculate_score_components(data, tf_type)
                
                # Calculate price action bonus
                current_price = data.get('current_price', 0)
                price_bonus = self.signal_gen.calculate_price_action_bonus(
                    current_price, 
                    sr['support'], 
                    sr['resistance'], 
                    magic_line
                )
                
                # Calculate total score
                total_score = self.signal_gen.calculate_total_score(scores, price_bonus, tf_type)
                
                # Classify signal
                signal = self.signal_gen.classify_signal(total_score, tf_type, data)
                
                # Calculate entry/stop/target
                atr = data.get('atr', 0)
                if signal in ['A-BUY', 'BUY']:
                    entry_price = current_price
                    atr_mult = 1.2 if tf_type == 'Intraday' else 2.0
                    target_mult = 2.0 if tf_type == 'Intraday' else 4.0
                    stop_loss = current_price - (atr * atr_mult)
                    target_price = current_price + (atr * target_mult)
                else:
                    entry_price = None
                    stop_loss = None
                    target_price = None
                
                # Build result
                result = {
                    'candle_id': int(data['candle_id']),
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'datetime': data['datetime'],
                    'tf_type': tf_type,
                    'max_score': max_score,
                    'score_total': total_score,
                    'score_rsi': scores['rsi'],
                    'score_macd': scores['macd'],
                    'score_bb': scores['bb'],
                    'score_ema_stack': scores['ema_stack'],
                    'score_supertrend': scores['supertrend'],
                    'score_vwap': scores['vwap'],
                    'score_volume': scores['volume'],
                    'score_adx': scores['adx'],
                    'score_di': scores['di'],
                    'score_obv': scores['obv'],
                    'score_price_action_bonus': price_bonus,
                    'signal': signal,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'target_price': target_price,
                    'current_price': current_price,
                    'support_level': sr['support'],
                    'resistance_level': sr['resistance'],
                    'magic_line_level': magic_line if magic_line else 0.0
                }
                
                return result
        
        except Exception as e:
            print(f"  ✗ Error generating signal for candle {candle_id}: {e}")
            return None
    
    def generate_historical_signals(self, symbols: list, timeframes: list):
        """
        Generate signals for all historical candles
        """
        print("=" * 80)
        print("HISTORICAL SIGNALS GENERATOR")
        print("=" * 80)
        
        total_generated = 0
        signal_counts = defaultdict(lambda: defaultdict(int))
        
        for symbol in symbols:
            print(f"\n{'─' * 80}")
            print(f"📊 {symbol}")
            print('─' * 80)
            
            for tf in timeframes:
                print(f"\n  Timeframe: {tf}")
                
                # Get all candles with indicators
                candle_ids = self.get_all_candles_with_indicators(symbol, tf)
                
                if not candle_ids:
                    print(f"    ⚠️  No candles with indicators")
                    continue
                
                print(f"    Processing {len(candle_ids)} candles...", end=' ')
                
                # Generate signals for all candles
                generated_count = 0
                for candle_id in candle_ids:
                    signal_data = self.generate_signal_for_candle(candle_id)
                    
                    if signal_data:
                        # Store signal
                        self.signal_gen.store_signal(signal_data)
                        
                        # Count signals
                        signal_counts[symbol][signal_data['signal']] += 1
                        
                        generated_count += 1
                        total_generated += 1
                
                print(f"✓ {generated_count} signals generated")
        
        # Print summary
        print("\n" + "=" * 80)
        print("📊 SIGNAL DISTRIBUTION SUMMARY")
        print("=" * 80)
        
        for symbol in symbols:
            print(f"\n{symbol}:")
            for signal_type in ['A-BUY', 'BUY', 'EARLY-BUY', 'WATCH', 'CAUTION', 'SELL']:
                count = signal_counts[symbol][signal_type]
                if count > 0:
                    print(f"  {signal_type:12} : {count:4} signals")
        
        print("\n" + "=" * 80)
        print(f"✅ TOTAL SIGNALS GENERATED: {total_generated}")
        print("=" * 80)
    
    def find_best_signals(self, signal_type: str = 'A-BUY', limit: int = 10):
        """
        Find best signals of a specific type
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        symbol,
                        timeframe,
                        datetime,
                        signal,
                        ROUND(score_total, 2) as score,
                        ROUND(max_score, 0) as max,
                        ROUND(current_price, 2) as price
                    FROM signals
                    WHERE signal = :signal_type
                    ORDER BY score_total DESC
                    LIMIT :limit
                """)
                
                result = conn.execute(query, {
                    'signal_type': signal_type,
                    'limit': limit
                })
                
                print(f"\n{'─' * 80}")
                print(f"🎯 TOP {limit} {signal_type} SIGNALS")
                print('─' * 80)
                print(f"{'Symbol':<12} {'TF':<6} {'Date':<20} {'Score':<10} {'Price':<12}")
                print('─' * 80)
                
                for row in result:
                    print(f"{row[0]:<12} {row[1]:<6} {str(row[2]):<20} {row[4]:.1f}/{row[5]:.0f}   ${row[6]:,.2f}")
        
        except Exception as e:
            print(f"✗ Error finding best signals: {e}")

# ============================================
# STANDALONE SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("HISTORICAL SIGNALS GENERATOR")
    print("=" * 80)
    print("\n⚠️  This will generate signals for ALL historical candles")
    print("   Estimated time: 2-3 minutes\n")
    
    # Confirm
    confirm = input("Continue? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Cancelled.")
        exit()
    
    generator = HistoricalSignalsGenerator()
    
    # Generate for BTC and ETH across all timeframes
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['15m', '1h', '1d']
    
    generator.generate_historical_signals(symbols, timeframes)
    
    # Find best signals
    print("\n")
    generator.find_best_signals('A-BUY', 10)
    generator.find_best_signals('BUY', 10)
    generator.find_best_signals('EARLY-BUY', 10)
    
    print("\n💡 View in Navicat:")
    print("   SELECT signal, COUNT(*) FROM signals GROUP BY signal ORDER BY signal;")
    print("\n💡 View best BUY signals:")
    print("   SELECT * FROM signals WHERE signal IN ('A-BUY', 'BUY') ORDER BY score_total DESC LIMIT 20;")