"""
Binance Exchange Adapter
Fetches OHLCV data from Binance using ccxt
"""

import ccxt
from typing import List, Dict, Optional
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

try:
    from .base_exchange import BaseExchange
except ImportError:
    from base_exchange import BaseExchange

# Load environment variables
load_dotenv()


class BinanceAdapter(BaseExchange):
    """
    Binance exchange adapter for fetching cryptocurrency data
    """
    
    def __init__(self):
        super().__init__()
        self.exchange_name = 'binance'
        self.timezone = 'UTC'
        
        # Initialize ccxt Binance client
        api_key = os.getenv('BINANCE_API_KEY', '')
        api_secret = os.getenv('BINANCE_API_SECRET', '')
        
        self.client = ccxt.binance({
            'apiKey': api_key,
            'secret': api_secret,
            'enableRateLimit': True,  # Respect rate limits
            'options': {
                'defaultType': 'spot',  # Use spot market
            }
        })
        
        print(f"✓ Binance adapter initialized (API key: {'Yes' if api_key else 'No - using public access'})")
    
    def get_candles(self, symbol: str, timeframe: str, 
                   since: Optional[datetime] = None, 
                   limit: int = 100) -> List[Dict]:
        """
        Fetch OHLCV candles from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h', '1d')
            since: Fetch candles after this datetime (UTC)
            limit: Maximum number of candles (max 1000 for Binance)
        
        Returns:
            List of candle dicts
        """
        try:
            # Convert datetime to milliseconds timestamp
            since_ms = None
            if since:
                since_ms = int(since.replace(tzinfo=timezone.utc).timestamp() * 1000)
            
            # Fetch OHLCV data
            ohlcv = self.client.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                since=since_ms,
                limit=min(limit, 1000)  # Binance max is 1000
            )
            
            # Convert to our format
            candles = []
            for candle in ohlcv:
                candles.append({
                    'datetime': datetime.fromtimestamp(candle[0] / 1000, tz=timezone.utc),
                    'open': float(candle[1]),
                    'high': float(candle[2]),
                    'low': float(candle[3]),
                    'close': float(candle[4]),
                    'volume': float(candle[5])
                })
            
            return candles
        
        except Exception as e:
            print(f"✗ Error fetching candles from Binance ({symbol} {timeframe}): {e}")
            return []
    
    def get_supported_symbols(self) -> List[str]:
        """
        Get supported cryptocurrency symbols
        
        Returns:
            List of trading pairs
        """
        return [
            'BTC/USDT',
            'ETH/USDT',
            'SOL/USDT'
        ]
    
    def get_supported_timeframes(self) -> List[str]:
        """
        Get supported timeframes
        
        Returns:
            List of timeframe strings
        """
        return ['15m', '1h', '4h', '1d']


# ============================================
# TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("BINANCE ADAPTER TEST")
    print("=" * 80)
    
    # Initialize adapter
    adapter = BinanceAdapter()
    
    print(f"\nExchange: {adapter.get_exchange_name()}")
    print(f"Timezone: {adapter.get_timezone()}")
    print(f"Symbols: {adapter.get_supported_symbols()}")
    print(f"Timeframes: {adapter.get_supported_timeframes()}")
    
    # Test fetching candles
    print("\n" + "=" * 80)
    print("FETCHING LATEST 5 CANDLES FOR BTC/USDT 1h")
    print("=" * 80)
    
    candles = adapter.get_candles('BTC/USDT', '1h', limit=5)
    
    print(f"\nFetched {len(candles)} candles:\n")
    
    for candle in candles:
        print(f"{candle['datetime']} | O: ${candle['open']:,.2f} | H: ${candle['high']:,.2f} | "
              f"L: ${candle['low']:,.2f} | C: ${candle['close']:,.2f} | V: {candle['volume']:,.0f}")
    
    # Test fetching with since parameter
    print("\n" + "=" * 80)
    print("FETCHING CANDLES SINCE 2025-12-01")
    print("=" * 80)
    
    since_date = datetime(2025, 12, 1, tzinfo=timezone.utc)
    candles = adapter.get_candles('ETH/USDT', '1d', since=since_date, limit=10)
    
    print(f"\nFetched {len(candles)} candles:\n")
    
    for candle in candles:
        print(f"{candle['datetime'].date()} | C: ${candle['close']:,.2f}")