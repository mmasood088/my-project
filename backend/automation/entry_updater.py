"""
Entry Updater
Automatically manage entry tracking lifecycle

Matches your existing entry_tracking table schema with:
- validation_status and exit_status
- Individual exit level tracking (exit_1_hit, exit_2_hit, exit_3_hit)
- Recovery tracking
- Active flag
"""

import sys
import os
from datetime import datetime
from sqlalchemy import text
from typing import List, Dict, Optional, Tuple

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine


class EntryUpdater:
    """
    Manage entry tracking lifecycle using your existing schema
    
    Validation Status:
    - VALIDATING: Entry confirming (0-1% profit zone)
    - VALIDATED: Entry confirmed
    - INVALID: Failed validation
    
    Exit Status:
    - ACTIVE: Tracking with exit system
    - EXIT-1: First exit level hit
    - EXIT-2: Second exit level hit
    - EXIT-3: Critical exit level hit
    - EXITED: Position closed
    """
    
    def __init__(self):
        self.engine = engine
        
        # Validation settings (matching Pine Script)
        self.intraday_validation_pct = 1.0
        self.intraday_invalidation_pct = 1.0
        self.swing_validation_pct = 1.0
        self.swing_invalidation_pct = 2.0
        self.validation_window_bars = 3
        
        # Breakeven settings
        self.breakeven_threshold = 1.0
        self.exit1_below_entry = 0.0
        self.exit2_below_entry = 0.5
        self.exit3_below_entry = 1.0
        
        # Zone 3 (2-5% profit)
        self.zone3_start = 2.0
        self.zone3_lock_pct = 50.0
        self.zone3_exit2_drop = 1.0
        self.zone3_exit3_drop = 1.0
        
        # Zone 4 (5-10% profit)
        self.zone4_start = 5.0
        self.zone4_lock_pct = 60.0
        self.zone4_exit2_drop = 1.5
        self.zone4_exit3_drop = 1.0
        
        # Zone 5 (10%+ profit)
        self.zone5_start = 10.0
        self.zone5_lock_pct = 70.0
        self.zone5_exit1_drop = 2.0
        self.zone5_exit2_drop = 1.0
        self.zone5_exit3_drop = 1.0
        
        print("✓ Entry Updater initialized")
    
    def classify_timeframe(self, timeframe: str) -> str:
        """Classify timeframe as Intraday or Swing"""
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
        elif timeframe.endswith('h'):
            minutes = int(timeframe[:-1]) * 60
        elif timeframe.endswith('d') or timeframe == 'D':
            minutes = 1440
        else:
            minutes = 60
        
        return 'Intraday' if minutes <= 240 else 'Swing'
    
    def get_new_entry_signals(self) -> List[Dict]:
        """
        Find new BUY/A-BUY/EARLY-BUY signals without entries
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        s.id as signal_id,
                        s.candle_id,
                        s.symbol,
                        s.timeframe,
                        s.datetime,
                        s.signal,
                        s.tf_type,
                        s.score_total,
                        s.entry_price,
                        s.stop_loss,
                        s.target_price,
                        s.current_price
                    FROM signals s
                    LEFT JOIN entry_tracking e ON s.id = e.signal_id
                    WHERE s.signal IN ('A-BUY', 'BUY', 'EARLY-BUY')
                      AND e.id IS NULL
                    ORDER BY s.datetime DESC
                    LIMIT 100
                """)
                
                result = conn.execute(query).fetchall()
                
                signals = []
                for row in result:
                    signals.append({
                        'signal_id': row[0],
                        'candle_id': row[1],
                        'symbol': row[2],
                        'timeframe': row[3],
                        'datetime': row[4],
                        'signal': row[5],
                        'tf_type': row[6],
                        'score': float(row[7]) if row[7] else 0.0,
                        'entry_price': float(row[8]) if row[8] else None,
                        'stop_loss': float(row[9]) if row[9] else None,
                        'target_price': float(row[10]) if row[10] else None,
                        'current_price': float(row[11]) if row[11] else None
                    })
                
                return signals
        
        except Exception as e:
            print(f"  ✗ Error finding new entry signals: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def create_entry(self, signal: Dict) -> bool:
        """
        Create a new entry from a signal
        """
        try:
            # Get ATR for this candle
            atr = self.get_atr_for_candle(signal['candle_id'])
            
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO entry_tracking (
                        signal_id, symbol, timeframe, entry_signal,
                        entry_datetime, entry_price, entry_score,
                        stop_loss, target_price, atr_at_entry,
                        validation_status, validation_candles_count, max_validation_candles,
                        exit_status,
                        peak_price, current_price,
                        current_profit_pct, max_profit_pct,
                        exit_1_hit, exit_2_hit, exit_3_hit,
                        trailing_stop_active, recovery_attempt,
                        active,
                        created_at, updated_at
                    ) VALUES (
                        :signal_id, :symbol, :timeframe, :entry_signal,
                        :entry_datetime, :entry_price, :entry_score,
                        :stop_loss, :target_price, :atr_at_entry,
                        'VALIDATING', 0, :max_validation_candles,
                        'ACTIVE',
                        :peak_price, :current_price,
                        0.0, 0.0,
                        FALSE, FALSE, FALSE,
                        FALSE, FALSE,
                        TRUE,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                """)
                
                conn.execute(query, {
                    'signal_id': signal['signal_id'],
                    'symbol': signal['symbol'],
                    'timeframe': signal['timeframe'],
                    'entry_signal': signal['signal'],
                    'entry_datetime': signal['datetime'],
                    'entry_price': signal['entry_price'],
                    'entry_score': signal['score'],
                    'stop_loss': signal['stop_loss'],
                    'target_price': signal['target_price'],
                    'atr_at_entry': atr,
                    'max_validation_candles': self.validation_window_bars,
                    'peak_price': signal['current_price'],
                    'current_price': signal['current_price']
                })
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"  ✗ Error creating entry: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_atr_for_candle(self, candle_id: int) -> Optional[float]:
        """Get ATR value for a candle"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT i.atr
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.id = :candle_id
                """)
                
                result = conn.execute(query, {'candle_id': candle_id}).fetchone()
                
                if result and result[0]:
                    return float(result[0])
                return None
        
        except Exception as e:
            return None
    
    def get_active_entries(self) -> List[Dict]:
        """
        Get all active entries
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        id, signal_id, symbol, timeframe, entry_signal,
                        entry_datetime, entry_price, entry_score,
                        stop_loss, target_price, atr_at_entry,
                        validation_status, validation_datetime, 
                        validation_candles_count, max_validation_candles,
                        exit_status, exit_datetime, exit_price, exit_reason,
                        peak_price, peak_datetime,
                        current_price, current_profit_pct, max_profit_pct, final_profit_pct,
                        exit_1_hit, exit_1_datetime, exit_1_price,
                        exit_2_hit, exit_2_datetime, exit_2_price,
                        exit_3_hit, exit_3_datetime, exit_3_price,
                        trailing_stop_price, trailing_stop_active,
                        recovery_attempt, recovery_low_price, recovery_datetime,
                        active
                    FROM entry_tracking
                    WHERE active = TRUE
                    ORDER BY entry_datetime DESC
                """)
                
                result = conn.execute(query).fetchall()
                
                entries = []
                for row in result:
                    entries.append({
                        'id': row[0],
                        'signal_id': row[1],
                        'symbol': row[2],
                        'timeframe': row[3],
                        'entry_signal': row[4],
                        'entry_datetime': row[5],
                        'entry_price': float(row[6]) if row[6] else None,
                        'entry_score': float(row[7]) if row[7] else None,
                        'stop_loss': float(row[8]) if row[8] else None,
                        'target_price': float(row[9]) if row[9] else None,
                        'atr_at_entry': float(row[10]) if row[10] else None,
                        'validation_status': row[11],
                        'validation_datetime': row[12],
                        'validation_candles_count': row[13],
                        'max_validation_candles': row[14],
                        'exit_status': row[15],
                        'exit_datetime': row[16],
                        'exit_price': float(row[17]) if row[17] else None,
                        'exit_reason': row[18],
                        'peak_price': float(row[19]) if row[19] else None,
                        'peak_datetime': row[20],
                        'current_price': float(row[21]) if row[21] else None,
                        'current_profit_pct': float(row[22]) if row[22] else None,
                        'max_profit_pct': float(row[23]) if row[23] else None,
                        'final_profit_pct': float(row[24]) if row[24] else None,
                        'exit_1_hit': row[25],
                        'exit_1_datetime': row[26],
                        'exit_1_price': float(row[27]) if row[27] else None,
                        'exit_2_hit': row[28],
                        'exit_2_datetime': row[29],
                        'exit_2_price': float(row[30]) if row[30] else None,
                        'exit_3_hit': row[31],
                        'exit_3_datetime': row[32],
                        'exit_3_price': float(row[33]) if row[33] else None,
                        'trailing_stop_price': float(row[34]) if row[34] else None,
                        'trailing_stop_active': row[35],
                        'recovery_attempt': row[36],
                        'recovery_low_price': float(row[37]) if row[37] else None,
                        'recovery_datetime': row[38],
                        'active': row[39]
                    })
                
                return entries
        
        except Exception as e:
            print(f"  ✗ Error getting active entries: {e}")
            import traceback
            traceback.print_exc()
            return []
    def get_latest_candle_price(self, symbol: str, timeframe: str) -> Optional[float]:
        """Get the latest candle close price"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT close
                    FROM candles
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                    ORDER BY datetime DESC
                    LIMIT 1
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()
                
                if result:
                    return float(result[0])
                return None
        
        except Exception as e:
            print(f"  ✗ Error getting latest price: {e}")
            return None
    
    def get_latest_signal(self, symbol: str, timeframe: str) -> Optional[str]:
        """Get the latest signal"""
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT signal
                    FROM signals
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                    ORDER BY datetime DESC
                    LIMIT 1
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()
                
                if result:
                    return result[0]
                return None
        
        except Exception as e:
            print(f"  ✗ Error getting latest signal: {e}")
            return None
    
    def calculate_exit_levels(self, entry_price: float, peak_price: float) -> Tuple[float, float, float]:
        """
        Calculate EXIT-1, EXIT-2, EXIT-3 levels based on profit zones
        
        Returns:
            Tuple of (exit1, exit2, exit3)
        """
        peak_profit_pct = ((peak_price - entry_price) / entry_price) * 100
        
        # Zone 1: 0-1% profit (No profit protection)
        if peak_profit_pct < self.breakeven_threshold:
            return (0.0, 0.0, 0.0)
        
        # Zone 2: 1-2% profit (Breakeven protection)
        elif peak_profit_pct < self.zone3_start:
            exit1 = entry_price * (1 - self.exit1_below_entry / 100)
            exit2 = entry_price * (1 - self.exit2_below_entry / 100)
            exit3 = entry_price * (1 - self.exit3_below_entry / 100)
            return (exit1, exit2, exit3)
        
        # Zone 3: 2-5% profit (Lock 50%)
        elif peak_profit_pct < self.zone4_start:
            profit_gain = peak_price - entry_price
            locked_profit = profit_gain * (self.zone3_lock_pct / 100)
            exit1 = entry_price + locked_profit
            exit2 = exit1 * (1 - self.zone3_exit2_drop / 100)
            exit3 = exit2 * (1 - self.zone3_exit3_drop / 100)
            return (exit1, exit2, exit3)
        
        # Zone 4: 5-10% profit (Lock 60%)
        elif peak_profit_pct < self.zone5_start:
            profit_gain = peak_price - entry_price
            locked_profit = profit_gain * (self.zone4_lock_pct / 100)
            exit1 = entry_price + locked_profit
            exit2 = exit1 * (1 - self.zone4_exit2_drop / 100)
            exit3 = exit2 * (1 - self.zone4_exit3_drop / 100)
            return (exit1, exit2, exit3)
        
        # Zone 5: 10%+ profit (Lock 70%)
        else:
            profit_gain = peak_price - entry_price
            locked_profit = profit_gain * (self.zone5_lock_pct / 100)
            exit1_from_lock = entry_price + locked_profit
            exit1_from_peak = peak_price * (1 - self.zone5_exit1_drop / 100)
            exit1 = max(exit1_from_lock, exit1_from_peak)
            exit2 = exit1 * (1 - self.zone5_exit2_drop / 100)
            exit3 = exit2 * (1 - self.zone5_exit3_drop / 100)
            return (exit1, exit2, exit3)
    
    def process_validating_entry(self, entry: Dict, current_price: float, 
                                 current_signal: str) -> Dict:
        """
        Process an entry in VALIDATING state
        
        Returns:
            Updated entry dict
        """
        entry_price = entry['entry_price']
        peak_price = entry['peak_price']
        validation_candles = entry['validation_candles_count']
        tf_type = self.classify_timeframe(entry['timeframe'])
        
        # Update peak
        if current_price > peak_price:
            peak_price = current_price
            entry['peak_price'] = peak_price
            entry['peak_datetime'] = datetime.now()
        
        # Calculate percentages
        current_pct = ((current_price - entry_price) / entry_price) * 100
        peak_pct = ((peak_price - entry_price) / entry_price) * 100
        
        # Track lowest for invalidation
        if entry['recovery_low_price'] is None or current_price < entry['recovery_low_price']:
            entry['recovery_low_price'] = current_price
        
        lowest_pct = ((entry['recovery_low_price'] - entry_price) / entry_price) * 100
        
        # Get thresholds
        validation_pct = self.intraday_validation_pct if tf_type == 'Intraday' else self.swing_validation_pct
        invalidation_pct = self.intraday_invalidation_pct if tf_type == 'Intraday' else self.swing_invalidation_pct
        
        # Check VALIDATION (reached +1%)
        if peak_pct >= validation_pct:
            entry['validation_status'] = 'VALIDATED'
            entry['validation_datetime'] = datetime.now()
            entry['exit_status'] = 'ACTIVE'
            print(f"    ✓ Entry #{entry['id']} VALIDATED at +{peak_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        # Check INVALIDATION
        elif lowest_pct <= -invalidation_pct:
            entry['validation_status'] = 'INVALID'
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = 'PRICE_DROP'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    ✗ Entry #{entry['id']} INVALIDATED - Price drop {lowest_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        elif current_signal == 'CAUTION':
            entry['validation_status'] = 'INVALID'
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = 'CAUTION_SIGNAL'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    ✗ Entry #{entry['id']} INVALIDATED - CAUTION signal ({entry['symbol']} {entry['timeframe']})")
        
        elif current_signal == 'WATCH' and lowest_pct <= -(invalidation_pct * 1.1):
            entry['validation_status'] = 'INVALID'
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = 'WATCH_PRICE_DROP'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    ✗ Entry #{entry['id']} INVALIDATED - WATCH + price drop ({entry['symbol']} {entry['timeframe']})")
        
        # Update counters
        entry['validation_candles_count'] = validation_candles + 1
        entry['current_price'] = current_price
        entry['current_profit_pct'] = current_pct
        entry['max_profit_pct'] = max(entry['max_profit_pct'] or 0.0, peak_pct)
        
        return entry
    def process_validated_entry(self, entry: Dict, current_price: float, 
                                current_signal: str) -> Dict:
        """
        Process an entry in VALIDATED state (exit tracking)
        
        Returns:
            Updated entry dict
        """
        entry_price = entry['entry_price']
        peak_price = entry['peak_price']
        exit_status = entry['exit_status']
        
        # Update peak
        if current_price > peak_price:
            peak_price = current_price
            entry['peak_price'] = peak_price
            entry['peak_datetime'] = datetime.now()
        
        current_pct = ((current_price - entry_price) / entry_price) * 100
        peak_pct = ((peak_price - entry_price) / entry_price) * 100
        
        # ==================== PRIORITY EXIT CHECKS ====================
        
        # Check SIGNAL-BASED EXITS (highest priority)
        if current_signal == 'SELL':
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = 'SELL_SIGNAL'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    🔴 Entry #{entry['id']} EXITED - SELL signal at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
            return entry
        
        elif current_signal == 'CAUTION':
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = 'CAUTION_SIGNAL'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    🔴 Entry #{entry['id']} EXITED - CAUTION signal at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
            return entry
        
        # ==================== CALCULATE EXIT LEVELS ====================
        
        exit1, exit2, exit3 = self.calculate_exit_levels(entry_price, peak_price)
        
        # Store trailing stop (EXIT-1 is the trailing stop)
        if exit1 > 0:
            entry['trailing_stop_price'] = exit1
            entry['trailing_stop_active'] = True
        
        # ==================== EXIT LEVEL TRACKING ====================
        
        # Check EXIT-1
        if exit1 > 0 and current_price <= exit1 and not entry['exit_1_hit']:
            entry['exit_1_hit'] = True
            entry['exit_1_datetime'] = datetime.now()
            entry['exit_1_price'] = current_price
            entry['exit_status'] = 'EXIT-1'
            print(f"    🟠 Entry #{entry['id']} → EXIT-1 at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        # Check EXIT-2
        if exit2 > 0 and current_price <= exit2 and not entry['exit_2_hit']:
            entry['exit_2_hit'] = True
            entry['exit_2_datetime'] = datetime.now()
            entry['exit_2_price'] = current_price
            entry['exit_status'] = 'EXIT-2'
            print(f"    🟠 Entry #{entry['id']} → EXIT-2 at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        # Check EXIT-3
        if exit3 > 0 and current_price <= exit3 and not entry['exit_3_hit']:
            entry['exit_3_hit'] = True
            entry['exit_3_datetime'] = datetime.now()
            entry['exit_3_price'] = current_price
            entry['exit_status'] = 'EXIT-3'
            print(f"    🔴 Entry #{entry['id']} → EXIT-3 CRITICAL at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        # Check RECOVERY (price moving back up)
        if entry['exit_3_hit'] and current_price > exit3:
            entry['exit_status'] = 'EXIT-2'
            entry['recovery_attempt'] = True
            entry['recovery_datetime'] = datetime.now()
            print(f"    🟢 Entry #{entry['id']} RECOVERING from EXIT-3 ({entry['symbol']} {entry['timeframe']})")
        
        elif entry['exit_2_hit'] and not entry['exit_3_hit'] and current_price > exit2:
            entry['exit_status'] = 'EXIT-1'
            entry['recovery_attempt'] = True
            entry['recovery_datetime'] = datetime.now()
            print(f"    🟢 Entry #{entry['id']} RECOVERING from EXIT-2 ({entry['symbol']} {entry['timeframe']})")
        
        elif entry['exit_1_hit'] and not entry['exit_2_hit'] and current_price > exit1:
            entry['exit_status'] = 'ACTIVE'
            entry['recovery_attempt'] = True
            entry['recovery_datetime'] = datetime.now()
            print(f"    🟢 Entry #{entry['id']} RECOVERED to ACTIVE ({entry['symbol']} {entry['timeframe']})")
        
        # Check EXIT-3 + weak signal = FINAL EXIT
        if entry['exit_3_hit'] and current_signal in ['WATCH', 'CAUTION']:
            entry['exit_status'] = 'EXITED'
            entry['exit_reason'] = f'EXIT3_{current_signal}'
            entry['exit_datetime'] = datetime.now()
            entry['exit_price'] = current_price
            entry['final_profit_pct'] = current_pct
            entry['active'] = False
            print(f"    🔴 Entry #{entry['id']} FINAL EXIT - EXIT-3 + {current_signal} at +{current_pct:.2f}% ({entry['symbol']} {entry['timeframe']})")
        
        # Update entry
        entry['current_price'] = current_price
        entry['current_profit_pct'] = current_pct
        entry['max_profit_pct'] = max(entry['max_profit_pct'] or 0.0, peak_pct)
        
        return entry
    
    def update_entry_in_db(self, entry: Dict) -> bool:
        """
        Update entry in database
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    UPDATE entry_tracking SET
                        validation_status = :validation_status,
                        validation_datetime = :validation_datetime,
                        validation_candles_count = :validation_candles_count,
                        exit_status = :exit_status,
                        exit_datetime = :exit_datetime,
                        exit_price = :exit_price,
                        exit_reason = :exit_reason,
                        peak_price = :peak_price,
                        peak_datetime = :peak_datetime,
                        current_price = :current_price,
                        current_profit_pct = :current_profit_pct,
                        max_profit_pct = :max_profit_pct,
                        final_profit_pct = :final_profit_pct,
                        exit_1_hit = :exit_1_hit,
                        exit_1_datetime = :exit_1_datetime,
                        exit_1_price = :exit_1_price,
                        exit_2_hit = :exit_2_hit,
                        exit_2_datetime = :exit_2_datetime,
                        exit_2_price = :exit_2_price,
                        exit_3_hit = :exit_3_hit,
                        exit_3_datetime = :exit_3_datetime,
                        exit_3_price = :exit_3_price,
                        trailing_stop_price = :trailing_stop_price,
                        trailing_stop_active = :trailing_stop_active,
                        recovery_attempt = :recovery_attempt,
                        recovery_low_price = :recovery_low_price,
                        recovery_datetime = :recovery_datetime,
                        active = :active,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = :id
                """)
                
                conn.execute(query, {
                    'id': entry['id'],
                    'validation_status': entry['validation_status'],
                    'validation_datetime': entry.get('validation_datetime'),
                    'validation_candles_count': entry['validation_candles_count'],
                    'exit_status': entry['exit_status'],
                    'exit_datetime': entry.get('exit_datetime'),
                    'exit_price': entry.get('exit_price'),
                    'exit_reason': entry.get('exit_reason'),
                    'peak_price': entry['peak_price'],
                    'peak_datetime': entry.get('peak_datetime'),
                    'current_price': entry['current_price'],
                    'current_profit_pct': entry['current_profit_pct'],
                    'max_profit_pct': entry['max_profit_pct'],
                    'final_profit_pct': entry.get('final_profit_pct'),
                    'exit_1_hit': entry['exit_1_hit'],
                    'exit_1_datetime': entry.get('exit_1_datetime'),
                    'exit_1_price': entry.get('exit_1_price'),
                    'exit_2_hit': entry['exit_2_hit'],
                    'exit_2_datetime': entry.get('exit_2_datetime'),
                    'exit_2_price': entry.get('exit_2_price'),
                    'exit_3_hit': entry['exit_3_hit'],
                    'exit_3_datetime': entry.get('exit_3_datetime'),
                    'exit_3_price': entry.get('exit_3_price'),
                    'trailing_stop_price': entry.get('trailing_stop_price'),
                    'trailing_stop_active': entry.get('trailing_stop_active'),
                    'recovery_attempt': entry.get('recovery_attempt'),
                    'recovery_low_price': entry.get('recovery_low_price'),
                    'recovery_datetime': entry.get('recovery_datetime'),
                    'active': entry['active']
                })
                
                conn.commit()
                return True
        
        except Exception as e:
            print(f"  ✗ Error updating entry #{entry['id']}: {e}")
            import traceback
            traceback.print_exc()
            return False
    def process_all_entries(self):
        """
        Main processing loop for all entries
        
        1. Create new entries from signals
        2. Update all active entries
        """
        print("=" * 80)
        print("ENTRY UPDATER")
        print("=" * 80)
        
        # Step 1: Create new entries
        print("\n📥 Step 1: Creating new entries from BUY/A-BUY/EARLY-BUY signals")
        print("-" * 80)
        
        new_signals = self.get_new_entry_signals()
        
        if new_signals:
            print(f"Found {len(new_signals)} new entry signals")
            
            created_count = 0
            for signal in new_signals:
                if self.create_entry(signal):
                    print(f"  ✓ Created entry: {signal['symbol']} {signal['timeframe']} ({signal['signal']}) @ {signal['entry_price']}")
                    created_count += 1
            
            print(f"\n✅ Created {created_count} new entries")
        else:
            print("  → No new entry signals")
        
        # Step 2: Update active entries
        print("\n🔄 Step 2: Updating active entries")
        print("-" * 80)
        
        active_entries = self.get_active_entries()
        
        if active_entries:
            print(f"Found {len(active_entries)} active entries to update\n")
            
            updated_count = 0
            for entry in active_entries:
                symbol = entry['symbol']
                timeframe = entry['timeframe']
                
                # Get latest price and signal
                current_price = self.get_latest_candle_price(symbol, timeframe)
                current_signal = self.get_latest_signal(symbol, timeframe)
                
                if current_price is None or current_signal is None:
                    print(f"  ⚠️  Entry #{entry['id']}: Missing price/signal data")
                    continue
                
                # Show entry info
                entry_pct = ((current_price - entry['entry_price']) / entry['entry_price']) * 100
                print(f"  Entry #{entry['id']}: {symbol} {timeframe}")
                print(f"    Status: {entry['validation_status']} / {entry['exit_status']}")
                print(f"    Price: {entry['entry_price']:.2f} → {current_price:.2f} ({entry_pct:+.2f}%)")
                print(f"    Signal: {current_signal}")
                
                # Process based on validation status
                if entry['validation_status'] == 'VALIDATING':
                    updated_entry = self.process_validating_entry(entry, current_price, current_signal)
                elif entry['validation_status'] == 'VALIDATED':
                    updated_entry = self.process_validated_entry(entry, current_price, current_signal)
                else:
                    # INVALID or EXITED - skip
                    continue
                
                # Update in database
                if self.update_entry_in_db(updated_entry):
                    updated_count += 1
                
                print()  # Blank line between entries
            
            print(f"✅ Updated {updated_count} entries")
        else:
            print("  → No active entries to update")
        
        print("\n" + "=" * 80)
        print("✅ ENTRY UPDATER COMPLETE")
        print("=" * 80)


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("ENTRY UPDATER TEST")
    print("=" * 80)
    
    updater = EntryUpdater()
    
    # Run the full processing loop
    updater.process_all_entries()
    
    print("\n💡 Verify in Navicat:")
    print("\n   -- View all active entries")
    print("   SELECT id, symbol, timeframe, entry_signal, entry_price,")
    print("          validation_status, exit_status, current_price, current_profit_pct")
    print("   FROM entry_tracking")
    print("   WHERE active = TRUE")
    print("   ORDER BY entry_datetime DESC;")
    
    print("\n   -- View entry details")
    print("   SELECT * FROM entry_tracking")
    print("   WHERE active = TRUE")
    print("   ORDER BY entry_datetime DESC")
    print("   LIMIT 5;")
    
    print("\n   -- View exit tracking")
    print("   SELECT id, symbol, validation_status, exit_status,")
    print("          exit_1_hit, exit_2_hit, exit_3_hit,")
    print("          current_profit_pct, max_profit_pct")
    print("   FROM entry_tracking")
    print("   WHERE active = TRUE;")