"""
Dashboard API Routes
Endpoints for dashboard statistics and overview
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from database import get_db

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"]
)


@router.get("/stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Get dashboard statistics
    FILTERED BY ACTIVE SYMBOLS ONLY
    """
    
    # Get active symbols
    active_symbols_query = text("""
        SELECT DISTINCT symbol 
        FROM tracked_symbols 
        WHERE active = TRUE
    """)
    active_symbols_result = db.execute(active_symbols_query)
    active_symbols = [row[0] for row in active_symbols_result.fetchall()]
    
    if not active_symbols:
        return {
            'active_entries': 0,
            'win_rate': 0.0,
            'avg_profit': 0.0,
            'signals_last_7_days': 0
        }
    
    # Build IN clause for SQL
    symbols_list = "'" + "','".join(active_symbols) + "'"
    
    # Active entries count (filtered by active symbols)
    active_entries_query = text(f"""
        SELECT COUNT(*) 
        FROM entry_tracking 
        WHERE active = TRUE
        AND symbol IN ({symbols_list})
    """)
    active_entries = db.execute(active_entries_query).scalar()
    
    # Win rate calculation (filtered by active symbols)
    entry_stats_query = text(f"""
        SELECT 
            COUNT(*) FILTER (WHERE validation_status = 'VALIDATED') as validated,
            COUNT(*) FILTER (WHERE validation_status = 'INVALIDATED') as invalidated
        FROM entry_tracking
        WHERE validation_status IN ('VALIDATED', 'INVALIDATED')
        AND symbol IN ({symbols_list})
    """)
    entry_stats = db.execute(entry_stats_query).fetchone()
    
    validated = entry_stats[0] or 0
    invalidated = entry_stats[1] or 0
    total_validated = validated + invalidated
    win_rate = (validated / total_validated * 100) if total_validated > 0 else 0.0
    
    # Average profit (filtered by active symbols)
    avg_profit_query = text(f"""
        SELECT AVG(current_profit_pct)
        FROM entry_tracking
        WHERE validation_status = 'VALIDATED'
        AND symbol IN ({symbols_list})
    """)
    avg_profit = db.execute(avg_profit_query).scalar() or 0.0
    
    # Signals in last 7 days (filtered by active symbols)
    signals_query = text(f"""
        SELECT COUNT(*)
        FROM signals
        WHERE datetime >= CURRENT_DATE - INTERVAL '7 days'
        AND symbol IN ({symbols_list})
    """)
    signals_count = db.execute(signals_query).scalar()
    
    return {
        'active_entries': active_entries,
        'win_rate': round(win_rate, 2),
        'avg_profit': round(avg_profit, 2),
        'signals_last_7_days': signals_count
    }


@router.get("/recent-activity")
async def get_recent_activity(db: Session = Depends(get_db)):
    """
    Get recent signals and entries
    """
    
    # Recent signals
    signal_query = text("""
        SELECT 
            symbol,
            timeframe,
            signal,
            datetime,
            score_total
        FROM signals
        ORDER BY datetime DESC
        LIMIT 10
    """)
    
    signals = db.execute(signal_query).fetchall()
    
    # Recent entries
    entry_query = text("""
        SELECT 
            symbol,
            timeframe,
            entry_signal,
            entry_datetime,
            validation_status,
            current_profit_pct
        FROM entry_tracking
        WHERE active = TRUE
        ORDER BY entry_datetime DESC
        LIMIT 10
    """)
    
    entries = db.execute(entry_query).fetchall()
    
    return {
        'recent_signals': [
            {
                'symbol': row[0],
                'timeframe': row[1],
                'signal': row[2],
                'datetime': row[3].isoformat() if row[3] else None,
                'score': float(row[4]) if row[4] else 0
            }
            for row in signals
        ],
        'recent_entries': [
            {
                'symbol': row[0],
                'timeframe': row[1],
                'entry_signal': row[2],
                'entry_datetime': row[3].isoformat() if row[3] else None,
                'status': row[4],
                'profit_pct': float(row[5]) if row[5] else 0
            }
            for row in entries
        ]
    }


@router.get("/table")
async def get_dashboard_table(db: Session = Depends(get_db)):
    """
    Get comprehensive dashboard table data
    Returns all indicators + signals + entries for active symbols
    OPTIMIZED: Fetch all live prices at once
    """
    
    # Get active symbols
    active_symbols_query = text("""
        SELECT symbol, timeframes, exchange, added_by
        FROM tracked_symbols 
        WHERE active = TRUE
        ORDER BY symbol
    """)
    active_symbols_result = db.execute(active_symbols_query)
    active_symbols_rows = active_symbols_result.fetchall()
    
    if not active_symbols_rows:
        return {'rows': [], 'count': 0}
    
    # Initialize price fetcher
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../automation'))
    from price_fetcher import PriceFetcher
    
    price_fetcher = PriceFetcher()
    
    # OPTIMIZATION: Fetch ALL live prices at once (not in loop!)
    all_symbols = [row[0] for row in active_symbols_rows]
    live_prices_data = price_fetcher.get_live_prices(all_symbols)
    
    # Build results
    table_rows = []
    
    for symbol_row in active_symbols_rows:
        symbol = symbol_row[0]
        timeframes = symbol_row[1]  # Array of timeframes
        
        # Get live price from pre-fetched data
        live_price = live_prices_data.get(symbol, {}).get('price', 0.0)
        
        # Get magic line for this symbol
        magic_line_query = text("""
            SELECT magic_line_price 
            FROM magic_lines 
            WHERE symbol = :symbol 
            ORDER BY updated_at DESC 
            LIMIT 1
        """)
        magic_line_result = db.execute(magic_line_query, {'symbol': symbol}).fetchone()
        magic_line = float(magic_line_result[0]) if magic_line_result else None
        
        # Get support/resistance for this symbol
        sr_query = text("""
            SELECT effective_support, effective_resistance 
            FROM support_resistance 
            WHERE symbol = :symbol 
            ORDER BY updated_at DESC 
            LIMIT 1
        """)
        sr_result = db.execute(sr_query, {'symbol': symbol}).fetchone()
        support = float(sr_result[0]) if sr_result and sr_result[0] else None
        resistance = float(sr_result[1]) if sr_result and sr_result[1] else None
        
        # For each timeframe
        for timeframe in timeframes:
            # Get latest candle with indicators
            candle_query = text("""
                SELECT 
                    c.id, c.datetime, c.open, c.high, c.low, c.close, c.volume,
                    i.rsi, i.rsi_ema, i.macd_line, i.macd_signal, i.macd_histogram,
                    i.adx, i.di_plus, i.di_minus, i.obv, i.obv_ma,
                    i.ema_44, i.ema_100, i.ema_200,
                    i.supertrend_1_direction, i.supertrend_2_direction,
                    i.bb_position, i.bb_squeeze,
                    i.vwap, i.atr, i.volume_avg, i.volume_signal
                FROM candles c
                LEFT JOIN indicators i ON c.id = i.candle_id
                WHERE c.symbol = :symbol 
                AND c.timeframe = :timeframe
                ORDER BY c.datetime DESC
                LIMIT 1
            """)
            candle_result = db.execute(candle_query, {
                'symbol': symbol,
                'timeframe': timeframe
            }).fetchone()
            
            if not candle_result:
                continue
            
            # Get latest signal
            signal_query = text("""
                SELECT signal, score_total, entry_price
                FROM signals
                WHERE symbol = :symbol
                AND timeframe = :timeframe
                ORDER BY datetime DESC
                LIMIT 1
            """)
            signal_result = db.execute(signal_query, {
                'symbol': symbol,
                'timeframe': timeframe
            }).fetchone()
            
            signal_type = signal_result[0] if signal_result else None
            signal_score = float(signal_result[1]) if signal_result and signal_result[1] else 0.0
            signal_entry = float(signal_result[2]) if signal_result and signal_result[2] else None
            
            # Get active entry (if exists)
            entry_query = text("""
                SELECT 
                    entry_price, validation_status, exit_status, 
                    exit_reason, current_profit_pct
                FROM entry_tracking
                WHERE symbol = :symbol
                AND timeframe = :timeframe
                AND active = TRUE
                ORDER BY entry_datetime DESC
                LIMIT 1
            """)
            entry_result = db.execute(entry_query, {
                'symbol': symbol,
                'timeframe': timeframe
            }).fetchone()
            
            entry_price = float(entry_result[0]) if entry_result else None
            entry_status = entry_result[1] if entry_result else None
            exit_status = entry_result[2] if entry_result else None
            exit_reason = entry_result[3] if entry_result else None
            current_profit = float(entry_result[4]) if entry_result and entry_result[4] else 0.0
            
            # Determine timeframe type
            tf_minutes = 0
            if timeframe == '15m':
                tf_minutes = 15
            elif timeframe == '1h':
                tf_minutes = 60
            elif timeframe == '4h':
                tf_minutes = 240
            elif timeframe == '1d':
                tf_minutes = 1440
            
            tf_type = "Intraday" if tf_minutes <= 240 else "Swing"
            
            # Calculate RSI crossover signal
            rsi_val = float(candle_result[7]) if candle_result[7] else 0.0
            rsi_ema = float(candle_result[8]) if candle_result[8] else 0.0
            rsi_cross = "↑" if rsi_val > rsi_ema else "↓"
            
            # Calculate MACD crossover signal
            macd_hist = float(candle_result[11]) if candle_result[11] else 0.0
            macd_cross = "↑" if macd_hist > 0 else "↓"
            
            # EMA Stack
            close_price = float(candle_result[5])
            ema_44 = float(candle_result[16]) if candle_result[16] else 0.0
            ema_100 = float(candle_result[17]) if candle_result[17] else 0.0
            ema_200 = float(candle_result[18]) if candle_result[18] else 0.0
            
            ema_44_status = "↑" if close_price > ema_44 else "↓"
            ema_100_status = "↑" if close_price > ema_100 else "↓"
            ema_200_status = "↑" if close_price > ema_200 else "↓"
            ema_stack = f"{ema_44_status}{ema_100_status}{ema_200_status}"
            
            # DI Status
            di_plus = float(candle_result[13]) if candle_result[13] else 0.0
            di_minus = float(candle_result[14]) if candle_result[14] else 0.0
            di_status = "+" if di_plus > di_minus else "-"
            
            # OBV Signal
            obv = float(candle_result[15]) if candle_result[15] else 0.0
            obv_ma = float(candle_result[16]) if candle_result[16] else 0.0
            obv_signal = "+" if obv > obv_ma else "-"
            
            # VWAP Signal
            vwap = float(candle_result[23]) if candle_result[23] else 0.0
            vwap_signal = "+" if live_price > vwap else "-" if live_price < vwap else "~"
            
            # ATR %
            atr = float(candle_result[25]) if candle_result[25] else 0.0
            candle_close = float(candle_result[5]) if candle_result[5] else 0.0
            atr_pct = (atr / candle_close * 100) if candle_close > 0 else 0.0
            print(f"DEBUG: atr={atr}, candle_close={candle_close}, atr_pct={atr_pct}")
            
            # SuperTrend values - convert to string for comparison
            st1_val = str(candle_result[19]) if candle_result[19] else ""
            st2_val = str(candle_result[20]) if candle_result[20] else ""
            
            # Build row
            row = {
                'symbol': symbol,
                'timeframe': timeframe,
                'tf_type': tf_type,
                'current_price': live_price,
                'support': support,
                'resistance': resistance,
                'magic_line': magic_line,
                'vwap': vwap_signal,
                'volume': candle_result[27] if candle_result[27] else "N",  # volume_signal (H/N/L)
                'atr_pct': round(atr_pct, 2),
                'rsi': round(rsi_val, 1),
                'rsi_cross': rsi_cross,
                'macd': "+" if macd_hist > 0 else "-",
                'macd_cross': macd_cross,
                'adx': round(float(candle_result[12]) if candle_result[12] else 0.0, 1),
                'di': di_status,
                'obv': obv_signal,
                'ema_stack': ema_stack,
                'st1': "UP" if st1_val == "1" else "DOWN" if st1_val == "-1" else "─",
                'st2': "UP" if st2_val == "1" else "DOWN" if st2_val == "-1" else "─",
                'bb_position': candle_result[21] if candle_result[21] else "N/A",
                'bb_squeeze': candle_result[22] if candle_result[22] else False,
                'score': signal_score,
                'signal': signal_type,
                'entry_status': entry_status or exit_status or "─",
                'exit_reason': exit_reason or "─",
                'entry_price': entry_price,
                'current_profit': current_profit
            }
            
            table_rows.append(row)
    
    return {
        'rows': table_rows,
        'count': len(table_rows)
    }