"""
Entry Tracking Updater
Monitor active entries and update their status based on price movement

This script:
- Fetches active entries
- Gets latest price for each entry
- Updates validation status
- Checks exit conditions
- Implements trailing stops
"""

import sys
import os
from sqlalchemy import text
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import engine
from calculations.entry_tracker import EntryTracker

class EntryTrackingUpdater:
    """
    Update entry tracking records with latest prices
    """
    
    def __init__(self):
        self.engine = engine
        self.tracker = EntryTracker()
    
    def get_latest_candle_for_entry(self, symbol: str, timeframe: str, after_datetime: datetime):
        """
        Get latest candle after entry datetime
        
        Returns:
            List of (datetime, close_price) tuples
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT datetime, close
                    FROM candles
                    WHERE symbol = :symbol
                      AND timeframe = :timeframe
                      AND datetime > :after_datetime
                    ORDER BY datetime ASC
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'after_datetime': after_datetime
                })
                
                candles = [(row[0], float(row[1])) for row in result]
                return candles
        
        except Exception as e:
            print(f"  ✗ Error fetching candles: {e}")
            return []
    
    def update_all_entries(self):
        """
        Update all active entries with latest prices
        """
        print("=" * 80)
        print("ENTRY TRACKING UPDATER")
        print("=" * 80)
        
        # Get active entries
        entries = self.tracker.get_active_entries()
        
        print(f"\nFound {len(entries)} active entries to update\n")
        
        if not entries:
            print("  ⚠️  No active entries to update")
            return
        
        updated_count = 0
        
        for entry in entries:
            entry_id = entry['id']
            symbol = entry['symbol']
            timeframe = entry['timeframe']
            entry_datetime = entry['entry_datetime']
            validation_status = entry['validation_status']
            exit_status = entry['exit_status']
            
            print(f"Entry #{entry_id}: {symbol} {timeframe} | Status: {validation_status}/{exit_status}")
            
            # Get candles after entry
            candles = self.get_latest_candle_for_entry(symbol, timeframe, entry_datetime)
            
            if not candles:
                print(f"  ⚠️  No candles found after entry")
                continue
            
            print(f"  Processing {len(candles)} candles...")
            
            # Update with each candle
            for candle_datetime, close_price in candles:
                self.tracker.update_entry_price(entry_id, close_price, candle_datetime)
            
            updated_count += 1
        
        print("\n" + "=" * 80)
        print(f"✅ UPDATED {updated_count} ENTRIES")
        print("=" * 80)
    
    def show_entry_summary(self):
        """
        Show summary of all entries
        """
        try:
            with self.engine.connect() as conn:
                # Summary by status
                query = text("""
                    SELECT 
                        validation_status,
                        exit_status,
                        COUNT(*) as count,
                        ROUND(AVG(current_profit_pct), 2) as avg_profit,
                        ROUND(AVG(max_profit_pct), 2) as avg_max_profit
                    FROM entry_tracking
                    GROUP BY validation_status, exit_status
                    ORDER BY validation_status, exit_status
                """)
                
                result = conn.execute(query)
                
                print("\n" + "=" * 80)
                print("📊 ENTRY SUMMARY BY STATUS")
                print("=" * 80)
                print(f"{'Validation':<15} {'Exit Status':<15} {'Count':<8} {'Avg P&L':<12} {'Max P&L':<12}")
                print("─" * 80)
                
                for row in result:
                    val_status = row[0] or 'N/A'
                    exit_status = row[1] or 'N/A'
                    count = row[2]
                    avg_profit = float(row[3]) if row[3] else 0.0
                    avg_max_profit = float(row[4]) if row[4] else 0.0
                    
                    print(f"{val_status:<15} {exit_status:<15} {count:<8} {avg_profit:>+8.2f}%   {avg_max_profit:>+8.2f}%")
                
                # Top performers
                print("\n" + "=" * 80)
                print("🏆 TOP 5 PERFORMERS (by max profit)")
                print("=" * 80)
                
                query = text("""
                    SELECT 
                        id, symbol, timeframe, entry_signal,
                        ROUND(entry_price, 2) as entry,
                        ROUND(current_price, 2) as current,
                        ROUND(peak_price, 2) as peak,
                        ROUND(current_profit_pct, 2) as profit,
                        ROUND(max_profit_pct, 2) as max_profit,
                        validation_status,
                        exit_status
                    FROM entry_tracking
                    ORDER BY max_profit_pct DESC
                    LIMIT 5
                """)
                
                result = conn.execute(query)
                
                for row in result:
                    entry_id = row[0]
                    symbol = row[1]
                    tf = row[2]
                    signal = row[3]
                    entry_price = float(row[4]) if row[4] else 0
                    current_price = float(row[5]) if row[5] else 0
                    peak_price = float(row[6]) if row[6] else 0
                    profit = float(row[7]) if row[7] else 0
                    max_profit = float(row[8]) if row[8] else 0
                    val_status = row[9]
                    exit_status = row[10]
                    
                    print(f"\nEntry #{entry_id}: {symbol} {tf} {signal}")
                    print(f"  Entry: ${entry_price:,.2f} | Current: ${current_price:,.2f} | Peak: ${peak_price:,.2f}")
                    print(f"  Profit: {profit:+.2f}% | Max: {max_profit:+.2f}%")
                    print(f"  Status: {val_status} / {exit_status}")
                
        except Exception as e:
            print(f"✗ Error showing summary: {e}")
            import traceback
            traceback.print_exc()

# ============================================
# STANDALONE SCRIPT
# ============================================

if __name__ == "__main__":
    updater = EntryTrackingUpdater()
    
    # Update all entries
    updater.update_all_entries()
    
    # Show summary
    updater.show_entry_summary()
    
    print("\n💡 View detailed entries in Navicat:")
    print("   SELECT id, symbol, timeframe, entry_signal, validation_status, exit_status,")
    print("          ROUND(current_profit_pct, 2) as profit, ROUND(max_profit_pct, 2) as max_profit")
    print("   FROM entry_tracking")
    print("   ORDER BY entry_datetime DESC;")