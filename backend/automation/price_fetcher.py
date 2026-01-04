"""
Live Price Fetcher
Fetches real-time prices from Binance exchange for tracked symbols
"""

import ccxt
import logging
from typing import Dict, List
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PriceFetcher:
    def __init__(self):
        """Initialize Binance exchange connection"""
        self.exchange = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'spot',
            }
        })
    
    def get_live_price(self, symbol: str) -> float:
        """
        Get live price for a single symbol
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
        
        Returns:
            Current price as float
        """
        try:
            ticker = self.exchange.fetch_ticker(symbol)
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {e}")
            return 0.0
    
    def get_live_prices(self, symbols: List[str]) -> Dict[str, dict]:
        """
        Get live prices for multiple symbols
        
        Args:
            symbols: List of trading pairs
        
        Returns:
            Dictionary with symbol as key and price data as value
        """
        results = {}
        
        for symbol in symbols:
            try:
                ticker = self.exchange.fetch_ticker(symbol)
                
                results[symbol] = {
                    'price': float(ticker['last']),
                    'bid': float(ticker['bid']) if ticker['bid'] else 0.0,
                    'ask': float(ticker['ask']) if ticker['ask'] else 0.0,
                    'high_24h': float(ticker['high']) if ticker['high'] else 0.0,
                    'low_24h': float(ticker['low']) if ticker['low'] else 0.0,
                    'volume_24h': float(ticker['quoteVolume']) if ticker['quoteVolume'] else 0.0,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                logger.info(f"✓ Fetched live price for {symbol}: ${results[symbol]['price']:.2f}")
                
            except Exception as e:
                logger.error(f"✗ Error fetching {symbol}: {e}")
                results[symbol] = {
                    'price': 0.0,
                    'error': str(e),
                    'timestamp': datetime.utcnow().isoformat()
                }
        
        return results


# Test function
if __name__ == "__main__":
    fetcher = PriceFetcher()
    
    # Test with a few symbols
    test_symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
    
    print("\n" + "="*80)
    print("LIVE PRICE FETCHER TEST")
    print("="*80)
    
    prices = fetcher.get_live_prices(test_symbols)
    
    print("\nResults:")
    for symbol, data in prices.items():
        if 'error' in data:
            print(f"  ✗ {symbol}: ERROR - {data['error']}")
        else:
            print(f"  ✓ {symbol}: ${data['price']:.2f}")
            print(f"    24h High: ${data['high_24h']:.2f} | 24h Low: ${data['low_24h']:.2f}")
    
    print("\n" + "="*80)