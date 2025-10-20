"""
Enhanced Technical Indicators
==============================
Improved indicators with:
- Comprehensive error handling
- NaN value management
- Dynamic tolerance for clustering
- Edge case handling
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class EnhancedTechnicalIndicators:
    """Technical indicators with robust error handling"""
    
    @staticmethod
    def ema(data: pd.Series, period: int) -> pd.Series:
        """Exponential Moving Average with error handling"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for EMA({period}): {len(data)} bars")
                return pd.Series([np.nan] * len(data), index=data.index)
            
            result = data.ewm(span=period, adjust=False).mean()
            return result.bfill()  # Fill initial NaN values
        except Exception as e:
            logger.error(f"Error calculating EMA: {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    @staticmethod
    def sma(data: pd.Series, period: int) -> pd.Series:
        """Simple Moving Average with error handling"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for SMA({period}): {len(data)} bars")
                return pd.Series([np.nan] * len(data), index=data.index)
            
            return data.rolling(window=period).mean()
        except Exception as e:
            logger.error(f"Error calculating SMA: {e}")
            return pd.Series([np.nan] * len(data), index=data.index)
    
    @staticmethod
    def rsi(data: pd.Series, period: int = 14) -> pd.Series:
        """Relative Strength Index with division by zero handling"""
        try:
            if len(data) < period + 1:
                logger.warning(f"Insufficient data for RSI({period}): {len(data)} bars")
                return pd.Series([50.0] * len(data), index=data.index)  # Neutral RSI
            
            delta = data.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            
            # Handle division by zero
            rs = gain / loss.replace(0, 0.0001)  # Avoid division by zero
            rsi = 100 - (100 / (1 + rs))
            
            # Fill NaN values with neutral 50
            return rsi.fillna(50.0)
        except Exception as e:
            logger.error(f"Error calculating RSI: {e}")
            return pd.Series([50.0] * len(data), index=data.index)
    
    @staticmethod
    def macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """MACD with error handling"""
        try:
            if len(data) < slow + signal:
                logger.warning(f"Insufficient data for MACD: {len(data)} bars")
                zeros = pd.Series([0.0] * len(data), index=data.index)
                return zeros, zeros, zeros
            
            ema_fast = data.ewm(span=fast, adjust=False).mean()
            ema_slow = data.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal, adjust=False).mean()
            histogram = macd_line - signal_line
            
            return macd_line.fillna(0), signal_line.fillna(0), histogram.fillna(0)
        except Exception as e:
            logger.error(f"Error calculating MACD: {e}")
            zeros = pd.Series([0.0] * len(data), index=data.index)
            return zeros, zeros, zeros
    
    @staticmethod
    def bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Bollinger Bands with error handling"""
        try:
            if len(data) < period:
                logger.warning(f"Insufficient data for Bollinger Bands({period}): {len(data)} bars")
                middle = pd.Series([data.iloc[-1]] * len(data), index=data.index)
                return middle, middle, middle
            
            sma = data.rolling(window=period).mean()
            std = data.rolling(window=period).std()
            
            # Handle NaN in std
            std = std.fillna(0.0001)
            
            upper = sma + (std_dev * std)
            lower = sma - (std_dev * std)
            
            return upper, sma, lower
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {e}")
            middle = pd.Series([data.iloc[-1]] * len(data), index=data.index)
            return middle, middle, middle
    
    @staticmethod
    def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average True Range with error handling"""
        try:
            if len(df) < period + 1:
                logger.warning(f"Insufficient data for ATR({period}): {len(df)} bars")
                # Return reasonable default based on price range
                price_range = df['high'].max() - df['low'].min()
                default_atr = price_range / len(df)
                return pd.Series([default_atr] * len(df), index=df.index)
            
            high = df['high']
            low = df['low']
            close = df['close']
            
            tr1 = high - low
            tr2 = abs(high - close.shift())
            tr3 = abs(low - close.shift())
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            
            atr = tr.rolling(window=period).mean()
            
            # Fill NaN values with first valid value
            return atr.bfill()
        except Exception as e:
            logger.error(f"Error calculating ATR: {e}")
            return pd.Series([0.0001] * len(df), index=df.index)
    
    @staticmethod
    def adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Average Directional Index with error handling"""
        try:
            if len(df) < period * 2:
                logger.warning(f"Insufficient data for ADX({period}): {len(df)} bars")
                return pd.Series([20.0] * len(df), index=df.index)  # Neutral ADX
            
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
            
            # Avoid division by zero
            atr = atr.replace(0, 0.0001)
            
            plus_di = 100 * (plus_dm.rolling(window=period).mean() / atr)
            minus_di = 100 * (minus_dm.rolling(window=period).mean() / atr)
            
            # Avoid division by zero in DX calculation
            di_sum = plus_di + minus_di
            di_sum = di_sum.replace(0, 0.0001)
            
            dx = 100 * abs(plus_di - minus_di) / di_sum
            adx = dx.rolling(window=period).mean()
            
            return adx.fillna(20.0)  # Fill with neutral value
        except Exception as e:
            logger.error(f"Error calculating ADX: {e}")
            return pd.Series([20.0] * len(df), index=df.index)
    
    @staticmethod
    def stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Tuple[pd.Series, pd.Series]:
        """Stochastic Oscillator with error handling"""
        try:
            if len(df) < k_period + d_period:
                logger.warning(f"Insufficient data for Stochastic: {len(df)} bars")
                neutral = pd.Series([50.0] * len(df), index=df.index)
                return neutral, neutral
            
            low_min = df['low'].rolling(window=k_period).min()
            high_max = df['high'].rolling(window=k_period).max()
            
            # Avoid division by zero
            denominator = (high_max - low_min).replace(0, 0.0001)
            
            k = 100 * (df['close'] - low_min) / denominator
            d = k.rolling(window=d_period).mean()
            
            return k.fillna(50.0), d.fillna(50.0)
        except Exception as e:
            logger.error(f"Error calculating Stochastic: {e}")
            neutral = pd.Series([50.0] * len(df), index=df.index)
            return neutral, neutral
    
    @staticmethod
    def cci(df: pd.DataFrame, period: int = 20) -> pd.Series:
        """Commodity Channel Index with error handling"""
        try:
            if len(df) < period:
                logger.warning(f"Insufficient data for CCI({period}): {len(df)} bars")
                return pd.Series([0.0] * len(df), index=df.index)
            
            tp = (df['high'] + df['low'] + df['close']) / 3
            sma_tp = tp.rolling(window=period).mean()
            mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean())
            
            # Avoid division by zero
            mad = mad.replace(0, 0.0001)
            
            cci = (tp - sma_tp) / (0.015 * mad)
            return cci.fillna(0.0)
        except Exception as e:
            logger.error(f"Error calculating CCI: {e}")
            return pd.Series([0.0] * len(df), index=df.index)
    
    @staticmethod
    def williams_r(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Williams %R with error handling"""
        try:
            if len(df) < period:
                logger.warning(f"Insufficient data for Williams %R({period}): {len(df)} bars")
                return pd.Series([-50.0] * len(df), index=df.index)
            
            high_max = df['high'].rolling(window=period).max()
            low_min = df['low'].rolling(window=period).min()
            
            # Avoid division by zero
            denominator = (high_max - low_min).replace(0, 0.0001)
            
            wr = -100 * (high_max - df['close']) / denominator
            return wr.fillna(-50.0)
        except Exception as e:
            logger.error(f"Error calculating Williams %R: {e}")
            return pd.Series([-50.0] * len(df), index=df.index)
    
    @staticmethod
    def support_resistance(df: pd.DataFrame, window: int = 20, num_levels: int = 3, atr: Optional[float] = None) -> dict:
        """
        Support and Resistance Levels with dynamic clustering
        
        Args:
            df: Price dataframe
            window: Window for finding swing points
            num_levels: Number of levels to return
            atr: ATR value for dynamic tolerance (optional)
        """
        try:
            recent_data = df.tail(100)
            
            if len(recent_data) < window * 2:
                logger.warning(f"Insufficient data for S/R: {len(recent_data)} bars")
                return {'resistance': [], 'support': []}
            
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
            
            # Dynamic tolerance based on ATR
            if atr and atr > 0:
                current_price = df['close'].iloc[-1]
                tolerance = (atr / current_price) * 0.5  # 50% of ATR as percentage
            else:
                tolerance = 0.0005  # Default 0.05%
            
            # Cluster nearby levels
            def cluster_levels(levels, tolerance):
                if not levels:
                    return []
                levels = sorted(levels)
                clustered = []
                current_cluster = [levels[0]]
                
                for level in levels[1:]:
                    if len(current_cluster) > 0 and abs(level - current_cluster[-1]) / current_cluster[-1] < tolerance:
                        current_cluster.append(level)
                    else:
                        clustered.append(np.mean(current_cluster))
                        current_cluster = [level]
                
                if current_cluster:
                    clustered.append(np.mean(current_cluster))
                return clustered
            
            resistance_levels = cluster_levels(resistance_candidates, tolerance)[-num_levels:]
            support_levels = cluster_levels(support_candidates, tolerance)[-num_levels:]
            
            return {
                'resistance': sorted(resistance_levels, reverse=True),
                'support': sorted(support_levels, reverse=True)
            }
        except Exception as e:
            logger.error(f"Error calculating S/R levels: {e}")
            return {'resistance': [], 'support': []}
    
    # Keep remaining indicators from original (pivot_points, fibonacci, etc.)
    # These are already well-implemented
    
    @staticmethod
    def pivot_points(df: pd.DataFrame) -> dict:
        """Daily Pivot Points"""
        try:
            if len(df) < 2:
                current_price = df['close'].iloc[-1]
                return {
                    'pivot': current_price,
                    'r1': current_price, 'r2': current_price, 'r3': current_price,
                    's1': current_price, 's2': current_price, 's3': current_price
                }
            
            prev_high = df['high'].iloc[-2]
            prev_low = df['low'].iloc[-2]
            prev_close = df['close'].iloc[-2]
            
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
        except Exception as e:
            logger.error(f"Error calculating pivot points: {e}")
            current_price = df['close'].iloc[-1]
            return {
                'pivot': current_price,
                'r1': current_price, 'r2': current_price, 'r3': current_price,
                's1': current_price, 's2': current_price, 's3': current_price
            }
    
    @staticmethod
    def fibonacci_retracement(df: pd.DataFrame, lookback: int = 50) -> dict:
        """Fibonacci Retracement Levels"""
        try:
            recent_data = df.tail(lookback)
            
            if len(recent_data) < 10:
                current_price = df['close'].iloc[-1]
                return {
                    'swing_high': current_price,
                    'swing_low': current_price,
                    'fib_0': current_price,
                    'fib_236': current_price,
                    'fib_382': current_price,
                    'fib_500': current_price,
                    'fib_618': current_price,
                    'fib_786': current_price,
                    'fib_100': current_price,
                }
            
            swing_high = recent_data['high'].max()
            swing_low = recent_data['low'].min()
            
            diff = swing_high - swing_low
            
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
        except Exception as e:
            logger.error(f"Error calculating Fibonacci levels: {e}")
            current_price = df['close'].iloc[-1]
            return {
                'swing_high': current_price,
                'swing_low': current_price,
                'fib_0': current_price,
                'fib_236': current_price,
                'fib_382': current_price,
                'fib_500': current_price,
                'fib_618': current_price,
                'fib_786': current_price,
                'fib_100': current_price,
            }
    
    @staticmethod
    def keltner_channels(df: pd.DataFrame, period: int = 20, multiplier: float = 2.0) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Keltner Channels with error handling"""
        try:
            if len(df) < period:
                logger.warning(f"Insufficient data for Keltner Channels({period}): {len(df)} bars")
                middle = pd.Series([df['close'].iloc[-1]] * len(df), index=df.index)
                return middle, middle, middle
            
            ema = df['close'].ewm(span=period, adjust=False).mean()
            atr = EnhancedTechnicalIndicators.atr(df, period)
            
            upper = ema + (multiplier * atr)
            lower = ema - (multiplier * atr)
            
            return upper, ema, lower
        except Exception as e:
            logger.error(f"Error calculating Keltner Channels: {e}")
            middle = pd.Series([df['close'].iloc[-1]] * len(df), index=df.index)
            return middle, middle, middle

