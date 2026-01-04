"""
Master Automation Script
Runs the complete automation pipeline:
1. Fetch new candles
2. Calculate indicators
3. Generate signals
4. Update entries

NOW WITH DYNAMIC SYMBOL LOADING FROM DATABASE!
"""

import sys
import os
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from candle_fetcher import CandleFetcher
from indicator_runner import IndicatorRunner
from signal_runner import SignalRunner
from entry_updater import EntryUpdater

# Database connection for reading symbols
# ⚠️ CHANGE 'your_password' TO YOUR ACTUAL PASSWORD!
DATABASE_URL = "postgresql://postgres:trading123@localhost:5432/trading_db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)


def get_tracked_symbols():
    """
    Load active symbols from database
    Returns list of symbol configurations
    """
    db = SessionLocal()
    
    try:
        query = text("""
            SELECT symbol, exchange, timeframes
            FROM tracked_symbols
            WHERE active = TRUE
            ORDER BY symbol
        """)
        
        result = db.execute(query).fetchall()
        
        symbols_config = []
        for row in result:
            symbols_config.append({
                'symbol': row[0],
                'exchange': row[1],
                'timeframes': row[2]  # PostgreSQL array
            })
        
        return symbols_config
    
    finally:
        db.close()


def run_automation():
    """
    Run the complete automation pipeline
    """
    start_time = datetime.now()
    
    print("=" * 80)
    print(f"TRADING DASHBOARD AUTOMATION - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Load symbols from database
    print("\n📊 Loading symbols from database...")
    try:
        symbols_config = get_tracked_symbols()
    except Exception as e:
        print(f"❌ Failed to load symbols from database: {e}")
        return False
    
    if not symbols_config:
        print("❌ No active symbols found in database!")
        return False
    
    print(f"✓ Loaded {len(symbols_config)} symbols:")
    for config in symbols_config:
        print(f"  - {config['symbol']} ({config['exchange']}): {', '.join(config['timeframes'])}")
    
    try:
        # ============================================
        # STEP 1: FETCH NEW CANDLES
        # ============================================
        print("\n" + "=" * 80)
        print("STEP 1: FETCHING NEW CANDLES")
        print("=" * 80)
        
        fetcher = CandleFetcher()
        total_candles = 0
        
        # Process each symbol from database
        for config in symbols_config:
            symbol = config['symbol']
            exchange = config['exchange']
            timeframes = config['timeframes']
            
            for tf in timeframes:
                candles_fetched = fetcher.fetch_and_store(exchange, symbol, tf, limit=10)
                total_candles += candles_fetched
        
        print(f"\n✅ STEP 1 COMPLETE: Fetched {total_candles} new candles")
        
        # ============================================
        # STEP 2: CALCULATE INDICATORS
        # ============================================
        print("\n" + "=" * 80)
        print("STEP 2: CALCULATING INDICATORS")
        print("=" * 80)
        
        runner = IndicatorRunner()
        total_indicators = 0
        
        # Process each symbol from database
        for config in symbols_config:
            symbol = config['symbol']
            timeframes = config['timeframes']
            
            for tf in timeframes:
                # Get candles without indicators
                candles = runner.get_candles_without_indicators(symbol, tf, limit=500)
                
                if not candles:
                    continue
                
                print(f"\n  {symbol} {tf}: Processing {len(candles)} candles")
                
                for candle in candles:
                    # Get historical candles
                    historical_df = runner.get_historical_candles(
                        symbol, tf, candle['datetime'], limit=250
                    )
                    
                    if len(historical_df) < 250:
                        print(f"    ⚠️  Candle {candle['id']}: Only {len(historical_df)} historical candles")
                        continue
                    
                    # Calculate indicators
                    indicators = runner.calculate_indicators_for_candle(candle, historical_df)
                    
                    if indicators:
                        if runner.store_indicators(candle['id'], indicators):
                            total_indicators += 1
        
        print(f"\n✅ STEP 2 COMPLETE: Calculated {total_indicators} indicator sets")
        
        # ============================================
        # STEP 3: GENERATE SIGNALS
        # ============================================
        print("\n" + "=" * 80)
        print("STEP 3: GENERATING SIGNALS")
        print("=" * 80)
        
        signal_runner = SignalRunner()
        total_signals = 0
        
        # Process each symbol from database
        for config in symbols_config:
            symbol = config['symbol']
            timeframes = config['timeframes']
            
            for tf in timeframes:
                count = signal_runner.process_symbol_timeframe(symbol, tf)
                total_signals += count
        
        print(f"\n✅ STEP 3 COMPLETE: Generated {total_signals} signals")
        
        # ============================================
        # STEP 4: UPDATE ENTRIES
        # ============================================
        print("\n" + "=" * 80)
        print("STEP 4: UPDATING ENTRIES")
        print("=" * 80)
        
        entry_updater = EntryUpdater()
        
        # Create new entries
        new_signals = entry_updater.get_new_entry_signals()
        created_count = 0
        
        if new_signals:
            print(f"\nFound {len(new_signals)} new entry signals")
            for signal in new_signals:
                if entry_updater.create_entry(signal):
                    created_count += 1
        
        print(f"\n✓ Created {created_count} new entries")
        
        # Update active entries
        active_entries = entry_updater.get_active_entries()
        updated_count = 0
        
        if active_entries:
            print(f"\nUpdating {len(active_entries)} active entries")
            
            for entry in active_entries:
                symbol = entry['symbol']
                timeframe = entry['timeframe']
                
                # Get latest price and signal
                current_price = entry_updater.get_latest_candle_price(symbol, timeframe)
                current_signal = entry_updater.get_latest_signal(symbol, timeframe)
                
                if current_price is None or current_signal is None:
                    continue
                
                # Process based on state
                if entry['validation_status'] == 'VALIDATING':
                    updated_entry = entry_updater.process_validating_entry(entry, current_price, current_signal)
                elif entry['validation_status'] == 'VALIDATED':
                    updated_entry = entry_updater.process_validated_entry(entry, current_price, current_signal)
                else:
                    continue
                
                # Update in database
                if entry_updater.update_entry_in_db(updated_entry):
                    updated_count += 1
        
        print(f"\n✓ Updated {updated_count} entries")
        print(f"\n✅ STEP 4 COMPLETE")
        
        # ============================================
        # SUMMARY
        # ============================================
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 80)
        print("AUTOMATION SUMMARY")
        print("=" * 80)
        print(f"Started:  {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Finished: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {duration:.1f} seconds")
        print(f"\n📊 Results:")
        print(f"  - Symbols loaded: {len(symbols_config)}")
        print(f"  - Candles fetched: {total_candles}")
        print(f"  - Indicators calculated: {total_indicators}")
        print(f"  - Signals generated: {total_signals}")
        print(f"  - Entries created: {created_count}")
        print(f"  - Entries updated: {updated_count}")
        print("\n✅ AUTOMATION COMPLETE")
        print("=" * 80)
        
        return True
    
    except Exception as e:
        print(f"\n❌ AUTOMATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_automation()
    sys.exit(0 if success else 1)