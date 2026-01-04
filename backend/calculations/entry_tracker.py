"""
Entry Tracker
Track BUY/A-BUY signal entries with validation and exit stages

Matches TradingView Pine Script entry tracking logic:
- Entry validation (VALIDATING → VALID)
- Exit stages (EXIT-1, EXIT-2, EXIT-3)
- Trailing stops
- Recovery tracking
"""

import pandas as pd
from sqlalchemy import text
from typing import Dict, List, Optional
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine

class EntryTracker:
    """
    Track and manage trading entries
    
    Features:
    - Create entries from BUY/A-BUY signals
    - Validate entries within N candles
    - Track exit stages (EXIT-1, EXIT-2, EXIT-3)
    - Implement trailing stops
    - Monitor recovery attempts
    """
    
    def __init__(self):
        self.engine = engine
    
    def create_entry_from_signal(self, signal_id: int, max_validation_candles: int = 3):
        """
        Create entry tracking record from a BUY/A-BUY signal
        
        Args:
            signal_id: ID of the signal to track
            max_validation_candles: Number of candles to validate entry (default 3)
        
        Returns:
            entry_id or None if failed
        """
        try:
            with self.engine.connect() as conn:
                # Fetch signal details
                query = text("""
                    SELECT 
                        id, symbol, timeframe, datetime, signal,
                        entry_price, stop_loss, target_price,
                        score_total, current_price
                    FROM signals
                    WHERE id = :signal_id
                      AND signal IN ('BUY', 'A-BUY')
                """)
                
                result = conn.execute(query, {'signal_id': signal_id}).fetchone()
                
                if result is None:
                    print(f"  ⚠️  Signal {signal_id} not found or not a BUY signal")
                    return None
                
                signal = dict(result._mapping)
                
                # Check if entry already exists
                check_query = text("""
                    SELECT id FROM entry_tracking WHERE signal_id = :signal_id
                """)
                existing = conn.execute(check_query, {'signal_id': signal_id}).fetchone()
                
                if existing:
                    print(f"  ⚠️  Entry already exists for signal {signal_id}")
                    return existing[0]
                
                # Fetch ATR
                atr_query = text("""
                    SELECT i.atr
                    FROM signals s
                    JOIN indicators i ON s.candle_id = i.candle_id
                    WHERE s.id = :signal_id
                """)
                atr_result = conn.execute(atr_query, {'signal_id': signal_id}).fetchone()
                atr = float(atr_result[0]) if atr_result and atr_result[0] else 0.0
                
                # Create entry
                insert_query = text("""
                    INSERT INTO entry_tracking (
                        signal_id, symbol, timeframe,
                        entry_signal, entry_datetime, entry_price, entry_score,
                        stop_loss, target_price, atr_at_entry,
                        peak_price, current_price,
                        max_validation_candles
                    ) VALUES (
                        :signal_id, :symbol, :timeframe,
                        :entry_signal, :entry_datetime, :entry_price, :entry_score,
                        :stop_loss, :target_price, :atr_at_entry,
                        :peak_price, :current_price,
                        :max_validation_candles
                    )
                    RETURNING id
                """)
                
                entry_id = conn.execute(insert_query, {
                    'signal_id': signal['id'],
                    'symbol': signal['symbol'],
                    'timeframe': signal['timeframe'],
                    'entry_signal': signal['signal'],
                    'entry_datetime': signal['datetime'],
                    'entry_price': signal['entry_price'],
                    'entry_score': signal['score_total'],
                    'stop_loss': signal['stop_loss'],
                    'target_price': signal['target_price'],
                    'atr_at_entry': atr,
                    'peak_price': signal['current_price'],
                    'current_price': signal['current_price'],
                    'max_validation_candles': max_validation_candles
                }).fetchone()[0]
                
                conn.commit()
                
                print(f"  ✓ Created entry #{entry_id} for {signal['symbol']} {signal['timeframe']} {signal['signal']}")
                return entry_id
        
        except Exception as e:
            print(f"  ✗ Error creating entry from signal {signal_id}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_active_entries(self, symbol: Optional[str] = None, 
                          timeframe: Optional[str] = None) -> List[Dict]:
        """
        Get all active entries (not exited)
        
        Returns:
            List of entry dicts
        """
        try:
            with self.engine.connect() as conn:
                query = "SELECT * FROM entry_tracking WHERE active = true"
                params = {}
                
                if symbol:
                    query += " AND symbol = :symbol"
                    params['symbol'] = symbol
                
                if timeframe:
                    query += " AND timeframe = :timeframe"
                    params['timeframe'] = timeframe
                
                query += " ORDER BY entry_datetime DESC"
                
                result = conn.execute(text(query), params)
                
                entries = []
                for row in result:
                    entry = dict(row._mapping)
                    # Convert Decimal to float
                    for key in entry:
                        if entry[key] is not None and hasattr(entry[key], '__float__'):
                            entry[key] = float(entry[key])
                    entries.append(entry)
                
                return entries
        
        except Exception as e:
            print(f"  ✗ Error getting active entries: {e}")
            return []
    
    def update_entry_price(self, entry_id: int, current_price: float, 
                          current_datetime: datetime):
        """
        Update entry with current price and check for all exit conditions
        
        Exit Stages:
        - EXIT-1: First target hit (2x ATR for Intraday, 4x for Swing)
        - EXIT-2: Second target hit (3x ATR for Intraday, 6x for Swing)
        - EXIT-3: Final target hit (4x ATR for Intraday, 8x for Swing)
        - STOP-LOSS: Stop loss hit
        - RECOVERY: Attempting recovery after drawdown
        """
        try:
            with self.engine.connect() as conn:
                # Fetch entry
                query = text("SELECT * FROM entry_tracking WHERE id = :entry_id")
                result = conn.execute(query, {'entry_id': entry_id}).fetchone()
                
                if result is None:
                    return
                
                entry = dict(result._mapping)
                
                # Skip if already exited (prevents duplicate SIGNAL-EXIT processing)
                if entry['exit_status'] in ['SIGNAL-EXIT', 'EXIT-3', 'STOP-LOSS']:
                    return
                
                # Convert Decimal to float
                for key in ['entry_price', 'stop_loss', 'target_price', 'peak_price', 
                           'current_price', 'trailing_stop_price', 'atr_at_entry']:
                    if entry.get(key) is not None:
                        entry[key] = float(entry[key])
                
                # Get timeframe type for multiplier
                tf_type = 'Intraday' if entry['timeframe'] in ['15m', '1h', '4h'] else 'Swing'
                atr = entry.get('atr_at_entry', 0)
                
                # Calculate exit targets
                if tf_type == 'Intraday':
                    exit_1_target = entry['entry_price'] + (2 * atr)
                    exit_2_target = entry['entry_price'] + (3 * atr)
                    exit_3_target = entry['entry_price'] + (4 * atr)
                else:  # Swing
                    exit_1_target = entry['entry_price'] + (4 * atr)
                    exit_2_target = entry['entry_price'] + (6 * atr)
                    exit_3_target = entry['entry_price'] + (8 * atr)
                
                # Update peak price if new high
                peak_price = entry['peak_price']
                peak_datetime = entry.get('peak_datetime')
                
                if current_price > peak_price:
                    peak_price = current_price
                    peak_datetime = current_datetime
                
                # Calculate profit percentages
                current_profit_pct = ((current_price - entry['entry_price']) / entry['entry_price']) * 100
                max_profit_pct = ((peak_price - entry['entry_price']) / entry['entry_price']) * 100
                
                # Initialize variables
                trailing_stop_active = entry.get('trailing_stop_active', False)
                trailing_stop_price = entry.get('trailing_stop_price')
                
                # Check validation status
                validation_status = entry['validation_status']
                validation_candles = entry['validation_candles_count'] + 1
                validation_datetime = entry.get('validation_datetime')
                
                if validation_status == 'VALIDATING':
                    # Check if price confirms entry (above entry price)
                    if current_price >= entry['entry_price']:
                        validation_status = 'VALID'
                        validation_datetime = current_datetime
                        print(f"    ✓ Entry #{entry_id} VALIDATED at ${current_price:.2f}")
                    elif validation_candles >= entry['max_validation_candles']:
                        validation_status = 'INVALIDATED'
                        validation_datetime = current_datetime
                        print(f"    ✗ Entry #{entry_id} INVALIDATED (price below entry after {validation_candles} candles)")
                
                # Exit condition tracking
                exit_status = entry['exit_status']
                exit_price = entry.get('exit_price')
                exit_datetime = entry.get('exit_datetime')
                exit_reason = entry.get('exit_reason')
                
                exit_1_hit = entry.get('exit_1_hit', False)
                exit_1_datetime = entry.get('exit_1_datetime')
                exit_1_price = entry.get('exit_1_price')
                
                exit_2_hit = entry.get('exit_2_hit', False)
                exit_2_datetime = entry.get('exit_2_datetime')
                exit_2_price = entry.get('exit_2_price')
                
                exit_3_hit = entry.get('exit_3_hit', False)
                exit_3_datetime = entry.get('exit_3_datetime')
                exit_3_price = entry.get('exit_3_price')
                
                recovery_attempt = entry.get('recovery_attempt', False)
                recovery_low_price = entry.get('recovery_low_price')
                recovery_datetime = entry.get('recovery_datetime')
                final_profit_pct = entry.get('final_profit_pct')
                
                # =====================================================
                # CHECK FOR SIGNAL-BASED EXIT (CAUTION/SELL)
                # Exit on CAUTION/SELL even if entry not validated yet
                # =====================================================
                signal_query = text("""
                    SELECT signal, datetime
                    FROM signals 
                    WHERE symbol = :symbol 
                    AND timeframe = :timeframe 
                    AND datetime <= :current_datetime
                    ORDER BY datetime DESC
                    LIMIT 1
                """)

                current_signal = conn.execute(signal_query, {
                    'symbol': entry['symbol'],
                    'timeframe': entry['timeframe'],
                    'current_datetime': current_datetime
                }).fetchone()
                
                # If latest signal is CAUTION or SELL, exit immediately (even if not validated)
                if current_signal and current_signal[0] in ['CAUTION', 'SELL']:
                    # Allow signal exit from VALIDATING, ACTIVE, EXIT-1, EXIT-2, TRAILING-STOP
                    if exit_status in ['ACTIVE', 'EXIT-1', 'EXIT-2', 'TRAILING-STOP'] or validation_status == 'VALIDATING':
                        exit_status = 'SIGNAL-EXIT'
                        validation_status = 'INVALIDATED'  # Mark as invalidated since exiting early
                        exit_price = current_price
                        exit_datetime = current_datetime
                        exit_reason = f'{current_signal[0]} signal at {current_signal[1]} - immediate exit'
                        final_profit_pct = current_profit_pct
                        print(f"    🚨 Entry #{entry_id} SIGNAL EXIT ({current_signal[0]})! Profit: {current_profit_pct:+.2f}%")
                        
                        # Update DB and return immediately
                        update_query = text("""
                            UPDATE entry_tracking SET
                                current_price = :current_price,
                                peak_price = :peak_price,
                                peak_datetime = :peak_datetime,
                                current_profit_pct = :current_profit_pct,
                                max_profit_pct = :max_profit_pct,
                                final_profit_pct = :final_profit_pct,
                                validation_status = :validation_status,
                                exit_status = :exit_status,
                                exit_price = :exit_price,
                                exit_datetime = :exit_datetime,
                                exit_reason = :exit_reason,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = :entry_id
                        """)
                        
                        conn.execute(update_query, {
                            'entry_id': entry_id,
                            'current_price': current_price,
                            'peak_price': peak_price,
                            'peak_datetime': peak_datetime,
                            'current_profit_pct': current_profit_pct,
                            'max_profit_pct': max_profit_pct,
                            'final_profit_pct': final_profit_pct,
                            'validation_status': validation_status,
                            'exit_status': exit_status,
                            'exit_price': exit_price,
                            'exit_datetime': exit_datetime,
                            'exit_reason': exit_reason
                        })
                        
                        conn.commit()
                        return
                
                # Only process normal exits if validated
                if validation_status == 'VALID':
                    
                    # =====================================================
                    # NORMAL EXIT LOGIC (only if not signal-exited)
                    # =====================================================
                    
                    # Check EXIT-3 (highest target)
                    if not exit_3_hit and current_price >= exit_3_target:
                        exit_3_hit = True
                        exit_3_datetime = current_datetime
                        exit_3_price = current_price
                        exit_status = 'EXIT-3'
                        exit_price = current_price
                        exit_datetime = current_datetime
                        exit_reason = 'Final target reached (EXIT-3) - Full exit'
                        final_profit_pct = current_profit_pct
                        print(f"    🎯🎯🎯 Entry #{entry_id} reached EXIT-3 FINAL target! Profit: +{current_profit_pct:.2f}%")
                    
                    # Check EXIT-2 (second target)
                    elif not exit_2_hit and current_price >= exit_2_target:
                        exit_2_hit = True
                        exit_2_datetime = current_datetime
                        exit_2_price = current_price
                        exit_status = 'EXIT-2'
                        # Move trailing stop tighter
                        trailing_stop_active = True
                        trailing_stop_price = entry['entry_price'] + atr  # Entry + 1 ATR
                        print(f"    🎯🎯 Entry #{entry_id} reached EXIT-2 target! Trailing stop → ${trailing_stop_price:.2f}")
                    
                    # Check EXIT-1 (first target)
                    elif not exit_1_hit and current_price >= exit_1_target:
                        exit_1_hit = True
                        exit_1_datetime = current_datetime
                        exit_1_price = current_price
                        exit_status = 'EXIT-1'
                        # Activate trailing stop at breakeven
                        trailing_stop_active = True
                        trailing_stop_price = entry['entry_price']
                        print(f"    🎯 Entry #{entry_id} reached EXIT-1 target! Trailing stop → ${trailing_stop_price:.2f}")
                    
                    # Check trailing stop (if active and not fully exited)
                    if trailing_stop_active and exit_status != 'EXIT-3':
                        # Update trailing stop if price makes new high
                        if exit_2_hit:
                            # After EXIT-2, trail at Entry + 1 ATR from peak
                            new_trailing_stop = peak_price - (2 * atr)
                            if new_trailing_stop > trailing_stop_price:
                                trailing_stop_price = new_trailing_stop
                        elif exit_1_hit:
                            # After EXIT-1, trail at breakeven until EXIT-2
                            new_trailing_stop = entry['entry_price']
                            trailing_stop_price = max(trailing_stop_price or 0, new_trailing_stop)
                        
                        # Check if trailing stop hit
                        if current_price <= trailing_stop_price:
                            exit_status = 'TRAILING-STOP'
                            exit_price = current_price
                            exit_datetime = current_datetime
                            exit_reason = f'Trailing stop hit at ${trailing_stop_price:.2f}'
                            final_profit_pct = current_profit_pct
                            print(f"    ⚠️ Entry #{entry_id} trailing stop hit. Profit: {current_profit_pct:+.2f}%")
                    
                    # Check regular stop-loss (if not exited and no trailing stop)
                    if exit_status == 'ACTIVE' and not trailing_stop_active:
                        if current_price <= entry['stop_loss']:
                            exit_status = 'STOP-LOSS'
                            exit_price = current_price
                            exit_datetime = current_datetime
                            exit_reason = 'Stop loss hit'
                            final_profit_pct = current_profit_pct
                            print(f"    ❌ Entry #{entry_id} stop loss hit. Loss: {current_profit_pct:.2f}%")
                    
                    # Check recovery attempt (after deep drawdown)
                    if exit_status in ['EXIT-1', 'EXIT-2'] and not exit_3_hit:
                        # If price drops more than 50% from peak after hitting EXIT-1/2
                        drawdown_pct = ((peak_price - current_price) / peak_price) * 100
                        
                        if drawdown_pct > 50 and not recovery_attempt:
                            recovery_attempt = True
                            recovery_low_price = current_price
                            recovery_datetime = current_datetime
                            exit_status = 'RECOVERY'
                            print(f"    🔄 Entry #{entry_id} in RECOVERY mode. Drawdown: -{drawdown_pct:.1f}%")
                        
                        # Track lowest price during recovery
                        if recovery_attempt:
                            if current_price < (recovery_low_price or float('inf')):
                                recovery_low_price = current_price
                                recovery_datetime = current_datetime
                
                # Update database
                update_query = text("""
                    UPDATE entry_tracking SET
                        current_price = :current_price,
                        peak_price = :peak_price,
                        peak_datetime = :peak_datetime,
                        current_profit_pct = :current_profit_pct,
                        max_profit_pct = :max_profit_pct,
                        final_profit_pct = :final_profit_pct,
                        
                        validation_status = :validation_status,
                        validation_datetime = :validation_datetime,
                        validation_candles_count = :validation_candles_count,
                        
                        exit_status = :exit_status,
                        exit_price = :exit_price,
                        exit_datetime = :exit_datetime,
                        exit_reason = :exit_reason,
                        
                        exit_1_hit = :exit_1_hit,
                        exit_1_datetime = :exit_1_datetime,
                        exit_1_price = :exit_1_price,
                        
                        exit_2_hit = :exit_2_hit,
                        exit_2_datetime = :exit_2_datetime,
                        exit_2_price = :exit_2_price,
                        
                        exit_3_hit = :exit_3_hit,
                        exit_3_datetime = :exit_3_datetime,
                        exit_3_price = :exit_3_price,
                        
                        trailing_stop_active = :trailing_stop_active,
                        trailing_stop_price = :trailing_stop_price,
                        
                        recovery_attempt = :recovery_attempt,
                        recovery_low_price = :recovery_low_price,
                        recovery_datetime = :recovery_datetime,
                        
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :entry_id
                """)
                
                conn.execute(update_query, {
                    'entry_id': entry_id,
                    'current_price': current_price,
                    'peak_price': peak_price,
                    'peak_datetime': peak_datetime,
                    'current_profit_pct': current_profit_pct,
                    'max_profit_pct': max_profit_pct,
                    'final_profit_pct': final_profit_pct,
                    
                    'validation_status': validation_status,
                    'validation_datetime': validation_datetime,
                    'validation_candles_count': validation_candles,
                    
                    'exit_status': exit_status,
                    'exit_price': exit_price,
                    'exit_datetime': exit_datetime,
                    'exit_reason': exit_reason,
                    
                    'exit_1_hit': exit_1_hit,
                    'exit_1_datetime': exit_1_datetime,
                    'exit_1_price': exit_1_price if exit_1_price else None,
                    
                    'exit_2_hit': exit_2_hit,
                    'exit_2_datetime': exit_2_datetime,
                    'exit_2_price': exit_2_price if exit_2_price else None,
                    
                    'exit_3_hit': exit_3_hit,
                    'exit_3_datetime': exit_3_datetime,
                    'exit_3_price': exit_3_price if exit_3_price else None,
                    
                    'trailing_stop_active': trailing_stop_active,
                    'trailing_stop_price': trailing_stop_price,
                    
                    'recovery_attempt': recovery_attempt,
                    'recovery_low_price': recovery_low_price,
                    'recovery_datetime': recovery_datetime
                })
                
                conn.commit()
        
        except Exception as e:
            print(f"  ✗ Error updating entry {entry_id}: {e}")
            import traceback
            traceback.print_exc()

# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("ENTRY TRACKER TEST")
    print("=" * 80)
    
    tracker = EntryTracker()
    
    # Find some BUY signals to track
    with engine.connect() as conn:
        query = text("""
            SELECT id, symbol, timeframe, datetime, signal, score_total, current_price
            FROM signals
            WHERE signal IN ('BUY', 'A-BUY')
            ORDER BY score_total DESC
            LIMIT 5
        """)
        
        result = conn.execute(query)
        signals = result.fetchall()
    
    print(f"\nFound {len(signals)} BUY/A-BUY signals to track\n")
    
    for signal in signals:
        signal_id, symbol, tf, dt, sig, score, price = signal
        print(f"Signal #{signal_id}: {symbol} {tf} {sig} @ ${float(price):.2f} (score: {float(score):.1f})")
        
        # Create entry
        entry_id = tracker.create_entry_from_signal(signal_id)
    
    # Show active entries
    print("\n" + "=" * 80)
    print("ACTIVE ENTRIES")
    print("=" * 80)
    
    entries = tracker.get_active_entries()
    print(f"\nTotal active entries: {len(entries)}\n")
    
    for entry in entries[:10]:  # Show first 10
        print(f"Entry #{entry['id']}: {entry['symbol']} {entry['timeframe']} {entry['entry_signal']}")
        print(f"  Entry: ${entry['entry_price']:.2f} | Stop: ${entry['stop_loss']:.2f} | Target: ${entry['target_price']:.2f}")
        print(f"  Status: {entry['validation_status']} | Exit: {entry['exit_status']}")
    
    print("\n💡 View in Navicat:")
    print("   SELECT * FROM entry_tracking ORDER BY entry_datetime DESC LIMIT 20;")