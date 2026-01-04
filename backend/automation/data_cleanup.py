"""
Data Cleanup Script
Deletes candles, indicators, and signals older than 6 months
Runs periodically to keep database size manageable

Author: Trading Dashboard System
Purpose: Maintain 6-month data retention policy
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
DATABASE_URL = "postgresql://postgres:trading123@localhost:5432/trading_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class DataCleanup:
    def __init__(self, retention_months=6):
        """
        Initialize data cleanup
        
        Args:
            retention_months: Number of months to retain (default 6)
        """
        self.db = SessionLocal()
        self.retention_months = retention_months
        self.cutoff_date = datetime.now() - timedelta(days=retention_months * 30)
    
    def get_old_data_stats(self):
        """
        Get statistics on old data before deletion
        """
        print(f"\n📊 Checking for data older than {self.cutoff_date.strftime('%Y-%m-%d')}...")
        
        try:
            # Count old candles
            candles_query = text("""
                SELECT 
                    symbol,
                    timeframe,
                    COUNT(*) as count,
                    MIN(datetime) as oldest,
                    MAX(datetime) as newest
                FROM candles
                WHERE datetime < :cutoff_date
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)
            
            candles_result = self.db.execute(candles_query, {
                'cutoff_date': self.cutoff_date
            }).fetchall()
            
            # Count old indicators (via candles)
            indicators_query = text("""
                SELECT COUNT(*) 
                FROM indicators i
                JOIN candles c ON i.candle_id = c.id
                WHERE c.datetime < :cutoff_date
            """)
            
            indicators_count = self.db.execute(indicators_query, {
                'cutoff_date': self.cutoff_date
            }).fetchone()[0]
            
            # Count old signals (via candles)
            signals_query = text("""
                SELECT COUNT(*) 
                FROM signals s
                JOIN candles c ON s.candle_id = c.id
                WHERE c.datetime < :cutoff_date
            """)
            
            signals_count = self.db.execute(signals_query, {
                'cutoff_date': self.cutoff_date
            }).fetchone()[0]
            
            return {
                'candles': candles_result,
                'indicators_count': indicators_count,
                'signals_count': signals_count
            }
        
        except Exception as e:
            print(f"✗ Error getting stats: {e}")
            return None
    
    def delete_old_candles(self):
        """
        Delete candles older than cutoff date
        Indicators and signals will cascade delete automatically
        """
        print(f"\n🗑️  Deleting candles older than {self.cutoff_date.strftime('%Y-%m-%d')}...")
        
        try:
            delete_query = text("""
                DELETE FROM candles
                WHERE datetime < :cutoff_date
            """)
            
            result = self.db.execute(delete_query, {
                'cutoff_date': self.cutoff_date
            })
            
            self.db.commit()
            
            deleted_count = result.rowcount
            print(f"✓ Deleted {deleted_count:,} old candles")
            print(f"  (Indicators and signals cascade deleted automatically)")
            
            return deleted_count
        
        except Exception as e:
            print(f"✗ Error deleting old data: {e}")
            self.db.rollback()
            return 0
    
    def get_current_stats(self):
        """
        Get current database statistics after cleanup
        """
        print(f"\n📊 Current Database Statistics:")
        
        try:
            # Total candles
            total_query = text("SELECT COUNT(*) FROM candles")
            total_candles = self.db.execute(total_query).fetchone()[0]
            
            # By symbol/timeframe
            breakdown_query = text("""
                SELECT 
                    symbol,
                    timeframe,
                    COUNT(*) as count,
                    MIN(datetime) as oldest,
                    MAX(datetime) as newest
                FROM candles
                GROUP BY symbol, timeframe
                ORDER BY symbol, timeframe
            """)
            
            breakdown = self.db.execute(breakdown_query).fetchall()
            
            # Total indicators
            indicators_query = text("SELECT COUNT(*) FROM indicators")
            total_indicators = self.db.execute(indicators_query).fetchone()[0]
            
            # Total signals
            signals_query = text("SELECT COUNT(*) FROM signals")
            total_signals = self.db.execute(signals_query).fetchone()[0]
            
            print(f"  📈 Total candles: {total_candles:,}")
            print(f"  📊 Total indicators: {total_indicators:,}")
            print(f"  🎯 Total signals: {total_signals:,}")
            
            print(f"\n  Breakdown by symbol/timeframe:")
            print(f"  {'Symbol':<15} {'TF':<6} {'Count':>10} {'Oldest':<20} {'Newest':<20}")
            print(f"  {'-'*75}")
            
            for row in breakdown:
                print(f"  {row[0]:<15} {row[1]:<6} {row[2]:>10,} {str(row[3]):<20} {str(row[4]):<20}")
            
            return {
                'total_candles': total_candles,
                'total_indicators': total_indicators,
                'total_signals': total_signals,
                'breakdown': breakdown
            }
        
        except Exception as e:
            print(f"✗ Error getting current stats: {e}")
            return None
    
    def run_cleanup(self, dry_run=False):
        """
        Run complete cleanup process
        
        Args:
            dry_run: If True, only show what would be deleted without actually deleting
        """
        start_time = datetime.now()
        
        print("=" * 80)
        print(f"DATA CLEANUP - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 80)
        print(f"Retention policy: {self.retention_months} months")
        print(f"Cutoff date: {self.cutoff_date.strftime('%Y-%m-%d')}")
        print(f"Mode: {'DRY RUN (no deletion)' if dry_run else 'LIVE (will delete)'}")
        
        # Get statistics on old data
        old_stats = self.get_old_data_stats()
        
        if not old_stats:
            print("✗ Failed to get statistics")
            return False
        
        # Display what will be deleted
        if old_stats['candles']:
            print(f"\n📋 Old data found:")
            print(f"  {'Symbol':<15} {'TF':<6} {'Count':>10} {'Oldest':<20} {'Newest':<20}")
            print(f"  {'-'*75}")
            
            total_old_candles = 0
            for row in old_stats['candles']:
                print(f"  {row[0]:<15} {row[1]:<6} {row[2]:>10,} {str(row[3]):<20} {str(row[4]):<20}")
                total_old_candles += row[2]
            
            print(f"\n  Total old candles: {total_old_candles:,}")
            print(f"  Associated indicators: {old_stats['indicators_count']:,}")
            print(f"  Associated signals: {old_stats['signals_count']:,}")
        else:
            print("\n✓ No old data found - database is clean!")
            return True
        
        # Delete if not dry run
        if not dry_run:
            deleted = self.delete_old_candles()
            
            if deleted > 0:
                # Show current stats after cleanup
                self.get_current_stats()
        else:
            print("\n⚠️  DRY RUN MODE - No data was deleted")
            print("   Run without --dry-run flag to actually delete old data")
        
        # Summary
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print(f"\n{'='*80}")
        print(f"✅ CLEANUP COMPLETE")
        print(f"Duration: {duration:.1f} seconds")
        print(f"{'='*80}")
        
        return True
    
    def close(self):
        self.db.close()


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up old trading data')
    parser.add_argument('--months', type=int, default=6, 
                       help='Retention period in months (default: 6)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    
    args = parser.parse_args()
    
    cleanup = DataCleanup(retention_months=args.months)
    
    try:
        cleanup.run_cleanup(dry_run=args.dry_run)
    finally:
        cleanup.close()