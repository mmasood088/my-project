"""
Settings API Routes
Endpoints for system configuration and settings
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Optional
import sys
import os
from database import get_db
# Add path to access support_resistance module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from calculations.support_resistance import SupportResistanceCalculator
router = APIRouter(
    prefix="/api/settings",
    tags=["settings"]
)


# Pydantic models
class SystemSettings(BaseModel):
    # Signal thresholds
    a_buy_threshold: float = 28.0
    buy_threshold: float = 24.0
    early_buy_threshold: float = 18.0
    
    # Entry validation
    validation_profit_threshold: float = 1.0
    invalidation_loss_threshold: float = -1.0
    
    # Exit zones (multipliers)
    exit_1_multiplier: float = 0.3
    exit_2_multiplier: float = 0.6
    exit_3_multiplier: float = 1.0


@router.get("/system")
async def get_system_info(db: Session = Depends(get_db)):
    """
    Get system information and status
    """
    
    # Get automation status (check if cron job exists)
    import subprocess
    try:
        result = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
        automation_enabled = 'run_automation.py' in result.stdout
    except:
        automation_enabled = False
    
    # Get last automation run time (from latest signal)
    last_run_query = text("""
        SELECT MAX(datetime) as last_run
        FROM signals
    """)
    last_run = db.execute(last_run_query).fetchone()
    
    # Get database stats
    stats_query = text("""
        SELECT 
            (SELECT COUNT(*) FROM candles) as total_candles,
            (SELECT COUNT(*) FROM signals) as total_signals,
            (SELECT COUNT(*) FROM entry_tracking) as total_entries,
            (SELECT COUNT(*) FROM tracked_symbols WHERE active = TRUE) as active_symbols
    """)
    stats = db.execute(stats_query).fetchone()
    
    return {
        'automation': {
            'enabled': automation_enabled,
            'last_run': last_run[0].isoformat() if last_run[0] else None,
            'interval': '15 minutes'
        },
        'database': {
            'total_candles': stats[0] or 0,
            'total_signals': stats[1] or 0,
            'total_entries': stats[2] or 0,
            'active_symbols': stats[3] or 0
        },
        'api': {
            'version': '1.0.0',
            'status': 'running'
        }
    }


@router.get("/thresholds")
async def get_thresholds():
    """
    Get current signal and entry thresholds
    
    Note: These are currently hardcoded in signal_generator.py
    In a production system, these would be stored in a settings table
    """
    
    return {
        'signal_thresholds': {
            'a_buy': 28.0,
            'buy': 24.0,
            'early_buy': 18.0,
            'watch': 16.0,
            'caution': 12.0
        },
        'entry_validation': {
            'validation_profit': 1.0,  # % profit to validate
            'invalidation_loss': -1.0,  # % loss to invalidate
            'intraday_stop_multiplier': 1.2,
            'intraday_target_multiplier': 2.0,
            'swing_stop_multiplier': 2.0,
            'swing_target_multiplier': 4.0
        },
        'exit_zones': {
            'exit_1_pct': 30,  # 30% of target
            'exit_2_pct': 60,  # 60% of target
            'exit_3_pct': 100  # 100% of target (full target)
        },
        'note': 'Threshold updates require code changes. Future version will support database-backed settings.'
    }


@router.get("/logs")
async def get_recent_logs():
    """
    Get recent automation logs
    """
    
    import os
    
    log_file = '/home/ts/trading-dashboard/logs/automation.log'
    
    if not os.path.exists(log_file):
        return {
            'logs': 'No log file found. Automation may not have run yet.',
            'file': log_file
        }
    
    try:
        # Read last 50 lines
        with open(log_file, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines
        
        return {
            'logs': ''.join(recent_lines),
            'total_lines': len(lines),
            'showing_lines': len(recent_lines)
        }
    except Exception as e:
        return {
            'error': str(e),
            'file': log_file
        }
# ==================== SUPPORT/RESISTANCE SETTINGS ====================

class SRUpdateRequest(BaseModel):
    symbol: str
    mode: str  # "auto" or "manual"
    manual_support: Optional[float] = None
    manual_resistance: Optional[float] = None


@router.get("/support-resistance")
async def get_sr_settings(db: Session = Depends(get_db)):
    """
    Get Support/Resistance settings for all active symbols
    """
    
    query = text("""
        SELECT 
            ts.symbol,
            sr.manual_support,
            sr.manual_resistance,
            sr.auto_support,
            sr.auto_resistance,
            sr.effective_support,
            sr.effective_resistance,
            sr.auto_sr_enabled
        FROM tracked_symbols ts
        LEFT JOIN support_resistance sr ON ts.symbol = sr.symbol AND sr.timeframe = '1d'
        WHERE ts.active = TRUE
        ORDER BY ts.symbol
    """)
    
    result = db.execute(query).fetchall()
    
    settings = []
    for row in result:
        # Determine mode
        mode = "auto" if (row[6] and (row[1] == 0 or row[1] is None)) else "manual"
        
        settings.append({
            'symbol': row[0],
            'mode': mode,
            'manual_support': float(row[1]) if row[1] else 0.0,
            'manual_resistance': float(row[2]) if row[2] else 0.0,
            'auto_support': float(row[3]) if row[3] else 0.0,
            'auto_resistance': float(row[4]) if row[4] else 0.0,
            'effective_support': float(row[5]) if row[5] else 0.0,
            'effective_resistance': float(row[6]) if row[6] else 0.0
        })
    
    return {
        'count': len(settings),
        'settings': settings
    }


@router.put("/support-resistance")
async def update_sr_settings(
    request: SRUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update Support/Resistance settings for a symbol
    
    If mode = "auto": Sets manual values to 0, enables auto_sr
    If mode = "manual": Uses provided manual values, disables auto_sr
    """
    
    try:
        calc = SupportResistanceCalculator()
        
        # Get all timeframes for this symbol
        timeframes_query = text("""
            SELECT DISTINCT unnest(timeframes) as tf
            FROM tracked_symbols
            WHERE symbol = :symbol AND active = TRUE
        """)
        
        timeframes = db.execute(timeframes_query, {'symbol': request.symbol}).fetchall()
        
        if not timeframes:
            return {
                'success': False,
                'message': f'Symbol {request.symbol} not found or inactive'
            }
        
        # Update S/R for all timeframes
        for tf_row in timeframes:
            tf = tf_row[0]
            
            if request.mode == "auto":
                # Auto mode: manual = 0, auto enabled
                calc.update_sr(
                    symbol=request.symbol,
                    timeframe=tf,
                    manual_support=0.0,
                    manual_resistance=0.0,
                    auto_sr_mode='Enabled'
                )
            else:
                # Manual mode: use provided values, auto disabled
                calc.update_sr(
                    symbol=request.symbol,
                    timeframe=tf,
                    manual_support=request.manual_support or 0.0,
                    manual_resistance=request.manual_resistance or 0.0,
                    auto_sr_mode='Disabled'
                )
        
        return {
            'success': True,
            'message': f'Updated S/R for {request.symbol}',
            'mode': request.mode
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error updating S/R: {str(e)}'
        }


@router.post("/support-resistance/recalculate")
async def recalculate_all_sr(db: Session = Depends(get_db)):
    """
    Recalculate auto S/R for all active symbols
    """
    
    try:
        calc = SupportResistanceCalculator()
        
        # Get all active symbols
        symbols_query = text("""
            SELECT symbol, timeframes
            FROM tracked_symbols
            WHERE active = TRUE
        """)
        
        symbols = db.execute(symbols_query).fetchall()
        
        updated_count = 0
        for row in symbols:
            symbol = row[0]
            timeframes = row[1]
            
            for tf in timeframes:
                calc.update_sr(
                    symbol=symbol,
                    timeframe=tf,
                    manual_support=0.0,
                    manual_resistance=0.0,
                    auto_sr_mode='Enabled'
                )
                updated_count += 1
        
        return {
            'success': True,
            'message': f'Recalculated S/R for {len(symbols)} symbols',
            'updated_count': updated_count
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Error recalculating S/R: {str(e)}'
        }
# ==================== TIMEZONE SETTINGS ====================

from datetime import datetime
import pytz

@router.get("/timezones")
async def get_available_timezones():
    """
    Get list of available timezones for user selection
    """
    
    # Common trading timezones
    common_timezones = [
        {'value': 'UTC', 'label': 'UTC (Coordinated Universal Time)', 'offset': '+00:00'},
        {'value': 'Asia/Bahrain', 'label': 'Bahrain / Kuwait / Saudi Arabia (AST)', 'offset': '+03:00'},
        {'value': 'Asia/Dubai', 'label': 'Dubai / Abu Dhabi (GST)', 'offset': '+04:00'},
        {'value': 'Asia/Karachi', 'label': 'Pakistan / Karachi (PKT)', 'offset': '+05:00'},
        {'value': 'Asia/Kolkata', 'label': 'India (IST)', 'offset': '+05:30'},
        {'value': 'Asia/Singapore', 'label': 'Singapore (SGT)', 'offset': '+08:00'},
        {'value': 'Asia/Hong_Kong', 'label': 'Hong Kong (HKT)', 'offset': '+08:00'},
        {'value': 'Asia/Tokyo', 'label': 'Japan (JST)', 'offset': '+09:00'},
        {'value': 'Europe/London', 'label': 'London (GMT/BST)', 'offset': '+00:00/+01:00'},
        {'value': 'Europe/Paris', 'label': 'Paris / Frankfurt (CET)', 'offset': '+01:00'},
        {'value': 'America/New_York', 'label': 'New York (EST/EDT)', 'offset': '-05:00/-04:00'},
        {'value': 'America/Chicago', 'label': 'Chicago (CST/CDT)', 'offset': '-06:00/-05:00'},
        {'value': 'America/Los_Angeles', 'label': 'Los Angeles (PST/PDT)', 'offset': '-08:00/-07:00'},
    ]
    
    return {
        'timezones': common_timezones,
        'current_server_timezone': 'UTC',
        'note': 'Candles are stored in UTC. Times will be converted for display only.'
    }


@router.post("/timezone")
async def set_user_timezone(timezone: str):
    """
    Set user's preferred timezone
    
    Note: This is stored in browser localStorage, not in database
    """
    
    # Validate timezone
    try:
        pytz.timezone(timezone)
        return {
            'success': True,
            'timezone': timezone,
            'message': f'Timezone set to {timezone}'
        }
    except:
        return {
            'success': False,
            'message': 'Invalid timezone'
        }        