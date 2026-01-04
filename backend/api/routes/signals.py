"""
Signals API Routes
Endpoints for fetching trading signals
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List
from datetime import datetime, timedelta

from database import get_db

# Create router
# Think of router as a "section" of your API
router = APIRouter(
    prefix="/api/signals",  # All routes start with /api/signals
    tags=["signals"]  # Groups endpoints in documentation
)


@router.get("/")
async def get_signals(
    db: Session = Depends(get_db),
    symbol: Optional[str] = Query(None, description="Filter by symbol (e.g., BTC/USDT)"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe (e.g., 1h)"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type (e.g., BUY)"),
    limit: int = Query(50, description="Number of signals to return")
):
    """
    Get list of signals with optional filters
    
    Example:
        /api/signals?symbol=BTC/USDT&timeframe=1h&limit=10
    """
    
    # Build SQL query - ONLY SHOW SIGNALS FOR ACTIVE SYMBOLS
    query = """
        SELECT 
            s.id,
            s.symbol,
            s.timeframe,
            s.datetime,
            s.signal,
            s.score_total,
            s.max_score,
            s.tf_type,
            s.entry_price,
            s.stop_loss,
            s.target_price,
            s.current_price
        FROM signals s
        INNER JOIN tracked_symbols ts ON s.symbol = ts.symbol
        WHERE ts.active = TRUE
    """
    
    params = {}
    
    # Add filters if provided
    if symbol:
        query += " AND s.symbol = :symbol"
        params['symbol'] = symbol
    
    if timeframe:
        query += " AND s.timeframe = :timeframe"
        params['timeframe'] = timeframe
    
    if signal_type:
        query += " AND s.signal = :signal_type"
        params['signal_type'] = signal_type
    
    # Order by most recent first
    query += " ORDER BY s.datetime DESC LIMIT :limit"
    params['limit'] = limit
    
    # Execute query
    result = db.execute(text(query), params).fetchall()
    
    # Convert to list of dictionaries
    signals = []
    for row in result:
        signals.append({
            'id': row[0],
            'symbol': row[1],
            'timeframe': row[2],
            'datetime': row[3].isoformat() if row[3] else None,
            'signal': row[4],
            'score_total': float(row[5]) if row[5] else 0,
            'max_score': float(row[6]) if row[6] else 0,
            'tf_type': row[7],
            'entry_price': float(row[8]) if row[8] else None,
            'stop_loss': float(row[9]) if row[9] else None,
            'target_price': float(row[10]) if row[10] else None,
            'current_price': float(row[11]) if row[11] else None
        })
    
    return {
        'count': len(signals),
        'signals': signals
    }


@router.get("/stats")
async def get_signal_stats(db: Session = Depends(get_db)):
    """
    Get signal statistics
    
    Returns counts of each signal type
    """
    
    query = text("""
        SELECT 
            s.signal,
            COUNT(*) as count
        FROM signals s
        INNER JOIN tracked_symbols ts ON s.symbol = ts.symbol
        WHERE ts.active = TRUE
        GROUP BY s.signal
        ORDER BY count DESC
    """)
    
    result = db.execute(query).fetchall()
    
    stats = {}
    total = 0
    
    for row in result:
        signal_type = row[0]
        count = row[1]
        stats[signal_type] = count
        total += count
    
    return {
        'total_signals': total,
        'by_type': stats
    }
