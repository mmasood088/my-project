"""
Signal Generator - Complete TradingView Scoring System
Matches Pine Script Dashboard Logic Exactly

Generates trading signals based on:
- All 11 technical indicators
- Support/Resistance levels
- Magic Line proximity
- Timeframe-aware scoring (Intraday vs Swing)

Signal Classification:
- A-BUY: Aggressive Buy (highest conviction)
- BUY: Standard Buy signal
- EARLY-BUY: Early entry opportunity (reversal setup)
- WATCH: Potential setup forming
- CAUTION: Weak/mixed signals
- SELL: Exit/avoid
"""

import pandas as pd
from sqlalchemy import text
from typing import Dict, Tuple, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import engine
from calculations.support_resistance import SupportResistanceCalculator
from calculations.magic_line import MagicLineManager

class SignalGenerator:
    """
    Generate trading signals using complete scoring system
    
    Matches your TradingView Pine Script exactly:
    - Timeframe classification (Intraday vs Swing)
    - Weighted scoring for each indicator
    - Price action bonuses (S/R, Magic Line)
    - Signal thresholds
    """
    
    def __init__(self):
        self.engine = engine
        self.sr_calc = SupportResistanceCalculator()
        self.ml_manager = MagicLineManager()
        
        # Load settings from database
        self.settings = self._load_settings()
    
    def _load_settings(self) -> Dict:
        """Load signal thresholds and settings from database"""
        try:
            with self.engine.connect() as conn:
                query = text("SELECT setting_key, setting_value FROM settings")
                result = conn.execute(query)
                
                settings = {}
                for row in result:
                    key = row[0]
                    value = row[1]
                    
                    # Convert to appropriate type
                    try:
                        settings[key] = float(value)
                    except:
                        settings[key] = value
                
                return settings
        
        except Exception as e:
            print(f"⚠️  Error loading settings: {e}")
            # Return defaults
            return {
                'auto_sr_mode': 'Enabled',
                'price_action_bonus_points': 2.0,
                'intraday_aggressive_buy_threshold': 29.0,
                'intraday_buy_threshold': 23.0,
                'intraday_early_buy_threshold': 18.0,
                'intraday_watch_threshold': 13.0,
                'intraday_caution_threshold': 9.0,
                'swing_aggressive_buy_threshold': 33.0,
                'swing_buy_threshold': 26.0,
                'swing_early_buy_threshold': 21.0,
                'swing_watch_threshold': 15.0,
                'swing_caution_threshold': 10.0
            }
    
    def classify_timeframe(self, timeframe: str) -> Tuple[str, float]:
        """
        Classify timeframe as Intraday or Swing
        
        Returns:
            (tf_type, max_score)
            - Intraday (<=4H): max 36 points
            - Swing (>4H): max 41 points
        """
        # Convert timeframe to minutes
        if timeframe.endswith('m'):
            minutes = int(timeframe[:-1])
        elif timeframe.endswith('h'):
            minutes = int(timeframe[:-1]) * 60
        elif timeframe.endswith('d') or timeframe == 'D':
            minutes = 24 * 60
        elif timeframe.endswith('W') or timeframe == 'W':
            minutes = 7 * 24 * 60
        else:
            minutes = 60  # Default to 1h
        
        if minutes <= 240:  # <= 4 hours
            return ('Intraday', 36.0)
        else:
            return ('Swing', 41.0)
    
    def fetch_indicator_data(self, symbol: str, timeframe: str) -> Optional[pd.Series]:
        """
        Fetch all indicator data for a symbol/timeframe
        
        Returns:
            pandas Series with all indicator values, or None if not found
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        c.id as candle_id,
                        c.symbol,
                        c.timeframe,
                        c.datetime,
                        c.close as current_price,
                        c.volume as current_volume,
                        i.id as indicator_id,
                        i.rsi,
                        i.rsi_ema,
                        i.macd_line,
                        i.macd_signal,
                        i.macd_histogram,
                        i.ema_44,
                        i.ema_100,
                        i.ema_200,
                        i.bb_basis,
                        i.bb_upper_1,
                        i.bb_lower_1,
                        i.bb_upper_2,
                        i.bb_lower_2,
                        i.bb_position,
                        i.bb_squeeze,
                        i.adx,
                        i.di_plus,
                        i.di_minus,
                        i.atr,
                        i.obv,
                        i.obv_ma,
                        i.vwap,
                        i.volume_avg,
                        i.volume_signal,
                        i.supertrend_1,
                        i.supertrend_1_direction,
                        i.supertrend_2,
                        i.supertrend_2_direction
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.symbol = :symbol
                    AND c.timeframe = :timeframe
                    ORDER BY c.datetime DESC
                    LIMIT 1
                """)
                
                result = conn.execute(query, {
                    'symbol': symbol,
                    'timeframe': timeframe
                }).fetchone()
                
                if result is None:
                    return None
                
                # Convert to Series
                data = pd.Series(dict(result._mapping))

                # Convert Decimal to float - be more aggressive
                for col in data.index:
                    if pd.notna(data[col]) and data[col] is not None:
                        try:
                            # Handle Decimal types explicitly
                            if hasattr(data[col], '__float__'):
                                data[col] = float(data[col])
                        except (ValueError, TypeError):
                            pass

                # Debug: Check key indicators
                print(f"  🔍 DEBUG: RSI raw value: {data.get('rsi')} (type: {type(data.get('rsi'))})")
                print(f"  🔍 DEBUG: MACD raw value: {data.get('macd_histogram')} (type: {type(data.get('macd_histogram'))})")

                if 'rsi' in data and data['rsi'] is not None:
                    print(f"  🔍 DEBUG: RSI before conversion: {data['rsi']}")
                    print(f"  🔍 DEBUG: Is NaN? {pd.isna(data['rsi'])}")

                return data
        
        except Exception as e:
            print(f"  ✗ Error fetching indicators for {symbol} {timeframe}: {e}")
            return None
    def fetch_indicator_data_by_id(self, candle_id: int) -> Optional[pd.Series]:
        """
        Fetch indicator data for a specific candle ID
        
        Args:
            candle_id: The candle ID to fetch
        
        Returns:
            pandas Series with all indicator values, or None if not found
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT 
                        c.id as candle_id,
                        c.symbol,
                        c.timeframe,
                        c.datetime,
                        c.close as current_price,
                        c.volume as current_volume,
                        i.id as indicator_id,
                        i.rsi,
                        i.rsi_ema,
                        i.macd_line,
                        i.macd_signal,
                        i.macd_histogram,
                        i.ema_44,
                        i.ema_100,
                        i.ema_200,
                        i.bb_basis,
                        i.bb_upper_1,
                        i.bb_lower_1,
                        i.bb_upper_2,
                        i.bb_lower_2,
                        i.bb_position,
                        i.bb_squeeze,
                        i.adx,
                        i.di_plus,
                        i.di_minus,
                        i.atr,
                        i.obv,
                        i.obv_ma,
                        i.vwap,
                        i.volume_avg,
                        i.volume_signal,
                        i.supertrend_1,
                        i.supertrend_1_direction,
                        i.supertrend_2,
                        i.supertrend_2_direction
                    FROM candles c
                    LEFT JOIN indicators i ON c.id = i.candle_id
                    WHERE c.id = :candle_id
                """)
                
                result = conn.execute(query, {'candle_id': candle_id}).fetchone()
                
                if result is None:
                    return None
                
                # Convert to Series
                data = pd.Series(dict(result._mapping))
                
                # Convert Decimal to float
                for col in data.index:
                    if pd.notna(data[col]) and data[col] is not None:
                        try:
                            if hasattr(data[col], '__float__'):
                                data[col] = float(data[col])
                        except (ValueError, TypeError):
                            pass
                
                return data
        
        except Exception as e:
            print(f"  ✗ Error fetching indicators for candle_id {candle_id}: {e}")
            return None
    def calculate_score_components(self, data: pd.Series, tf_type: str) -> Dict[str, float]:
        """
        Calculate individual score components
        
        This matches your Pine Script scoring exactly
        
        Returns:
            Dictionary with score breakdown
        """
        scores = {
            'rsi': 0.0,
            'macd': 0.0,
            'bb': 0.0,
            'ema_stack': 0.0,
            'supertrend': 0.0,
            'vwap': 0.0,
            'volume': 0.0,
            'adx': 0.0,
            'di': 0.0,
            'obv': 0.0
        }
        
        # RSI Score (0-4.5 points based on level and position)
        if pd.notna(data.get('rsi')):
            rsi = data['rsi']
            if rsi <= 30:
                scores['rsi'] = 4.5  # Oversold
            elif rsi <= 40:
                scores['rsi'] = 3.0
            elif rsi <= 50:
                scores['rsi'] = 2.0
            elif rsi <= 60:
                scores['rsi'] = 1.0
            # RSI > 60 = 0 points
        
        # MACD Score (0-5 points based on histogram position)
        if pd.notna(data.get('macd_histogram')):
            histogram = data['macd_histogram']
            macd_line = data.get('macd_line', 0)
            
            if histogram > 0:
                if macd_line > 0:
                    scores['macd'] = 5.0  # Bullish above zero
                else:
                    scores['macd'] = 3.5  # Bullish below zero
            # Histogram <= 0 = 0 points
        
        # Bollinger Bands Score (0-12 points based on position)
        # Simplified - you can enhance this with squeeze logic
        bb_pos = data.get('bb_position', 'BB~')
        if bb_pos == 'BB3↓':  # Extreme oversold
            scores['bb'] = 6.0
        elif bb_pos == 'BB2↓':  # Strong oversold
            scores['bb'] = 4.0
        elif bb_pos == 'BB1↓':  # Mild oversold
            scores['bb'] = 2.0
        
        # EMA Stack Score
        ema_44_up = data.get('ema_44', 0) < data.get('current_price', 0) if pd.notna(data.get('ema_44')) else False
        ema_100_up = data.get('ema_100', 0) < data.get('current_price', 0) if pd.notna(data.get('ema_100')) else False
        ema_200_up = data.get('ema_200', 0) < data.get('current_price', 0) if pd.notna(data.get('ema_200')) else False
        
        if tf_type == 'Intraday':
            # Intraday: EMA stack = 6 points max
            if ema_44_up:
                scores['ema_stack'] += 2.5
            if ema_100_up:
                scores['ema_stack'] += 2.0
            if ema_200_up:
                scores['ema_stack'] += 1.5
        else:  # Swing
            # Swing: EMA stack = 9 points max (weighted toward longer EMAs)
            if ema_200_up:
                scores['ema_stack'] += 5.0
            if ema_100_up:
                scores['ema_stack'] += 3.0
            if ema_44_up:
                scores['ema_stack'] += 1.0
        
        # SuperTrend Score
        st1_up = str(data.get('supertrend_1', '')).upper() == 'UP' if 'supertrend_1' in data else False
        st2_up = str(data.get('supertrend_2', '')).upper() == 'UP' if 'supertrend_2' in data else False
        
        # Check if current price > supertrend values (numeric comparison)
        if pd.notna(data.get('supertrend_1')) and pd.notna(data.get('current_price')):
            st1_up = data['current_price'] > data['supertrend_1']
        if pd.notna(data.get('supertrend_2')) and pd.notna(data.get('current_price')):
            st2_up = data['current_price'] > data['supertrend_2']
        
        if tf_type == 'Intraday':
            if st1_up:
                scores['supertrend'] += 2.5
            if st2_up:
                scores['supertrend'] += 2.5
        else:  # Swing
            if st2_up:
                scores['supertrend'] += 4.0
            if st1_up:
                scores['supertrend'] += 1.0
        
        # VWAP Score (2 points for price above VWAP + neutral zone)
        # Matches Pine Script: vwapNeutralZone = 0.5%
        if pd.notna(data.get('vwap')) and pd.notna(data.get('current_price')):
            vwap_neutral_zone = 0.005  # 0.5% neutral zone
            percent_diff = (data['current_price'] - data['vwap']) / data['vwap']
            
            if percent_diff > vwap_neutral_zone:
                # Price > VWAP + 0.5% → Bullish
                scores['vwap'] = 2.0
            elif percent_diff < -vwap_neutral_zone:
                # Price < VWAP - 0.5% → Bearish (no points)
                scores['vwap'] = 0.0
            else:
                # Price within ±0.5% of VWAP → Neutral (no points)
                scores['vwap'] = 0.0
        
        # Volume Score
        vol_signal = data.get('volume_signal', 'N')
        if tf_type == 'Intraday':
            if vol_signal == 'H':
                scores['volume'] = 2.0
            elif vol_signal == 'L':
                scores['volume'] = -1.5  # Penalty
        else:  # Swing
            if vol_signal == 'H':
                scores['volume'] = 2.0
            # No penalty for low volume in swing
        
        # ADX Score (1.5 points if ADX > 25 = strong trend)
        if pd.notna(data.get('adx')):
            if data['adx'] > 25:
                scores['adx'] = 1.5
        
        # DI Score (1 point if DI+ > DI-)
        if pd.notna(data.get('di_plus')) and pd.notna(data.get('di_minus')):
            if data['di_plus'] > data['di_minus']:
                scores['di'] = 1.0
        
        # OBV Score (1 point if OBV > OBV-MA)
        if pd.notna(data.get('obv')) and pd.notna(data.get('obv_ma')):
            if data['obv'] > data['obv_ma']:
                scores['obv'] = 1.0
        
        return scores
    def calculate_price_action_bonus(self, current_price: float, 
                                     support: float, resistance: float, 
                                     magic_line: Optional[float]) -> float:
        """
        Calculate price action bonus from S/R and Magic Line
        
        Matches Pine Script getPriceActionBonus() function
        
        Returns:
            Bonus points (0 to price_action_bonus_points)
        """
        bonus = 0.0
        max_bonus = self.settings.get('price_action_bonus_points', 2.0)
        
        # Breakout above resistance
        if resistance > 0 and current_price >= resistance * 1.005:
            bonus = max_bonus
        
        # Bounce from support
        elif support > 0 and current_price >= support and current_price <= support * 1.02:
            bonus = max_bonus * 0.8
        
        # Crossing above Magic Line
        elif magic_line and magic_line > 0:
            if current_price > magic_line and current_price <= magic_line * 1.02:
                bonus = max_bonus * 0.9
        
        return bonus
    
    def calculate_total_score(self, scores: Dict[str, float], 
                             price_action_bonus: float, 
                             tf_type: str) -> float:
        """
        Sum all score components
        
        Returns:
            Total score
        """
        total = sum(scores.values()) + price_action_bonus
        
        # Cap at max score
        max_score = 36.0 if tf_type == 'Intraday' else 41.0
        total = min(total, max_score)
        
        return total
    
    def classify_signal(self, score: float, tf_type: str, 
                       data: pd.Series) -> str:
        """
        Classify signal based on score and conditions
        
        Matches your Pine Script signal classification
        
        Returns:
            Signal string: 'A-BUY', 'BUY', 'EARLY-BUY', 'WATCH', 'CAUTION', 'SELL'
        """
        # Get thresholds
        if tf_type == 'Intraday':
            aggressive_buy = self.settings.get('intraday_aggressive_buy_threshold', 29.0)
            buy = self.settings.get('intraday_buy_threshold', 23.0)
            early_buy = self.settings.get('intraday_early_buy_threshold', 18.0)
            watch = self.settings.get('intraday_watch_threshold', 13.0)
            caution = self.settings.get('intraday_caution_threshold', 9.0)
        else:  # Swing
            aggressive_buy = self.settings.get('swing_aggressive_buy_threshold', 33.0)
            buy = self.settings.get('swing_buy_threshold', 26.0)
            early_buy = self.settings.get('swing_early_buy_threshold', 21.0)
            watch = self.settings.get('swing_watch_threshold', 15.0)
            caution = self.settings.get('swing_caution_threshold', 10.0)
        
        # Safety checks
        rsi = data.get('rsi', None)
        if rsi is None or pd.isna(rsi):
            rsi = 50  # Default to neutral if missing
        rsi_safe = rsi >= 30
        
        # Signal classification
        if score >= aggressive_buy and rsi_safe:
            return 'A-BUY'
        elif score >= buy and rsi_safe:
            return 'BUY'
        elif score >= early_buy:
            return 'EARLY-BUY'
        elif score >= watch:
            return 'WATCH'
        elif score >= caution:
            return 'CAUTION'
        else:
            return 'SELL'
    
    def generate_signal(self, symbol: str, timeframe: str, candle_id: Optional[int] = None) -> Optional[Dict]:
        """
        Generate complete signal for a symbol/timeframe
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            candle_id: Specific candle ID (optional, defaults to latest)
        
        Returns:
            Dictionary with signal data, or None if failed
        """
        try:
            # Fetch indicator data for specific candle or latest
            if candle_id:
                data = self.fetch_indicator_data_by_id(candle_id)
            else:
                data = self.fetch_indicator_data(symbol, timeframe)
            
            if data is None:
                print(f"  ⚠️  No indicator data for {symbol} {timeframe}" + (f" candle_id={candle_id}" if candle_id else ""))
                return None
            
            # Check if we have minimum required indicators
            if pd.isna(data.get('rsi')) or pd.isna(data.get('macd_histogram')):
                print(f"  ⚠️  Missing required indicators (RSI/MACD) for {symbol} {timeframe}")
                return None
            
            # Get symbol and timeframe from data
            symbol = data['symbol']
            timeframe = data['timeframe']
            
            # Classify timeframe
            tf_type, max_score = self.classify_timeframe(timeframe)
            
            # Get S/R levels
            auto_sr_mode = self.settings.get('auto_sr_mode', 'Enabled')
            sr = self.sr_calc.get_effective_sr(symbol, timeframe, auto_sr_mode)
            
            # Get Magic Line
            magic_line = self.ml_manager.get_magic_line(symbol)
            
            # Calculate score components
            scores = self.calculate_score_components(data, tf_type)
            
            # Calculate price action bonus
            current_price = data.get('current_price', 0)
            price_bonus = self.calculate_price_action_bonus(
                current_price, 
                sr['support'], 
                sr['resistance'], 
                magic_line
            )
            
            # Calculate total score
            total_score = self.calculate_total_score(scores, price_bonus, tf_type)
            
            # Classify signal
            signal = self.classify_signal(total_score, tf_type, data)
            
            # Calculate entry/stop/target
            atr = data.get('atr', 0)
            if signal in ['A-BUY', 'BUY', 'EARLY-BUY']:
                entry_price = current_price
                atr_mult = 1.2 if tf_type == 'Intraday' else 2.0
                target_mult = 2.0 if tf_type == 'Intraday' else 4.0
                stop_loss = current_price - (atr * atr_mult)
                target_price = current_price + (atr * target_mult)
            else:
                entry_price = None
                stop_loss = None
                target_price = None
            
            # Build result
            result = {
                'candle_id': int(data['candle_id']),
                'symbol': symbol,
                'timeframe': timeframe,
                'datetime': data['datetime'],
                'tf_type': tf_type,
                'max_score': max_score,
                'score_total': total_score,
                'score_rsi': scores['rsi'],
                'score_macd': scores['macd'],
                'score_bb': scores['bb'],
                'score_ema_stack': scores['ema_stack'],
                'score_supertrend': scores['supertrend'],
                'score_vwap': scores['vwap'],
                'score_volume': scores['volume'],
                'score_adx': scores['adx'],
                'score_di': scores['di'],
                'score_obv': scores['obv'],
                'score_price_action_bonus': price_bonus,
                'signal': signal,
                'entry_price': entry_price,
                'stop_loss': stop_loss,
                'target_price': target_price,
                'current_price': current_price,
                'support_level': sr['support'],
                'resistance_level': sr['resistance'],
                'magic_line_level': magic_line if magic_line else 0.0
            }
            
            return result
        
        except Exception as e:
            print(f"  ✗ Error generating signal for {symbol} {timeframe}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def store_signal(self, signal_data: Dict):
        """
        Store signal in database
        """
        try:
            with self.engine.connect() as conn:
                query = text("""
                    INSERT INTO signals (
                        candle_id, symbol, timeframe, datetime,
                        tf_type, max_score, score_total,
                        score_rsi, score_macd, score_bb, score_ema_stack, score_supertrend,
                        score_vwap, score_volume, score_adx, score_di, score_obv,
                        score_price_action_bonus,
                        signal, entry_price, stop_loss, target_price,
                        current_price, support_level, resistance_level, magic_line_level
                    ) VALUES (
                        :candle_id, :symbol, :timeframe, :datetime,
                        :tf_type, :max_score, :score_total,
                        :score_rsi, :score_macd, :score_bb, :score_ema_stack, :score_supertrend,
                        :score_vwap, :score_volume, :score_adx, :score_di, :score_obv,
                        :score_price_action_bonus,
                        :signal, :entry_price, :stop_loss, :target_price,
                        :current_price, :support_level, :resistance_level, :magic_line_level
                    )
                    ON CONFLICT (candle_id) 
                    DO UPDATE SET
                        symbol = EXCLUDED.symbol,
                        timeframe = EXCLUDED.timeframe,
                        datetime = EXCLUDED.datetime,
                        tf_type = EXCLUDED.tf_type,
                        max_score = EXCLUDED.max_score,
                        score_total = EXCLUDED.score_total,
                        score_rsi = EXCLUDED.score_rsi,
                        score_macd = EXCLUDED.score_macd,
                        score_bb = EXCLUDED.score_bb,
                        score_ema_stack = EXCLUDED.score_ema_stack,
                        score_supertrend = EXCLUDED.score_supertrend,
                        score_vwap = EXCLUDED.score_vwap,
                        score_volume = EXCLUDED.score_volume,
                        score_adx = EXCLUDED.score_adx,
                        score_di = EXCLUDED.score_di,
                        score_obv = EXCLUDED.score_obv,
                        score_price_action_bonus = EXCLUDED.score_price_action_bonus,
                        signal = EXCLUDED.signal,
                        entry_price = EXCLUDED.entry_price,
                        stop_loss = EXCLUDED.stop_loss,
                        target_price = EXCLUDED.target_price,
                        current_price = EXCLUDED.current_price,
                        support_level = EXCLUDED.support_level,
                        resistance_level = EXCLUDED.resistance_level,
                        magic_line_level = EXCLUDED.magic_line_level
                """)
                
                conn.execute(query, signal_data)
                conn.commit()
        
        except Exception as e:
            print(f"  ✗ Error storing signal: {e}")
            import traceback
            traceback.print_exc()
    
    def generate_signals_for_symbols(self, symbols: list, timeframes: list):
        """
        Generate signals for multiple symbols and timeframes
        """
        print("=" * 80)
        print("SIGNAL GENERATOR")
        print("=" * 80)
        
        total_generated = 0
        
        for symbol in symbols:
            print(f"\n{'─' * 80}")
            print(f"📊 {symbol}")
            print('─' * 80)
            
            for tf in timeframes:
                print(f"  {tf}...", end=' ')
                
                signal_data = self.generate_signal(symbol, tf)
                
                if signal_data:
                    self.store_signal(signal_data)
                    
                    score = signal_data['score_total']
                    max_score = signal_data['max_score']
                    signal = signal_data['signal']
                    
                    print(f"✓ {signal} ({score:.1f}/{max_score:.0f})")
                    total_generated += 1
                else:
                    print("✗ Failed")
        
        print("\n" + "=" * 80)
        print(f"✅ GENERATED {total_generated} SIGNALS")
        print("=" * 80)

# ============================================
# STANDALONE TEST SCRIPT
# ============================================

if __name__ == "__main__":
    print("=" * 80)
    print("SIGNAL GENERATOR TEST")
    print("=" * 80)
    
    generator = SignalGenerator()
    
    # Test symbols and timeframes
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['15m', '1h', '1d']
    
    # Generate signals
    generator.generate_signals_for_symbols(symbols, timeframes)
    
    print("\n💡 Verify in Navicat:")
    print("   SELECT symbol, timeframe, signal, score_total, max_score")
    print("   FROM signals ORDER BY symbol, timeframe;")
    print("\n💡 View detailed breakdown:")
    print("   SELECT * FROM signals WHERE symbol = 'BTC/USDT' AND timeframe = '1h';")