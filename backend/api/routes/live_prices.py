"""
Live Prices API Routes
Endpoints for fetching real-time prices from exchange
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict
import sys
import os

# Add automation directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../automation'))
from price_fetcher import PriceFetcher

from database import get_db

router = APIRouter(
    prefix="/api/live-prices",
    tags=["live-prices"]
)

# Initialize price fetcher (singleton)
price_fetcher = PriceFetcher()


@router.get("/")
async def get_live_prices(db: Session = Depends(get_db)):
    """
    Get live prices for all active tracked symbols
    """
    
    # Get active symbols from tracked_symbols table
    query = text("""
        SELECT DISTINCT symbol 
        FROM tracked_symbols 
        WHERE active = TRUE
        ORDER BY symbol
    """)
    
    result = db.execute(query)
    active_symbols = [row[0] for row in result.fetchall()]
    
    if not active_symbols:
        return {
            'prices': [],
            'message': 'No active symbols found'
        }
    
    # Fetch live prices
    prices = price_fetcher.get_live_prices(active_symbols)
    
    # Format response
    price_list = []
    for symbol, data in prices.items():
        if 'error' not in data:
            price_list.append({
                'symbol': symbol,
                'price': data['price'],
                'bid': data['bid'],
                'ask': data['ask'],
                'high_24h': data['high_24h'],
                'low_24h': data['low_24h'],
                'volume_24h': data['volume_24h'],
                'timestamp': data['timestamp']
            })
    
    return {
        'prices': price_list,
        'count': len(price_list),
        'timestamp': price_list[0]['timestamp'] if price_list else None
    }


@router.get("/{symbol}")
async def get_single_live_price(symbol: str):
    """
    Get live price for a specific symbol
    Example: /api/live-prices/BTC/USDT
    """
    
    # Format symbol (replace - with /)
    symbol = symbol.replace('-', '/')
    
    try:
        price_data = price_fetcher.get_live_prices([symbol])
        
        if symbol in price_data and 'error' not in price_data[symbol]:
            return {
                'symbol': symbol,
                'data': price_data[symbol]
            }
        else:
            return {
                'symbol': symbol,
                'error': price_data[symbol].get('error', 'Unknown error')
            }
    
    except Exception as e:
        return {
            'symbol': symbol,
            'error': str(e)
        }