"""
Symbols API Routes
Endpoints for managing tracked symbols
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import List, Optional

from database import get_db
import subprocess
import threading
from pathlib import Path

router = APIRouter(
    prefix="/api/symbols",
    tags=["symbols"]
)


# Pydantic models for request/response
class SymbolCreate(BaseModel):
    symbol: str
    exchange: str = "binance"
    timeframes: List[str] = ["15m", "1h", "4h", "1d"]
    notes: Optional[str] = None


class SymbolUpdate(BaseModel):
    timeframes: Optional[List[str]] = None
    active: Optional[bool] = None
    notes: Optional[str] = None


@router.get("/")
async def get_symbols(
    db: Session = Depends(get_db),
    active_only: bool = True
):
    """
    Get list of tracked symbols
    """
    
    query = """
        SELECT 
            id,
            symbol,
            exchange,
            timeframes,
            active,
            added_by,
            added_at,
            updated_at,
            notes
        FROM tracked_symbols
    """
    
    params = {}
    
    if active_only:
        query += " WHERE active = TRUE"
    
    query += " ORDER BY symbol"
    
    result = db.execute(text(query), params).fetchall()
    
    symbols = []
    for row in result:
        symbols.append({
            'id': row[0],
            'symbol': row[1],
            'exchange': row[2],
            'timeframes': row[3],  # PostgreSQL array
            'active': row[4],
            'added_by': row[5],
            'added_at': row[6].isoformat() if row[6] else None,
            'updated_at': row[7].isoformat() if row[7] else None,
            'notes': row[8]
        })
    
    return {
        'count': len(symbols),
        'symbols': symbols
    }
def trigger_historical_download(symbol: str, exchange: str, timeframes: List[str]):
    """
    Trigger smart historical data download in background
    Uses smart_loader.py which checks if data exists first
    """
    try:
        # Path to the smart loader script
        backend_dir = Path(__file__).parent.parent.parent
        script_path = backend_dir / "automation" / "smart_loader.py"
        venv_python = backend_dir.parent / "venv" / "bin" / "python"
        
        # Run script in background
        subprocess.Popen(
            [
                str(venv_python), 
                str(script_path), 
                symbol,
                '--exchange', exchange,
                '--timeframes'] + timeframes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(backend_dir / "automation")
        )
        
        print(f"✓ Triggered smart loader for {symbol}")
    except Exception as e:
        print(f"✗ Failed to trigger smart loader: {e}")

@router.post("/")
async def add_symbol(
    symbol_data: SymbolCreate,
    db: Session = Depends(get_db)
):
    """
    Add a new symbol to track
    If symbol exists but is inactive, reactivate it
    Automatically triggers historical data download
    """
    
    # Check if symbol already exists (active or inactive)
    check_query = text("""
        SELECT id, active FROM tracked_symbols 
        WHERE symbol = :symbol AND exchange = :exchange
    """)
    
    existing = db.execute(check_query, {
        'symbol': symbol_data.symbol,
        'exchange': symbol_data.exchange
    }).fetchone()
    
    if existing:
        symbol_id = existing[0]
        is_active = existing[1]
        
        if is_active:
            # Symbol is already active
            raise HTTPException(
                status_code=400,
                detail=f"Symbol {symbol_data.symbol} on {symbol_data.exchange} is already active"
            )
        else:
            # Symbol exists but is inactive - REACTIVATE IT
            reactivate_query = text("""
                UPDATE tracked_symbols
                SET 
                    active = TRUE,
                    timeframes = :timeframes,
                    notes = :notes,
                    data_status = 'pending',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """)
            
            db.execute(reactivate_query, {
                'id': symbol_id,
                'timeframes': symbol_data.timeframes,
                'notes': symbol_data.notes
            })
            
            db.commit()
            
            # Trigger historical data check/download
            trigger_historical_download(
                symbol_data.symbol,
                symbol_data.exchange,
                symbol_data.timeframes
            )
            
            return {
                'success': True,
                'message': f'Symbol {symbol_data.symbol} reactivated successfully. Checking historical data...',
                'id': symbol_id,
                'status': 'reactivated',
                'action': 'checking_data'
            }
    
    # Symbol doesn't exist - create new
    insert_query = text("""
        INSERT INTO tracked_symbols 
            (symbol, exchange, timeframes, active, added_by, notes, data_status)
        VALUES 
            (:symbol, :exchange, :timeframes, TRUE, 'user', :notes, 'pending')
        RETURNING id
    """)
    
    result = db.execute(insert_query, {
        'symbol': symbol_data.symbol,
        'exchange': symbol_data.exchange,
        'timeframes': symbol_data.timeframes,
        'notes': symbol_data.notes
    })
    
    db.commit()
    
    new_id = result.fetchone()[0]
    
    # Trigger historical data download in background
    trigger_historical_download(
        symbol_data.symbol,
        symbol_data.exchange,
        symbol_data.timeframes
    )
    
    return {
        'success': True,
        'message': f'Symbol {symbol_data.symbol} added successfully. Historical data download started in background.',
        'id': new_id,
        'status': 'downloading'
    }


@router.put("/{symbol_id}")
async def update_symbol(
    symbol_id: int,
    symbol_data: SymbolUpdate,
    db: Session = Depends(get_db)
):
    """
    Update symbol configuration
    """
    
    # Check if symbol exists
    check_query = text("SELECT id FROM tracked_symbols WHERE id = :id")
    existing = db.execute(check_query, {'id': symbol_id}).fetchone()
    
    if not existing:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    # Build update query dynamically
    updates = []
    params = {'id': symbol_id}
    
    if symbol_data.timeframes is not None:
        updates.append("timeframes = :timeframes")
        params['timeframes'] = symbol_data.timeframes
    
    if symbol_data.active is not None:
        updates.append("active = :active")
        params['active'] = symbol_data.active
    
    if symbol_data.notes is not None:
        updates.append("notes = :notes")
        params['notes'] = symbol_data.notes
    
    if not updates:
        return {'success': True, 'message': 'No changes to update'}
    
    updates.append("updated_at = CURRENT_TIMESTAMP")
    
    update_query = text(f"""
        UPDATE tracked_symbols 
        SET {', '.join(updates)}
        WHERE id = :id
    """)
    
    db.execute(update_query, params)
    db.commit()
    
    return {
        'success': True,
        'message': 'Symbol updated successfully'
    }


@router.delete("/{symbol_id}")
async def delete_symbol(
    symbol_id: int,
    db: Session = Depends(get_db)
):
    """
    Delete (deactivate) a symbol
    
    Note: We don't actually delete, just set active = FALSE
    """
    
    query = text("""
        UPDATE tracked_symbols 
        SET active = FALSE, updated_at = CURRENT_TIMESTAMP
        WHERE id = :id
    """)
    
    result = db.execute(query, {'id': symbol_id})
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    return {
        'success': True,
        'message': 'Symbol deactivated successfully'
    }
@router.get("/{symbol_id}/status")
async def get_symbol_status(
    symbol_id: int,
    db: Session = Depends(get_db)
):
    """
    Get data download status for a symbol
    """
    
    query = text("""
        SELECT 
            symbol,
            data_status,
            data_download_started,
            data_download_completed
        FROM tracked_symbols
        WHERE id = :id
    """)
    
    result = db.execute(query, {'id': symbol_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    # Also check actual data in database
    candle_query = text("""
        SELECT 
            timeframe,
            COUNT(*) as count,
            MIN(datetime) as oldest,
            MAX(datetime) as newest
        FROM candles
        WHERE symbol = :symbol
        GROUP BY timeframe
        ORDER BY timeframe
    """)
    
    candle_result = db.execute(candle_query, {'symbol': result[0]}).fetchall()
    
    candles_info = []
    for row in candle_result:
        candles_info.append({
            'timeframe': row[0],
            'count': row[1],
            'oldest': row[2].isoformat() if row[2] else None,
            'newest': row[3].isoformat() if row[3] else None
        })
    
    return {
        'symbol': result[0],
        'status': result[1],
        'download_started': result[2].isoformat() if result[2] else None,
        'download_completed': result[3].isoformat() if result[3] else None,
        'candles': candles_info
    }

@router.post("/validate")
async def validate_symbol(
    symbol: str,
    exchange: str = "binance"
):
    """
    Validate if a symbol exists on the exchange
    
    For now, just basic validation
    In future, we'll actually check with exchange API
    """
    
    # Basic validation
    if not symbol or len(symbol) < 3:
        return {
            'valid': False,
            'message': 'Symbol too short'
        }
    
    if '/' not in symbol:
        return {
            'valid': False,
            'message': 'Symbol must be in format: BASE/QUOTE (e.g., BTC/USDT)'
        }
    
    # TODO: Add actual exchange validation
    # For now, assume valid
    return {
        'valid': True,
        'message': 'Symbol format is valid',
        'note': 'Full exchange validation not yet implemented'
    }