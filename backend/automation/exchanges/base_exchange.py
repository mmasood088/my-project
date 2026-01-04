"""
Base Exchange Adapter
Abstract interface for all exchange adapters (Binance, PSX, etc.)
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime


class BaseExchange(ABC):
    """
    Abstract base class for exchange adapters
    
    All exchange adapters must implement these methods
    """
    
    def __init__(self):
        self.exchange_name = None
        self.timezone = 'UTC'
    
    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, 
                   since: Optional[datetime] = None, 
                   limit: int = 100) -> List[Dict]:
        """
        Fetch OHLCV candles from exchange
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '1h', '1d')
            since: Fetch candles after this datetime
            limit: Maximum number of candles to fetch
        
        Returns:
            List of candle dicts with keys:
            - datetime: Candle datetime
            - open: Open price
            - high: High price
            - low: Low price
            - close: Close price
            - volume: Volume
        """
        pass
    
    @abstractmethod
    def get_supported_symbols(self) -> List[str]:
        """
        Get list of symbols supported by this exchange
        
        Returns:
            List of symbol strings (e.g., ['BTC/USDT', 'ETH/USDT'])
        """
        pass
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        """
        Get list of timeframes supported by this exchange
        
        Returns:
            List of timeframe strings (e.g., ['15m', '1h', '4h', '1d'])
        """
        pass
    
    def get_timezone(self) -> str:
        """
        Get timezone used by this exchange
        
        Returns:
            Timezone string (e.g., 'UTC', 'Asia/Karachi')
        """
        return self.timezone
    
    def get_exchange_name(self) -> str:
        """
        Get exchange name
        
        Returns:
            Exchange name string (e.g., 'binance', 'psx')
        """
        return self.exchange_name