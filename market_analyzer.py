"""
Market Analyzer - Advanced Market Structure Analysis
=====================================================
Provides dynamic market analysis for intelligent SL/TP placement
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """Advanced market structure and volatility analysis"""
    
    def __init__(self):
        self.volatility_regimes = {
            'low': (0, 33),      # 0-33rd percentile
            'medium': (33, 67),  # 33-67th percentile
            'high': (67, 100)    # 67-100th percentile
        }
    
    def analyze_market_structure(self, df: pd.DataFrame, lookback: int = 50) -> Dict:
        """
        Comprehensive market structure analysis
        
        Returns:
            - swing_high: Recent swing high price
            - swing_low: Recent swing low price
            - support_levels: List of support prices
            - resistance_levels: List of resistance prices
            - trend_strength: 0-100 score
            - volatility_regime: 'low', 'medium', 'high'
        """
        try:
            recent_data = df.tail(lookback)
            
            # Find swing highs and lows
            swing_high = self._find_swing_high(recent_data)
            swing_low = self._find_swing_low(recent_data)
            
            # Identify support and resistance
            support_levels = self._find_support_levels(recent_data)
            resistance_levels = self._find_resistance_levels(recent_data)
            
            # Calculate trend strength using ADX
            trend_strength = self._calculate_trend_strength(df)
            
            # Determine volatility regime
            volatility_regime = self._determine_volatility_regime(df)
            
            return {
                'swing_high': swing_high,
                'swing_low': swing_low,
                'support_levels': support_levels,
                'resistance_levels': resistance_levels,
                'trend_strength': trend_strength,
                'volatility_regime': volatility_regime,
                'current_price': df['close'].iloc[-1]
            }
        
        except Exception as e:
            logger.error(f"Market structure analysis error: {e}")
            return self._default_structure(df)
    
    def _find_swing_high(self, df: pd.DataFrame, window: int = 5) -> float:
        """Find most recent swing high"""
        try:
            highs = df['high'].values
            for i in range(len(highs) - window - 1, window, -1):
                if all(highs[i] > highs[i-j] for j in range(1, window+1)) and \
                   all(highs[i] > highs[i+j] for j in range(1, window+1)):
                    return highs[i]
            return df['high'].max()
        except:
            return df['high'].max()
    
    def _find_swing_low(self, df: pd.DataFrame, window: int = 5) -> float:
        """Find most recent swing low"""
        try:
            lows = df['low'].values
            for i in range(len(lows) - window - 1, window, -1):
                if all(lows[i] < lows[i-j] for j in range(1, window+1)) and \
                   all(lows[i] < lows[i+j] for j in range(1, window+1)):
                    return lows[i]
            return df['low'].min()
        except:
            return df['low'].min()
    
    def _find_support_levels(self, df: pd.DataFrame, num_levels: int = 3) -> list:
        """Identify key support levels using price clustering"""
        try:
            lows = df['low'].values
            # Use clustering to find support zones
            hist, bin_edges = np.histogram(lows, bins=20)
            # Find bins with high frequency (support zones)
            support_indices = np.argsort(hist)[-num_levels:]
            support_levels = [(bin_edges[i] + bin_edges[i+1]) / 2 
                            for i in support_indices]
            return sorted(support_levels)
        except:
            return [df['low'].min()]
    
    def _find_resistance_levels(self, df: pd.DataFrame, num_levels: int = 3) -> list:
        """Identify key resistance levels using price clustering"""
        try:
            highs = df['high'].values
            # Use clustering to find resistance zones
            hist, bin_edges = np.histogram(highs, bins=20)
            # Find bins with high frequency (resistance zones)
            resistance_indices = np.argsort(hist)[-num_levels:]
            resistance_levels = [(bin_edges[i] + bin_edges[i+1]) / 2 
                                for i in resistance_indices]
            return sorted(resistance_levels, reverse=True)
        except:
            return [df['high'].max()]
    
    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength using ADX (0-100)"""
        try:
            period = 14
            high = df['high']
            low = df['low']
            close = df['close']
            
            # Calculate +DM and -DM
            plus_dm = high.diff()
            minus_dm = -low.diff()
            
            plus_dm[plus_dm < 0] = 0
            minus_dm[minus_dm < 0] = 0
            
            # Calculate True Range
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            # Calculate smoothed +DI and -DI
            atr = tr.rolling(window=period).mean()
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
            
            # Calculate DX and ADX
            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(window=period).mean()
            
            return min(100, max(0, adx.iloc[-1]))
        except:
            return 25  # Default medium strength
    
    def _determine_volatility_regime(self, df: pd.DataFrame, lookback: int = 100) -> str:
        """Determine current volatility regime"""
        try:
            # Calculate ATR percentile
            high = df['high'].tail(lookback)
            low = df['low'].tail(lookback)
            close = df['close'].tail(lookback)
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=14).mean()
            current_atr = atr.iloc[-1]
            
            # Calculate percentile
            percentile = (atr < current_atr).sum() / len(atr) * 100
            
            if percentile < 33:
                return 'low'
            elif percentile < 67:
                return 'medium'
            else:
                return 'high'
        except:
            return 'medium'
    
    def _default_structure(self, df: pd.DataFrame) -> Dict:
        """Return default structure on error"""
        return {
            'swing_high': df['high'].iloc[-1],
            'swing_low': df['low'].iloc[-1],
            'support_levels': [df['low'].min()],
            'resistance_levels': [df['high'].max()],
            'trend_strength': 25,
            'volatility_regime': 'medium',
            'current_price': df['close'].iloc[-1]
        }
    
    def get_session_info(self) -> Dict:
        """Get current trading session information"""
        from datetime import datetime, timezone
        
        now_utc = datetime.now(timezone.utc)
        hour = now_utc.hour
        
        # Define sessions
        if 0 <= hour < 8:
            session = 'asian'
            volatility_multiplier = 0.7  # Lower volatility
        elif 8 <= hour < 13:
            session = 'london'
            volatility_multiplier = 1.2  # Higher volatility
        elif 13 <= hour < 16:
            session = 'overlap'
            volatility_multiplier = 1.5  # Highest volatility
        elif 16 <= hour < 21:
            session = 'newyork'
            volatility_multiplier = 1.1  # High volatility
        else:
            session = 'asian'
            volatility_multiplier = 0.7
        
        return {
            'session': session,
            'volatility_multiplier': volatility_multiplier,
            'hour_utc': hour
        }
    
    def calculate_dynamic_atr_multiplier(self, df: pd.DataFrame, 
                                        strategy_type: str) -> Tuple[float, float]:
        """
        Calculate dynamic ATR multipliers based on market conditions
        
        Args:
            df: Price dataframe
            strategy_type: Type of strategy (trend/reversion/breakout/momentum)
        
        Returns:
            (sl_multiplier, tp_multiplier)
        """
        try:
            # Get market structure
            structure = self.analyze_market_structure(df)
            session_info = self.get_session_info()
            
            # Base multipliers by strategy type
            base_multipliers = {
                'trend': (1.5, 3.0),      # Wider stops, larger targets
                'reversion': (0.8, 1.2),  # Tighter stops, quick profits
                'breakout': (1.2, 2.5),   # Medium stops, good targets
                'momentum': (0.9, 1.5),   # Quick scalping
                'confluence': (1.8, 3.5)  # High confidence, wider parameters
            }
            
            sl_mult, tp_mult = base_multipliers.get(strategy_type, (1.0, 2.0))
            
            # Adjust for volatility regime
            if structure['volatility_regime'] == 'high':
                sl_mult *= 1.3  # Wider stops in high volatility
                tp_mult *= 1.2
            elif structure['volatility_regime'] == 'low':
                sl_mult *= 0.8  # Tighter stops in low volatility
                tp_mult *= 0.9
            
            # Adjust for trend strength
            trend_strength = structure['trend_strength']
            if trend_strength > 30:  # Strong trend
                if strategy_type == 'trend':
                    sl_mult *= 1.2  # Wider stops in strong trends
                    tp_mult *= 1.3  # Larger targets
            else:  # Weak trend / ranging
                if strategy_type in ['reversion', 'momentum']:
                    tp_mult *= 0.9  # Tighter targets in ranging markets
            
            # Adjust for session
            session_mult = session_info['volatility_multiplier']
            sl_mult *= session_mult
            
            return (sl_mult, tp_mult)
        
        except Exception as e:
            logger.error(f"Dynamic ATR multiplier error: {e}")
            return (1.0, 2.0)
    
    def calculate_structure_based_sl_tp(self, df: pd.DataFrame, action: str,
                                       entry_price: float, atr: float,
                                       pip_size: float, strategy_type: str) -> Tuple[float, float]:
        """
        Calculate SL/TP based on market structure, not just ATR
        
        Returns:
            (sl_pips, tp_pips)
        """
        try:
            structure = self.analyze_market_structure(df)
            
            # Get dynamic ATR multipliers
            sl_mult, tp_mult = self.calculate_dynamic_atr_multiplier(df, strategy_type)
            
            # Base ATR calculation
            base_sl_pips = (atr / pip_size) * sl_mult
            base_tp_pips = (atr / pip_size) * tp_mult
            
            # Adjust SL based on swing points
            if action == 'BUY':
                # Place SL below swing low
                swing_distance = (entry_price - structure['swing_low']) / pip_size
                # Use the larger of ATR-based or swing-based
                sl_pips = max(base_sl_pips, swing_distance * 1.1)
                
                # Place TP near resistance or use ATR
                nearest_resistance = min([r for r in structure['resistance_levels'] 
                                        if r > entry_price], default=entry_price + base_tp_pips * pip_size)
                resistance_distance = (nearest_resistance - entry_price) / pip_size
                tp_pips = min(base_tp_pips * 1.5, resistance_distance * 0.9)
            
            else:  # SELL
                # Place SL above swing high
                swing_distance = (structure['swing_high'] - entry_price) / pip_size
                sl_pips = max(base_sl_pips, swing_distance * 1.1)
                
                # Place TP near support or use ATR
                nearest_support = max([s for s in structure['support_levels'] 
                                     if s < entry_price], default=entry_price - base_tp_pips * pip_size)
                support_distance = (entry_price - nearest_support) / pip_size
                tp_pips = min(base_tp_pips * 1.5, support_distance * 0.9)
            
            # Ensure minimum distances (account for commission)
            min_sl = 8 if strategy_type != 'momentum' else 6
            min_tp = 12 if strategy_type != 'momentum' else 10
            
            sl_pips = max(min_sl, sl_pips)
            tp_pips = max(min_tp, tp_pips)
            
            # Ensure reasonable maximums
            max_sl = 50 if strategy_type == 'confluence' else 35
            max_tp = 100 if strategy_type == 'confluence' else 60
            
            sl_pips = min(max_sl, sl_pips)
            tp_pips = min(max_tp, tp_pips)
            
            # Ensure minimum R:R ratio
            min_rr = 1.2 if strategy_type == 'reversion' else 1.5
            if tp_pips / sl_pips < min_rr:
                tp_pips = sl_pips * min_rr
            
            return (round(sl_pips, 1), round(tp_pips, 1))
        
        except Exception as e:
            logger.error(f"Structure-based SL/TP error: {e}")
            # Fallback to simple ATR-based
            sl_pips = (atr / pip_size) * 1.2
            tp_pips = sl_pips * 2.0
            return (round(sl_pips, 1), round(tp_pips, 1))
    
    def get_symbol_pip_size(self, symbol: str, price: float) -> float:
        """
        Accurate pip size calculation for any symbol
        
        Args:
            symbol: Trading symbol
            price: Current price
        
        Returns:
            Pip size (e.g., 0.0001 for EURUSD, 0.01 for USDJPY)
        """
        symbol_upper = symbol.upper()
        
        # JPY pairs
        if 'JPY' in symbol_upper:
            return 0.01
        
        # Metals
        elif 'XAU' in symbol_upper or 'GOLD' in symbol_upper:
            return 0.10
        elif 'XAG' in symbol_upper or 'SILVER' in symbol_upper:
            return 0.01
        
        # Crypto (if supported)
        elif 'BTC' in symbol_upper:
            return 1.0
        elif 'ETH' in symbol_upper:
            return 0.1
        
        # Exotic pairs with high prices
        elif price > 100:
            return 0.01
        elif price > 10:
            return 0.001
        
        # Standard forex pairs
        else:
            return 0.0001
    
    def should_use_trailing_stop(self, strategy_type: str, confidence: float) -> bool:
        """
        Determine if trailing stop should be used
        
        Args:
            strategy_type: Type of strategy
            confidence: Signal confidence (0-100)
        
        Returns:
            True if trailing stop recommended
        """
        # Use trailing stops for:
        # 1. Breakout strategies (capture extended moves)
        # 2. High confidence trend following (let winners run)
        # 3. Multi-timeframe confluence (strong signals)
        
        if strategy_type == 'breakout':
            return True
        elif strategy_type == 'trend' and confidence >= 70:
            return True
        elif strategy_type == 'confluence' and confidence >= 75:
            return True
        else:
            return False
    
    def calculate_trailing_stop_distance(self, atr: float, pip_size: float,
                                        strategy_type: str) -> float:
        """
        Calculate trailing stop distance in pips
        
        Args:
            atr: Average True Range
            pip_size: Pip size for the symbol
            strategy_type: Type of strategy
        
        Returns:
            Trailing stop distance in pips
        """
        base_distance = (atr / pip_size) * 1.5
        
        if strategy_type == 'breakout':
            # Wider trailing for breakouts
            return max(15, min(base_distance * 1.2, 30))
        elif strategy_type == 'trend':
            return max(12, min(base_distance, 25))
        else:
            return max(10, min(base_distance * 0.8, 20))

