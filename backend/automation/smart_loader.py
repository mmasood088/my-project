"""
Smart Historical Loader
Only downloads data if needed, tracks progress
"""

import sys
import os
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Database connection
DATABASE_URL = "postgresql://postgres:trading123@localhost:5432/trading_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


class SmartLoader:
    def __init__(self):
        self.db = SessionLocal()
    
    def check_existing_data(self, symbol, timeframe, required_months=6):
        """
        Check if we have enough historical data
        
        Returns: (needs_download, missing_months, oldest_date, candle_count)
        """
        query = text("""
            SELECT 
                COUNT(*) as count,
                MIN(datetime) as oldest_date,
                MAX(datetime) as newest_date
            FROM candles
            WHERE symbol = :symbol
            AND timeframe = :timeframe
        """)
        
        result = self.db.execute(query, {
            'symbol': symbol,
            'timeframe': timeframe
        }).fetchone()
        
        count = result[0]
        oldest_date = result[1]
        
        if count == 0:
            return True, required_months, None, 0
        
        # Check if oldest date is at least 6 months ago
        required_date = datetime.now() - timedelta(days=required_months * 30)
        
        if oldest_date and oldest_date <= required_date:
            # We have enough historical data
            return False, 0, oldest_date, count
        else:
            # Calculate how many months we're missing
            if oldest_date:
                days_missing = (oldest_date - required_date).days
                months_missing = max(1, days_missing // 30)
            else:
                months_missing = required_months
            
            return True, months_missing, oldest_date, count
    
    def check_symbol_status(self, symbol, timeframes):
        """
        Check if symbol needs historical data download
        
        Returns: {
            'needs_download': bool,
            'status': 'ready' | 'partial' | 'missing',
            'details': {...}
        }
        """
        print(f"\n🔍 Checking data status for {symbol}...")
        
        details = {}
        needs_any_download = False
        
        for tf in timeframes:
            needs_download, missing_months, oldest_date, count = self.check_existing_data(symbol, tf)
            
            details[tf] = {
                'needs_download': needs_download,
                'missing_months': missing_months,
                'candle_count': count,
                'oldest_date': oldest_date.isoformat() if oldest_date else None
            }
            
            if needs_download:
                needs_any_download = True
                print(f"  {tf}: Missing {missing_months} months of data")
            else:
                print(f"  {tf}: ✓ Has {count:,} candles from {oldest_date}")
        
        # Determine overall status
        if not needs_any_download:
            status = 'ready'
        elif all(details[tf]['candle_count'] == 0 for tf in timeframes):
            status = 'missing'
        else:
            status = 'partial'
        
        return {
            'needs_download': needs_any_download,
            'status': status,
            'details': details
        }
    
    def update_symbol_status(self, symbol, status, started=None, completed=None):
        """
        Update symbol download status in database
        """
        try:
            updates = ['data_status = :status']
            params = {'symbol': symbol, 'status': status}
            
            if started:
                updates.append('data_download_started = :started')
                params['started'] = started
            
            if completed:
                updates.append('data_download_completed = :completed')
                params['completed'] = completed
            
            query = text(f"""
                UPDATE tracked_symbols
                SET {', '.join(updates)}
                WHERE symbol = :symbol
            """)
            
            self.db.execute(query, params)
            self.db.commit()
            
            print(f"✓ Updated {symbol} status to: {status}")
            return True
        
        except Exception as e:
            print(f"✗ Failed to update status: {e}")
            return False
    
    def load_symbol(self, symbol, exchange, timeframes):
        """
        Smart load: Only download if needed
        """
        print(f"\n{'='*80}")
        print(f"SMART LOADER: {symbol}")
        print(f"{'='*80}")
        
        # Check current status
        status_check = self.check_symbol_status(symbol, timeframes)
        
        if not status_check['needs_download']:
            print(f"\n✅ {symbol} already has complete historical data!")
            print(f"   No download needed.")
            
            # Update status to ready
            self.update_symbol_status(symbol, 'ready')
            
            return {
                'success': True,
                'downloaded': False,
                'message': 'Symbol already has complete data'
            }
        
        # Need to download - update status to downloading
        self.update_symbol_status(symbol, 'downloading', started=datetime.now())
        
        print(f"\n📥 Downloading missing data...")
        
        # Import and run the historical loader
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        
        try:
            # Run add_new_symbol.py functionality
            import subprocess
            script_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'add_new_symbol.py'
            )
            
            result = subprocess.run(
                [sys.executable, script_path, symbol],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            
            if result.returncode == 0:
                print(f"\n✅ Download completed successfully!")
                self.update_symbol_status(symbol, 'ready', completed=datetime.now())
                
                return {
                    'success': True,
                    'downloaded': True,
                    'message': 'Historical data downloaded successfully'
                }
            else:
                print(f"\n✗ Download failed!")
                print(result.stderr)
                self.update_symbol_status(symbol, 'error')
                
                return {
                    'success': False,
                    'downloaded': False,
                    'message': 'Download failed',
                    'error': result.stderr
                }
        
        except Exception as e:
            print(f"\n✗ Error during download: {e}")
            self.update_symbol_status(symbol, 'error')
            
            return {
                'success': False,
                'downloaded': False,
                'message': str(e)
            }
    
    def close(self):
        self.db.close()


# CLI Interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Smart historical data loader')
    parser.add_argument('symbol', help='Trading symbol (e.g., BTC/USDT)')
    parser.add_argument('--exchange', default='binance', help='Exchange name')
    parser.add_argument('--timeframes', nargs='+', default=['15m', '1h', '4h', '1d'],
                       help='Timeframes to check/download')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check status, do not download')
    
    args = parser.parse_args()
    
    loader = SmartLoader()
    
    try:
        if args.check_only:
            status = loader.check_symbol_status(args.symbol, args.timeframes)
            print(f"\n{'='*80}")
            print(f"STATUS: {status['status'].upper()}")
            print(f"Needs download: {status['needs_download']}")
            print(f"{'='*80}")
        else:
            result = loader.load_symbol(args.symbol, args.exchange, args.timeframes)
            print(f"\n{'='*80}")
            print(f"RESULT: {'SUCCESS' if result['success'] else 'FAILED'}")
            print(f"Message: {result['message']}")
            print(f"{'='*80}")
    finally:
        loader.close()