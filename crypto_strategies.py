"""
Cryptocurrency Trading Strategies
==================================
Specialized strategies optimized for crypto market characteristics:
- Higher volatility
- 24/7 trading
- Strong momentum
- News-driven moves
- Support/resistance respect
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from indicators import TechnicalIndicators as TI
from market_analyzer import MarketAnalyzer
import logging

logger = logging.getLogger(__name__)


class CryptoTradingStrategies:
    """
    Cryptocurrency-specific trading strategies
    
    Key differences from forex:
    - Wider stops (2-4x volatility)
    - Stronger momentum following
    - Less mean reversion
    - Round number psychology (BTC: 40k, 50k, etc.)
    - News/sentiment driven
    """
    
    def __init__(self):
        self.ti = TI()
        self.market_analyzer = MarketAnalyzer()
    
    def crypto_strategy_1_momentum_breakout(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame,
                                           symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Crypto Strategy 1: Momentum Breakout
        
        Cryptos have strong momentum - ride the wave
        
        Entry:
        - Price breaks above/below 20-period high/low
        - Volume confirms (2x average)
        - RSI shows momentum (>60 for buy, <40 for sell)
        
        Exit:
        - Structure-based SL/TP
        - Trailing stop (cryptos can run far)
        """
        try:
            if len(df_m15) < 100 or len(df_h1) < 50:
                return None, 0, {}
            
            # Calculate indicators on M15
            df_m15 = self.ti.calculate_ema(df_m15, 20)
            df_m15 = self.ti.calculate_rsi(df_m15, 14)
            df_m15 = self.ti.calculate_atr(df_m15, 14)
            
            # Calculate volume indicators
            df_m15['volume_ma'] = df_m15['tick_volume'].rolling(20).mean()
            df_m15['volume_ratio'] = df_m15['tick_volume'] / df_m15['volume_ma']
            
            # 20-period high/low
            df_m15['high_20'] = df_m15['high'].rolling(20).max()
            df_m15['low_20'] = df_m15['low'].rolling(20).min()
            
            # Current values
            close = df_m15['close'].iloc[-1]
            high_20 = df_m15['high_20'].iloc[-2]  # Previous candle
            low_20 = df_m15['low_20'].iloc[-2]
            rsi = df_m15['rsi'].iloc[-1]
            volume_ratio = df_m15['volume_ratio'].iloc[-1]
            atr = df_m15['atr'].iloc[-1]
            
            # H1 trend confirmation
            df_h1 = self.ti.calculate_ema(df_h1, 50)
            h1_trend = 'bullish' if df_h1['close'].iloc[-1] > df_h1['ema_50'].iloc[-1] else 'bearish'
            
            action = None
            confidence = 0
            
            # Bullish breakout
            if close > high_20 and volume_ratio > 2.0 and rsi > 60 and h1_trend == 'bullish':
                action = 'BUY'
                confidence = 70
                
                # Increase confidence for strong momentum
                if rsi > 70:
                    confidence += 10
                if volume_ratio > 3.0:
                    confidence += 5
            
            # Bearish breakout
            elif close < low_20 and volume_ratio > 2.0 and rsi < 40 and h1_trend == 'bearish':
                action = 'SELL'
                confidence = 70
                
                if rsi < 30:
                    confidence += 10
                if volume_ratio > 3.0:
                    confidence += 5
            
            if not action:
                return None, 0, {}
            
            # Dynamic SL/TP using market analyzer
            market_analysis = self.market_analyzer.analyze_market_structure(df_h1, symbol)
            
            # Crypto-specific adjustments
            volatility_mult = 3.0  # Cryptos are 3x more volatile
            
            sl_pips = market_analysis['recommended_sl'] * volatility_mult
            tp_pips = market_analysis['recommended_tp'] * volatility_mult
            
            # Ensure minimum distances
            min_sl = atr * 2.0
            min_tp = atr * 4.0
            
            sl_pips = max(sl_pips, min_sl)
            tp_pips = max(tp_pips, min_tp)
            
            logger.info(f"Crypto Momentum Breakout: {symbol} {action} @ {close:.2f}")
            logger.info(f"  Confidence: {confidence}%, Volume: {volume_ratio:.1f}x, RSI: {rsi:.1f}")
            logger.info(f"  SL: {sl_pips:.1f}, TP: {tp_pips:.1f}")
            
            return action, confidence, {
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'strategy': 'Crypto_Momentum_Breakout',
                'use_trailing_stop': True,
                'trailing_activation': 0.4,  # Activate early for crypto
                'entry_reason': f'Breakout with {volume_ratio:.1f}x volume, RSI {rsi:.0f}'
            }
        
        except Exception as e:
            logger.error(f"Error in crypto_strategy_1: {e}")
            return None, 0, {}
    
    def crypto_strategy_2_support_resistance(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame,
                                            symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Crypto Strategy 2: Support/Resistance Bounce
        
        Cryptos respect round numbers and key levels
        
        Entry:
        - Price bounces off major support/resistance
        - Confluence with round numbers (BTC: 40k, 45k, 50k)
        - Volume spike on bounce
        
        Exit:
        - Target next key level
        - Tight stop below/above level
        """
        try:
            if len(df_m15) < 100 or len(df_h1) < 100:
                return None, 0, {}
            
            # Calculate indicators
            df_h1 = self.ti.calculate_ema(df_h1, 20)
            df_h1 = self.ti.calculate_rsi(df_h1, 14)
            df_h1 = self.ti.calculate_atr(df_h1, 14)
            
            # Identify support/resistance levels
            levels = self._find_key_levels(df_h1)
            
            if not levels:
                return None, 0, {}
            
            close = df_h1['close'].iloc[-1]
            rsi = df_h1['rsi'].iloc[-1]
            atr = df_h1['atr'].iloc[-1]
            
            # Check for round numbers (for BTC, ETH, etc.)
            round_numbers = self._get_round_numbers(symbol, close)
            
            action = None
            confidence = 0
            nearest_level = None
            
            # Check if price is near support
            for level in levels['support']:
                distance = abs(close - level) / close
                
                if distance < 0.02:  # Within 2% of support
                    # Check if bouncing
                    if df_h1['low'].iloc[-1] <= level <= df_h1['close'].iloc[-1]:
                        action = 'BUY'
                        confidence = 65
                        nearest_level = level
                        
                        # Increase confidence for round number confluence
                        if any(abs(level - rn) / level < 0.01 for rn in round_numbers):
                            confidence += 10
                        
                        # RSI oversold
                        if rsi < 40:
                            confidence += 10
                        
                        break
            
            # Check if price is near resistance
            if not action:
                for level in levels['resistance']:
                    distance = abs(close - level) / close
                    
                    if distance < 0.02:  # Within 2% of resistance
                        # Check if rejecting
                        if df_h1['high'].iloc[-1] >= level >= df_h1['close'].iloc[-1]:
                            action = 'SELL'
                            confidence = 65
                            nearest_level = level
                            
                            # Round number confluence
                            if any(abs(level - rn) / level < 0.01 for rn in round_numbers):
                                confidence += 10
                            
                            # RSI overbought
                            if rsi > 60:
                                confidence += 10
                            
                            break
            
            if not action:
                return None, 0, {}
            
            # Calculate SL/TP
            if action == 'BUY':
                # Stop below support
                sl_pips = (close - nearest_level) * 1.5
                # Target next resistance
                next_resistance = min([r for r in levels['resistance'] if r > close], default=close + atr * 5)
                tp_pips = next_resistance - close
            else:
                # Stop above resistance
                sl_pips = (nearest_level - close) * 1.5
                # Target next support
                next_support = max([s for s in levels['support'] if s < close], default=close - atr * 5)
                tp_pips = close - next_support
            
            # Ensure minimum distances
            sl_pips = max(sl_pips, atr * 2.0)
            tp_pips = max(tp_pips, atr * 3.0)
            
            logger.info(f"Crypto S/R Bounce: {symbol} {action} @ {close:.2f}")
            logger.info(f"  Level: {nearest_level:.2f}, Confidence: {confidence}%")
            logger.info(f"  SL: {sl_pips:.1f}, TP: {tp_pips:.1f}")
            
            return action, confidence, {
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'strategy': 'Crypto_Support_Resistance',
                'use_trailing_stop': False,  # Fixed target at key level
                'entry_reason': f'Bounce off {nearest_level:.0f} level'
            }
        
        except Exception as e:
            logger.error(f"Error in crypto_strategy_2: {e}")
            return None, 0, {}
    
    def crypto_strategy_3_trend_following(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame, df_h4: pd.DataFrame,
                                         symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Crypto Strategy 3: Multi-Timeframe Trend Following
        
        Cryptos have strong, sustained trends
        
        Entry:
        - H4 trend established (EMA alignment)
        - H1 pullback to support
        - M15 reversal signal
        
        Exit:
        - Trailing stop (let winners run)
        - Exit on trend break
        """
        try:
            if len(df_m15) < 50 or len(df_h1) < 100 or len(df_h4) < 100:
                return None, 0, {}
            
            # H4 trend
            df_h4 = self.ti.calculate_ema(df_h4, 20)
            df_h4 = self.ti.calculate_ema(df_h4, 50)
            
            h4_trend = None
            if df_h4['ema_20'].iloc[-1] > df_h4['ema_50'].iloc[-1]:
                h4_trend = 'bullish'
            elif df_h4['ema_20'].iloc[-1] < df_h4['ema_50'].iloc[-1]:
                h4_trend = 'bearish'
            
            if not h4_trend:
                return None, 0, {}
            
            # H1 pullback
            df_h1 = self.ti.calculate_ema(df_h1, 20)
            df_h1 = self.ti.calculate_rsi(df_h1, 14)
            df_h1 = self.ti.calculate_atr(df_h1, 14)
            
            close_h1 = df_h1['close'].iloc[-1]
            ema_20_h1 = df_h1['ema_20'].iloc[-1]
            rsi_h1 = df_h1['rsi'].iloc[-1]
            atr_h1 = df_h1['atr'].iloc[-1]
            
            # M15 reversal
            df_m15 = self.ti.calculate_ema(df_m15, 10)
            close_m15 = df_m15['close'].iloc[-1]
            ema_10_m15 = df_m15['ema_10'].iloc[-1]
            
            action = None
            confidence = 0
            
            # Bullish trend following
            if h4_trend == 'bullish':
                # Pullback to H1 EMA
                if close_h1 < ema_20_h1 * 1.02 and close_h1 > ema_20_h1 * 0.98:
                    # M15 reversal up
                    if close_m15 > ema_10_m15:
                        action = 'BUY'
                        confidence = 75
                        
                        # RSI not overbought
                        if 40 < rsi_h1 < 60:
                            confidence += 10
            
            # Bearish trend following
            elif h4_trend == 'bearish':
                # Pullback to H1 EMA
                if close_h1 > ema_20_h1 * 0.98 and close_h1 < ema_20_h1 * 1.02:
                    # M15 reversal down
                    if close_m15 < ema_10_m15:
                        action = 'SELL'
                        confidence = 75
                        
                        # RSI not oversold
                        if 40 < rsi_h1 < 60:
                            confidence += 10
            
            if not action:
                return None, 0, {}
            
            # Dynamic SL/TP
            market_analysis = self.market_analyzer.analyze_market_structure(df_h1, symbol)
            
            volatility_mult = 3.0
            sl_pips = market_analysis['recommended_sl'] * volatility_mult
            tp_pips = market_analysis['recommended_tp'] * volatility_mult * 1.5  # Wider TP for trends
            
            # Minimum distances
            sl_pips = max(sl_pips, atr_h1 * 2.5)
            tp_pips = max(tp_pips, atr_h1 * 6.0)
            
            logger.info(f"Crypto Trend Following: {symbol} {action} @ {close_h1:.2f}")
            logger.info(f"  H4 Trend: {h4_trend}, Confidence: {confidence}%")
            logger.info(f"  SL: {sl_pips:.1f}, TP: {tp_pips:.1f}")
            
            return action, confidence, {
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'strategy': 'Crypto_Trend_Following',
                'use_trailing_stop': True,
                'trailing_activation': 0.3,  # Activate early
                'entry_reason': f'{h4_trend.capitalize()} H4 trend, pullback entry'
            }
        
        except Exception as e:
            logger.error(f"Error in crypto_strategy_3: {e}")
            return None, 0, {}
    
    def crypto_strategy_4_volatility_breakout(self, df_m15: pd.DataFrame, df_h1: pd.DataFrame,
                                             symbol: str) -> Tuple[Optional[str], float, Dict]:
        """
        Crypto Strategy 4: Volatility Breakout (Bollinger Bands)
        
        Cryptos have explosive moves after consolidation
        
        Entry:
        - Bollinger Bands squeeze (low volatility)
        - Price breaks out of bands
        - Volume confirms
        
        Exit:
        - Bollinger Band expansion complete
        - Trailing stop
        """
        try:
            if len(df_m15) < 100 or len(df_h1) < 100:
                return None, 0, {}
            
            # Calculate Bollinger Bands on H1
            df_h1 = self.ti.calculate_bollinger_bands(df_h1, 20, 2.0)
            df_h1 = self.ti.calculate_atr(df_h1, 14)
            
            # Calculate band width (measure of volatility)
            df_h1['bb_width'] = (df_h1['bb_upper'] - df_h1['bb_lower']) / df_h1['bb_middle']
            df_h1['bb_width_ma'] = df_h1['bb_width'].rolling(50).mean()
            
            # Volume
            df_h1['volume_ma'] = df_h1['tick_volume'].rolling(20).mean()
            df_h1['volume_ratio'] = df_h1['tick_volume'] / df_h1['volume_ma']
            
            close = df_h1['close'].iloc[-1]
            bb_upper = df_h1['bb_upper'].iloc[-1]
            bb_lower = df_h1['bb_lower'].iloc[-1]
            bb_width = df_h1['bb_width'].iloc[-1]
            bb_width_ma = df_h1['bb_width_ma'].iloc[-1]
            volume_ratio = df_h1['volume_ratio'].iloc[-1]
            atr = df_h1['atr'].iloc[-1]
            
            action = None
            confidence = 0
            
            # Check for squeeze (low volatility)
            is_squeeze = bb_width < bb_width_ma * 0.7
            
            if not is_squeeze:
                return None, 0, {}
            
            # Bullish breakout
            if close > bb_upper and volume_ratio > 1.5:
                action = 'BUY'
                confidence = 70
                
                # Strong volume
                if volume_ratio > 2.5:
                    confidence += 10
            
            # Bearish breakout
            elif close < bb_lower and volume_ratio > 1.5:
                action = 'SELL'
                confidence = 70
                
                if volume_ratio > 2.5:
                    confidence += 10
            
            if not action:
                return None, 0, {}
            
            # SL/TP based on ATR
            sl_pips = atr * 2.5
            tp_pips = atr * 6.0  # Wide target for breakouts
            
            logger.info(f"Crypto Volatility Breakout: {symbol} {action} @ {close:.2f}")
            logger.info(f"  BB Squeeze, Volume: {volume_ratio:.1f}x, Confidence: {confidence}%")
            logger.info(f"  SL: {sl_pips:.1f}, TP: {tp_pips:.1f}")
            
            return action, confidence, {
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'strategy': 'Crypto_Volatility_Breakout',
                'use_trailing_stop': True,
                'trailing_activation': 0.4,
                'entry_reason': f'BB squeeze breakout, {volume_ratio:.1f}x volume'
            }
        
        except Exception as e:
            logger.error(f"Error in crypto_strategy_4: {e}")
            return None, 0, {}
    
    def _find_key_levels(self, df: pd.DataFrame, lookback: int = 100) -> Dict:
        """
        Find key support and resistance levels
        
        Returns:
            {'support': [levels], 'resistance': [levels]}
        """
        if len(df) < lookback:
            return {'support': [], 'resistance': []}
        
        df_recent = df.iloc[-lookback:]
        
        # Find swing highs and lows
        highs = []
        lows = []
        
        for i in range(2, len(df_recent) - 2):
            # Swing high
            if (df_recent['high'].iloc[i] > df_recent['high'].iloc[i-1] and
                df_recent['high'].iloc[i] > df_recent['high'].iloc[i-2] and
                df_recent['high'].iloc[i] > df_recent['high'].iloc[i+1] and
                df_recent['high'].iloc[i] > df_recent['high'].iloc[i+2]):
                highs.append(df_recent['high'].iloc[i])
            
            # Swing low
            if (df_recent['low'].iloc[i] < df_recent['low'].iloc[i-1] and
                df_recent['low'].iloc[i] < df_recent['low'].iloc[i-2] and
                df_recent['low'].iloc[i] < df_recent['low'].iloc[i+1] and
                df_recent['low'].iloc[i] < df_recent['low'].iloc[i+2]):
                lows.append(df_recent['low'].iloc[i])
        
        # Cluster levels (within 1% of each other)
        resistance = self._cluster_levels(highs)
        support = self._cluster_levels(lows)
        
        return {
            'support': sorted(support),
            'resistance': sorted(resistance, reverse=True)
        }
    
    def _cluster_levels(self, levels: list, threshold: float = 0.01) -> list:
        """Cluster levels that are close to each other"""
        if not levels:
            return []
        
        levels = sorted(levels)
        clusters = []
        current_cluster = [levels[0]]
        
        for level in levels[1:]:
            if abs(level - current_cluster[-1]) / current_cluster[-1] < threshold:
                current_cluster.append(level)
            else:
                clusters.append(np.mean(current_cluster))
                current_cluster = [level]
        
        clusters.append(np.mean(current_cluster))
        
        return clusters
    
    def _get_round_numbers(self, symbol: str, price: float) -> list:
        """
        Get psychologically important round numbers
        
        BTC: 40000, 45000, 50000, etc.
        ETH: 2000, 2500, 3000, etc.
        Others: nearest 100s or 1000s
        """
        round_numbers = []
        
        if 'BTC' in symbol.upper():
            # 5000 increments
            base = int(price / 5000) * 5000
            round_numbers = [base - 5000, base, base + 5000]
        
        elif 'ETH' in symbol.upper():
            # 500 increments
            base = int(price / 500) * 500
            round_numbers = [base - 500, base, base + 500]
        
        else:
            # 100 increments for smaller cryptos
            base = int(price / 100) * 100
            round_numbers = [base - 100, base, base + 100]
        
        return [rn for rn in round_numbers if rn > 0]


def integrate_crypto_strategies(scanner):
    """
    Integrate crypto strategies into opportunity scanner
    
    Usage:
        crypto_strategies = CryptoTradingStrategies()
        integrate_crypto_strategies(scanner)
    """
    scanner.crypto_strategies = CryptoTradingStrategies()
    
    logger.info("✅ Cryptocurrency strategies integrated")


# Example usage in opportunity_scanner_improved.py:
"""
from crypto_strategies import CryptoTradingStrategies

class ImprovedOpportunityScanner:
    def __init__(self):
        self.strategies = ImprovedTradingStrategies()
        self.crypto_strategies = CryptoTradingStrategies()  # Add this
    
    def scan_symbol(self, symbol, timeframe):
        # Check if crypto
        if self.is_crypto(symbol):
            # Use crypto strategies
            signal = self.crypto_strategies.crypto_strategy_1_momentum_breakout(...)
            # ... etc
        else:
            # Use forex strategies
            signal = self.strategies.strategy_1_trend_following(...)
"""

