"""
Improved Trading Strategies with Dynamic SL/TP
===============================================
Enhanced versions of 6 trading strategies with intelligent risk management
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from indicators import TechnicalIndicators as TI
from market_analyzer import MarketAnalyzer


class ImprovedTradingStrategies:
    """Enhanced trading strategies with dynamic SL/TP calculation"""
    
    def __init__(self):
        self.ti = TI()
        self.market_analyzer = MarketAnalyzer()
    
    def strategy_1_trend_following(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame, 
                                  symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 1: Improved Trend Following
        - Dynamic ATR multipliers based on trend strength
        - Structure-aware SL placement
        - Session-adjusted parameters
        """
        try:
            # M5 indicators
            ema9 = self.ti.ema(df_m5['close'], 9)
            ema21 = self.ti.ema(df_m5['close'], 21)
            macd_line, signal_line, histogram = self.ti.macd(df_m5['close'])
            volume_sma = df_m5['tick_volume'].rolling(20).mean()
            atr = self.ti.atr(df_m5, 14)
            
            # H1 trend
            ema50_h1 = self.ti.ema(df_h1['close'], 50)
            ema200_h1 = self.ti.ema(df_h1['close'], 200)
            
            # Current values
            curr_ema9 = ema9.iloc[-1]
            prev_ema9 = ema9.iloc[-2]
            curr_ema21 = ema21.iloc[-1]
            prev_ema21 = ema21.iloc[-2]
            curr_macd = macd_line.iloc[-1]
            curr_signal = signal_line.iloc[-1]
            curr_volume = df_m5['tick_volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            curr_atr = atr.iloc[-1]
            curr_price = df_m5['close'].iloc[-1]
            
            h1_trend = 'bullish' if ema50_h1.iloc[-1] > ema200_h1.iloc[-1] else 'bearish'
            volume_confirmed = curr_volume > avg_volume * 1.15
            
            action = None
            confidence = 0
            
            # BUY Signal
            if (prev_ema9 <= prev_ema21 and curr_ema9 > curr_ema21 and
                curr_macd > curr_signal and h1_trend == 'bullish'):
                action = 'BUY'
                confidence = 65
                
                if volume_confirmed:
                    confidence += 10
                if curr_macd > 0:
                    confidence += 5
                if (curr_ema9 - curr_ema21) / curr_ema21 > 0.0005:
                    confidence += 5
            
            # SELL Signal
            elif (prev_ema9 >= prev_ema21 and curr_ema9 < curr_ema21 and
                  curr_macd < curr_signal and h1_trend == 'bearish'):
                action = 'SELL'
                confidence = 65
                
                if volume_confirmed:
                    confidence += 10
                if curr_macd < 0:
                    confidence += 5
                if (curr_ema21 - curr_ema9) / curr_ema21 > 0.0005:
                    confidence += 5
            
            if action:
                # Get pip size
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # Calculate structure-based SL/TP
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'trend'
                )
                
                # Check if trailing stop should be used
                use_trailing = self.market_analyzer.should_use_trailing_stop('trend', confidence)
                trailing_distance = None
                if use_trailing:
                    trailing_distance = self.market_analyzer.calculate_trailing_stop_distance(
                        curr_atr, pip_size, 'trend'
                    )
                
                return action, confidence, {
                    'strategy': 'TREND_FOLLOWING',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': use_trailing,
                    'trailing_distance_pips': trailing_distance,
                    'reason': f'EMA crossover + MACD + H1 {h1_trend} (Dynamic SL/TP)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'TREND_FOLLOWING', 'reason': 'No crossover'}
        
        except Exception as e:
            return None, 0, {'strategy': 'TREND_FOLLOWING', 'error': str(e)}
    
    def strategy_2_fibonacci_retracement(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame,
                                        symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 2: Improved Fibonacci Retracement
        - Better R:R for mean reversion characteristics
        - Structure-aware TP placement
        """
        try:
            fib_levels = self.ti.fibonacci_retracement(df_m5, 50)
            rsi = self.ti.rsi(df_m5['close'], 14)
            atr = self.ti.atr(df_m5, 14)
            
            ema50_h1 = self.ti.ema(df_h1['close'], 50)
            ema200_h1 = self.ti.ema(df_h1['close'], 200)
            h1_trend = 'bullish' if ema50_h1.iloc[-1] > ema200_h1.iloc[-1] else 'bearish'
            
            curr_price = df_m5['close'].iloc[-1]
            curr_rsi = rsi.iloc[-1]
            curr_atr = atr.iloc[-1]
            
            fib_618 = fib_levels['fib_618']
            fib_500 = fib_levels['fib_500']
            
            action = None
            confidence = 0
            
            # BUY at retracement in uptrend
            if h1_trend == 'bullish':
                distance_to_618 = abs(curr_price - fib_618) / curr_price
                distance_to_500 = abs(curr_price - fib_500) / curr_price
                
                if (distance_to_618 < 0.0015 or distance_to_500 < 0.0015) and 40 < curr_rsi < 60:
                    action = 'BUY'
                    confidence = 60
                    
                    if distance_to_618 < 0.001:
                        confidence += 10
                    if 45 < curr_rsi < 55:
                        confidence += 8
            
            # SELL at retracement in downtrend
            elif h1_trend == 'bearish':
                fib_382 = fib_levels['fib_382']
                distance_to_382 = abs(curr_price - fib_382) / curr_price
                distance_to_500 = abs(curr_price - fib_500) / curr_price
                
                if (distance_to_382 < 0.0015 or distance_to_500 < 0.0015) and 40 < curr_rsi < 60:
                    action = 'SELL'
                    confidence = 60
                    
                    if distance_to_382 < 0.001:
                        confidence += 10
                    if 45 < curr_rsi < 55:
                        confidence += 8
            
            if action:
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # Fibonacci retracement is a trend continuation strategy
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'trend'
                )
                
                return action, confidence, {
                    'strategy': 'FIBONACCI_RETRACEMENT',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': False,
                    'trailing_distance_pips': None,
                    'reason': f'Fib retracement in {h1_trend} trend (Dynamic SL/TP)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'FIBONACCI_RETRACEMENT', 'reason': 'Not at Fib level'}
        
        except Exception as e:
            return None, 0, {'strategy': 'FIBONACCI_RETRACEMENT', 'error': str(e)}
    
    def strategy_3_mean_reversion(self, df_m5: pd.DataFrame, symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 3: Improved Mean Reversion
        - Tighter R:R for quick reversals
        - Session-aware parameters
        """
        try:
            bb_upper, bb_middle, bb_lower = self.ti.bollinger_bands(df_m5['close'], 20, 2.0)
            rsi = self.ti.rsi(df_m5['close'], 14)
            stoch_k, stoch_d = self.ti.stochastic(df_m5, 14, 3)
            atr = self.ti.atr(df_m5, 14)
            
            curr_price = df_m5['close'].iloc[-1]
            curr_bb_upper = bb_upper.iloc[-1]
            curr_bb_lower = bb_lower.iloc[-1]
            curr_rsi = rsi.iloc[-1]
            curr_stoch_k = stoch_k.iloc[-1]
            curr_atr = atr.iloc[-1]
            
            action = None
            confidence = 0
            
            # BUY at lower band (oversold)
            if curr_price <= curr_bb_lower and curr_rsi < 35 and curr_stoch_k < 25:
                action = 'BUY'
                confidence = 60
                
                if curr_rsi < 25:
                    confidence += 10
                if curr_stoch_k < 15:
                    confidence += 8
            
            # SELL at upper band (overbought)
            elif curr_price >= curr_bb_upper and curr_rsi > 65 and curr_stoch_k > 75:
                action = 'SELL'
                confidence = 60
                
                if curr_rsi > 75:
                    confidence += 10
                if curr_stoch_k > 85:
                    confidence += 8
            
            if action:
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # Mean reversion needs tighter SL/TP
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'reversion'
                )
                
                return action, confidence, {
                    'strategy': 'MEAN_REVERSION',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': False,
                    'trailing_distance_pips': None,
                    'reason': f'BB + RSI + Stochastic {action.lower()} (Dynamic SL/TP)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'MEAN_REVERSION', 'reason': 'Not at extremes'}
        
        except Exception as e:
            return None, 0, {'strategy': 'MEAN_REVERSION', 'error': str(e)}
    
    def strategy_4_breakout(self, df_m5: pd.DataFrame, df_h1: pd.DataFrame,
                           symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 4: Improved Breakout
        - Trailing stops for extended moves
        - Better volatility adjustment
        """
        try:
            pivots = self.ti.pivot_points(df_m5)
            sar = self.ti.parabolic_sar(df_m5)
            volume_sma = df_m5['tick_volume'].rolling(20).mean()
            atr = self.ti.atr(df_m5, 14)
            
            curr_price = df_m5['close'].iloc[-1]
            prev_price = df_m5['close'].iloc[-2]
            curr_sar = sar.iloc[-1]
            curr_volume = df_m5['tick_volume'].iloc[-1]
            avg_volume = volume_sma.iloc[-1]
            curr_atr = atr.iloc[-1]
            
            volume_spike = curr_volume > avg_volume * 1.5
            
            action = None
            confidence = 0
            
            # BUY on upward breakout
            if (prev_price <= pivots['r1'] and curr_price > pivots['r1'] and
                curr_price > curr_sar and volume_spike):
                action = 'BUY'
                confidence = 62
                
                if curr_volume > avg_volume * 2.0:
                    confidence += 10
                if curr_price > pivots['r2']:
                    confidence += 5
            
            # SELL on downward breakout
            elif (prev_price >= pivots['s1'] and curr_price < pivots['s1'] and
                  curr_price < curr_sar and volume_spike):
                action = 'SELL'
                confidence = 62
                
                if curr_volume > avg_volume * 2.0:
                    confidence += 10
                if curr_price < pivots['s2']:
                    confidence += 5
            
            if action:
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # Breakout strategy with trailing stops
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'breakout'
                )
                
                # Always use trailing stops for breakouts
                trailing_distance = self.market_analyzer.calculate_trailing_stop_distance(
                    curr_atr, pip_size, 'breakout'
                )
                
                return action, confidence, {
                    'strategy': 'BREAKOUT',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': True,
                    'trailing_distance_pips': trailing_distance,
                    'reason': f'Pivot breakout + volume spike (Trailing Stop)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'BREAKOUT', 'reason': 'No breakout'}
        
        except Exception as e:
            return None, 0, {'strategy': 'BREAKOUT', 'error': str(e)}
    
    def strategy_5_momentum(self, df_m5: pd.DataFrame, symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 5: Improved Momentum
        - Quick scalping with tight parameters
        - Session-adjusted volatility
        """
        try:
            stoch_k, stoch_d = self.ti.stochastic(df_m5, 14, 3)
            cci = self.ti.cci(df_m5, 20)
            williams_r = self.ti.williams_r(df_m5, 14)
            atr = self.ti.atr(df_m5, 14)
            
            curr_stoch_k = stoch_k.iloc[-1]
            curr_cci = cci.iloc[-1]
            curr_williams = williams_r.iloc[-1]
            curr_atr = atr.iloc[-1]
            curr_price = df_m5['close'].iloc[-1]
            
            action = None
            confidence = 0
            
            # BUY on oversold momentum
            if curr_stoch_k < 20 and curr_cci < -100 and curr_williams < -80:
                action = 'BUY'
                confidence = 58
                
                if curr_stoch_k < 10:
                    confidence += 8
                if curr_cci < -150:
                    confidence += 7
                if curr_williams < -90:
                    confidence += 7
            
            # SELL on overbought momentum
            elif curr_stoch_k > 80 and curr_cci > 100 and curr_williams > -20:
                action = 'SELL'
                confidence = 58
                
                if curr_stoch_k > 90:
                    confidence += 8
                if curr_cci > 150:
                    confidence += 7
                if curr_williams > -10:
                    confidence += 7
            
            if action:
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # Momentum scalping with tight parameters
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'momentum'
                )
                
                return action, confidence, {
                    'strategy': 'MOMENTUM',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': False,
                    'trailing_distance_pips': None,
                    'reason': f'Multi-momentum {action.lower()} (Quick Scalp)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'MOMENTUM', 'reason': 'No momentum extreme'}
        
        except Exception as e:
            return None, 0, {'strategy': 'MOMENTUM', 'error': str(e)}
    
    def strategy_6_multi_timeframe_confluence(self, df_m5: pd.DataFrame, df_m15: pd.DataFrame, 
                                              df_h1: pd.DataFrame, df_h4: pd.DataFrame,
                                              symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Strategy 6: Improved Multi-Timeframe Confluence
        - Wider parameters for high confidence signals
        - Trailing stops for strong trends
        """
        try:
            # M5
            ema9_m5 = self.ti.ema(df_m5['close'], 9)
            ema21_m5 = self.ti.ema(df_m5['close'], 21)
            rsi_m5 = self.ti.rsi(df_m5['close'], 14)
            
            # M15
            ema9_m15 = self.ti.ema(df_m15['close'], 9)
            ema21_m15 = self.ti.ema(df_m15['close'], 21)
            
            # H1
            ema50_h1 = self.ti.ema(df_h1['close'], 50)
            ema200_h1 = self.ti.ema(df_h1['close'], 200)
            
            # H4
            ema50_h4 = self.ti.ema(df_h4['close'], 50)
            ema200_h4 = self.ti.ema(df_h4['close'], 200)
            
            atr_m5 = self.ti.atr(df_m5, 14)
            curr_price = df_m5['close'].iloc[-1]
            
            # Check alignment
            m5_bullish = ema9_m5.iloc[-1] > ema21_m5.iloc[-1] and rsi_m5.iloc[-1] > 50
            m15_bullish = ema9_m15.iloc[-1] > ema21_m15.iloc[-1]
            h1_bullish = ema50_h1.iloc[-1] > ema200_h1.iloc[-1]
            h4_bullish = ema50_h4.iloc[-1] > ema200_h4.iloc[-1]
            
            m5_bearish = ema9_m5.iloc[-1] < ema21_m5.iloc[-1] and rsi_m5.iloc[-1] < 50
            m15_bearish = ema9_m15.iloc[-1] < ema21_m15.iloc[-1]
            h1_bearish = ema50_h1.iloc[-1] < ema200_h1.iloc[-1]
            h4_bearish = ema50_h4.iloc[-1] < ema200_h4.iloc[-1]
            
            action = None
            confidence = 0
            
            # BUY on full bullish alignment
            if m5_bullish and m15_bullish and h1_bullish and h4_bullish:
                action = 'BUY'
                confidence = 80  # High confidence!
                
                if rsi_m5.iloc[-1] > 55:
                    confidence += 5
            
            # SELL on full bearish alignment
            elif m5_bearish and m15_bearish and h1_bearish and h4_bearish:
                action = 'SELL'
                confidence = 80  # High confidence!
                
                if rsi_m5.iloc[-1] < 45:
                    confidence += 5
            
            if action:
                curr_atr = atr_m5.iloc[-1]
                pip_size = self.market_analyzer.get_symbol_pip_size(symbol, curr_price)
                
                # High confidence = wider parameters + trailing stops
                sl_pips, tp_pips = self.market_analyzer.calculate_structure_based_sl_tp(
                    df_m5, action, curr_price, curr_atr, pip_size, 'confluence'
                )
                
                # Use trailing stops for high confidence signals
                trailing_distance = self.market_analyzer.calculate_trailing_stop_distance(
                    curr_atr, pip_size, 'trend'
                )
                
                return action, confidence, {
                    'strategy': 'MULTI_TIMEFRAME_CONFLUENCE',
                    'sl_pips': sl_pips,
                    'tp_pips': tp_pips,
                    'use_trailing_stop': True,
                    'trailing_distance_pips': trailing_distance,
                    'reason': 'All timeframes aligned (High Confidence + Trailing)',
                    'market_structure': self.market_analyzer.analyze_market_structure(df_m5)
                }
            
            return None, 0, {'strategy': 'MULTI_TIMEFRAME_CONFLUENCE', 'reason': 'No full alignment'}
        
        except Exception as e:
            return None, 0, {'strategy': 'MULTI_TIMEFRAME_CONFLUENCE', 'error': str(e)}

