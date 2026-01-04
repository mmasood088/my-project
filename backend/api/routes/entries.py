"""
Entries API Routes
Endpoints for fetching entry tracking data
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from database import get_db

router = APIRouter(
    prefix="/api/entries",
    tags=["entries"]
)


@router.get("/")
async def get_entries(
    db: Session = Depends(get_db),
    active_only: bool = Query(True, description="Show only active entries"),
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    timeframe: Optional[str] = Query(None, description="Filter by timeframe"),
    limit: int = Query(50, description="Number of entries to return")
):
    """
    Get list of entries
    """
    
    query = """
        SELECT 
            e.id,
            e.symbol,
            e.timeframe,
            e.entry_signal,
            e.entry_datetime,
            e.entry_price,
            e.entry_score,
            e.stop_loss,
            e.target_price,
            e.validation_status,
            e.exit_status,
            e.current_price,
            e.current_profit_pct,
            e.max_profit_pct,
            e.peak_price,
            e.exit_1_hit,
            e.exit_2_hit,
            e.exit_3_hit,
            e.active
        FROM entry_tracking e
        INNER JOIN tracked_symbols ts ON e.symbol = ts.symbol
        WHERE ts.active = TRUE
    """
    
    params = {}
    
    if active_only:
        query += " AND e.active = TRUE"
    
    if symbol:
        query += " AND e.symbol = :symbol"
        params['symbol'] = symbol
    
    if timeframe:
        query += " AND e.timeframe = :timeframe"
        params['timeframe'] = timeframe
    query += " ORDER BY e.entry_datetime DESC LIMIT :limit"
    params['limit'] = limit
    
    result = db.execute(text(query), params).fetchall()
    
    entries = []
    for row in result:
        entries.append({
            'id': row[0],
            'symbol': row[1],
            'timeframe': row[2],
            'entry_signal': row[3],
            'entry_datetime': row[4].isoformat() if row[4] else None,
            'entry_price': float(row[5]) if row[5] else None,
            'entry_score': float(row[6]) if row[6] else None,
            'stop_loss': float(row[7]) if row[7] else None,
            'target_price': float(row[8]) if row[8] else None,
            'validation_status': row[9],
            'exit_status': row[10],
            'current_price': float(row[11]) if row[11] else None,
            'current_profit_pct': float(row[12]) if row[12] else 0,
            'max_profit_pct': float(row[13]) if row[13] else 0,
            'peak_price': float(row[14]) if row[14] else None,
            'exit_1_hit': row[15],
            'exit_2_hit': row[16],
            'exit_3_hit': row[17],
            'active': row[18]
        })
    
    return {
        'count': len(entries),
        'entries': entries
    }


@router.get("/stats")
async def get_entry_stats(db: Session = Depends(get_db)):
    """
    Get entry statistics
    """
    
    query = text("""
        SELECT 
            COUNT(*) FILTER (WHERE active = TRUE) as active_count,
            COUNT(*) FILTER (WHERE validation_status = 'VALIDATED') as validated_count,
            COUNT(*) FILTER (WHERE validation_status = 'INVALIDATED') as invalidated_count,
            AVG(current_profit_pct) FILTER (WHERE active = TRUE) as avg_profit,
            MAX(max_profit_pct) as max_profit,
            COUNT(*) FILTER (WHERE exit_status = 'EXITED') as exited_count
        FROM entry_tracking
    """)
    
    result = db.execute(query).fetchone()
    
    return {
        'active_entries': result[0] or 0,
        'validated': result[1] or 0,
        'invalidated': result[2] or 0,
        'avg_profit_pct': float(result[3]) if result[3] else 0.0,
        'max_profit_pct': float(result[4]) if result[4] else 0.0,
        'exited': result[5] or 0
    }