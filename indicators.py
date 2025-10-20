"""
Ultimate Indicator Library
===========================
All technical indicators needed for the trading system
"""

import pandas as pd
import numpy as np
from typing import Tuple, List


class TechnicalIndicators:
    """Comprehensive technical indicator calculations"""
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average"""
        return data.ewm(span=period, adjust=False).mean()
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average"""
        return data.rolling(window=period).mean()
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index"""
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD (Moving Average Convergence Divergence)"""
        ema_fast = data.ewm(span=fast, adjust=False).mean()
        ema_slow = data.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands"""
        sma = data.rolling(window=period).mean()
        std = data.rolling(window=period).std()
        upper = sma + (std_dev * std)
        lower = sma - (std_dev * std)
        return upper, sma, lower
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        return tr.rolling(window=period).mean()
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average Directional Index"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        plus_dm = high.diff()
        minus_dm = -low.diff()
        
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        
        atr = tr.rolling(window=period).mean()
        plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(window=period).mean()
        
        return adx
    
    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator"""
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        
        k = 100 * (df['close'] - low_min) / (high_max - low_min)
        d = k.rolling(window=d_period).mean()
        
        return k, d
    
    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index"""
        tp = (df['high'] + df['low'] + df['close']) / 3
        sma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
        
        cci = (tp - sma_tp) / (0.015 * mad)
        return cci
    
    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R"""
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        
        wr = -100 * (high_max - df['close']) / (high_max - low_min)
        return wr
    
    @staticmethod
    def parabolic_sar(df: pd.DataFrame, af: float = 0.02, max_af: float = 0.2) -> pd.Series:
        """Parabolic SAR"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        sar = close.copy()
        ep = close.copy()
        trend = pd.Series([1] * len(df), index=df.index)
        acceleration = af
        
        for i in range(2, len(df)):
            if trend.iloc[i-1] == 1:  # Uptrend
                sar.iloc[i] = sar.iloc[i-1] + acceleration * (ep.iloc[i-1] - sar.iloc[i-1])
                
                if low.iloc[i] < sar.iloc[i]:
                    trend.iloc[i] = -1
                    sar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = low.iloc[i]
                    acceleration = af
                else:
                    if high.iloc[i] > ep.iloc[i-1]:
                        ep.iloc[i] = high.iloc[i]
                        acceleration = min(acceleration + af, max_af)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
            else:  # Downtrend
                sar.iloc[i] = sar.iloc[i-1] - acceleration * (sar.iloc[i-1] - ep.iloc[i-1])
                
                if high.iloc[i] > sar.iloc[i]:
                    trend.iloc[i] = 1
                    sar.iloc[i] = ep.iloc[i-1]
                    ep.iloc[i] = high.iloc[i]
                    acceleration = af
                else:
                    if low.iloc[i] < ep.iloc[i-1]:
                        ep.iloc[i] = low.iloc[i]
                        acceleration = min(acceleration + af, max_af)
                    else:
                        ep.iloc[i] = ep.iloc[i-1]
        
        return sar
    
    @staticmethod
    def pivot_points(df: pd.DataFrame) -> dict:
        """Daily Pivot Points"""
        # Get previous day's data
        prev_high = df['high'].iloc[-2] if len(df) > 1 else df['high'].iloc[-1]
        prev_low = df['low'].iloc[-2] if len(df) > 1 else df['low'].iloc[-1]
        prev_close = df['close'].iloc[-2] if len(df) > 1 else df['close'].iloc[-1]
        
        pivot = (prev_high + prev_low + prev_close) / 3
        
        r1 = 2 * pivot - prev_low
        s1 = 2 * pivot - prev_high
        r2 = pivot + (prev_high - prev_low)
        s2 = pivot - (prev_high - prev_low)
        r3 = prev_high + 2 * (pivot - prev_low)
        s3 = prev_low - 2 * (prev_high - pivot)
        
        return {
            'pivot': pivot,
            'r1': r1, 'r2': r2, 'r3': r3,
            's1': s1, 's2': s2, 's3': s3
        }
    
    @staticmethod
    def fibonacci_retracement(df: pd.DataFrame, lookback: int = 50) -> dict:
        """Fibonacci Retracement Levels"""
        recent_data = df.tail(lookback)
        
        # Find swing high and low
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        diff = swing_high - swing_low
        
        # Calculate Fibonacci levels
        levels = {
            'swing_high': swing_high,
            'swing_low': swing_low,
            'fib_0': swing_high,
            'fib_236': swing_high - 0.236 * diff,
            'fib_382': swing_high - 0.382 * diff,
            'fib_500': swing_high - 0.500 * diff,
            'fib_618': swing_high - 0.618 * diff,
            'fib_786': swing_high - 0.786 * diff,
            'fib_100': swing_low,
        }
        
        return levels
    
    @staticmethod
    def fibonacci_extension(df: pd.DataFrame, lookback: int = 50) -> dict:
        """Fibonacci Extension Levels"""
        recent_data = df.tail(lookback)
        
        swing_high = recent_data['high'].max()
        swing_low = recent_data['low'].min()
        
        diff = swing_high - swing_low
        
        # Calculate extension levels
        levels = {
            'ext_0': swing_low,
            'ext_618': swing_low + 0.618 * diff,
            'ext_1000': swing_low + 1.000 * diff,
            'ext_1272': swing_low + 1.272 * diff,
            'ext_1618': swing_low + 1.618 * diff,
            'ext_2000': swing_low + 2.000 * diff,
        }
        
        return levels
    
    @staticmethod
    def support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 3) -> dict:
        """Support and Resistance Levels"""
        recent_data = df.tail(100)
        
        # Find local maxima (resistance)
        resistance_candidates = []
        for i in range(window, len(recent_data) - window):
            if recent_data['high'].iloc[i] == recent_data['high'].iloc[i-window:i+window].max():
                resistance_candidates.append(recent_data['high'].iloc[i])
        
        # Find local minima (support)
        support_candidates = []
        for i in range(window, len(recent_data) - window):
            if recent_data['low'].iloc[i] == recent_data['low'].iloc[i-window:i+window].min():
                support_candidates.append(recent_data['low'].iloc[i])
        
        # Cluster nearby levels
        def cluster_levels(levels, tolerance=0.0005):
            if not levels:
                return []
            levels = sorted(levels)
            clustered = []
            current_cluster = [levels[0]]
            
            for level in levels[1:]:
                if abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                    current_cluster.append(level)
                else:
                    clustered.append(np.mean(current_cluster))
                    current_cluster = [level]
            clustered.append(np.mean(current_cluster))
            return clustered
        
        resistance_levels = cluster_levels(resistance_candidates)[-num_levels:]
        support_levels = cluster_levels(support_candidates)[-num_levels:]
        
        return {
            'resistance': sorted(resistance_levels, reverse=True),
            'support': sorted(support_levels, reverse=True)
        }
    
    @staticmethod
    def keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Keltner Channels"""
        ema = df['close'].ewm(span=period, adjust=False).mean()
        atr = TechnicalIndicators.atr(df, period)
        
        upper = ema + (multiplier * atr)
        lower = ema - (multiplier * atr)
        
        return upper, ema, lower

