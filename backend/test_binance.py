import ccxt
import pandas as pd
from datetime import datetime

print("=" * 50)
print("Testing Binance Connection")
print("=" * 50)

try:
    # Connect to Binance
    exchange = ccxt.binance()
    print("\n✓ Connected to Binance successfully!")
    
    # Fetch 10 recent 1-hour candles for BTC/USDT
    print("\nFetching BTC/USDT data (last 10 hours)...")
    ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h', limit=10)
    
    # Convert to DataFrame
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['datetime'] = pd.to_datetime(df['timestamp'], unit='ms')
    
    # Display results
    print(f"\n✓ Fetched {len(df)} candles successfully!")
    print(f"\nLatest BTC/USDT Price: ${df['close'].iloc[-1]:,.2f}")
    print("\nLast 5 Candles:")
    print("-" * 80)
    print(df[['datetime', 'open', 'high', 'low', 'close', 'volume']].tail().to_string(index=False))
    print("-" * 80)
    
    print("\n✓ Test completed successfully! All systems working.")
    
except Exception as e:
    print(f"\n✗ Error occurred: {e}")
    print("Please check your internet connection and try again.")

print("\n" + "=" * 50)