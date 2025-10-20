"""
Opportunity Scanner
===================
Scans 50+ pairs and ranks opportunities
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import List, Dict, Tuple
from strategies import TradingStrategies
import logging

logger = logging.getLogger(__name__)


class OpportunityScanner:
    """Scans multiple pairs and finds best trading opportunities"""
    
    TIMEFRAME_MAP = {
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
    }
    
    def __init__(self):
        self.strategies = TradingStrategies()
        self.last_scan_results = []
    
    def scan_all_pairs(self, symbols: List[str], enable_multi_tf: bool = False) -> List[Dict]:
        """
        Scan all pairs with all strategies
        
        Returns list of opportunities sorted by confidence
        """
        opportunities = []
        
        for symbol in symbols:
            try:
                # Get data for all timeframes
                rates_m5 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['M5'], 0, 200)
                if rates_m5 is None or len(rates_m5) < 100:
                    continue
                
                df_m5 = pd.DataFrame(rates_m5)
                df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
                
                rates_h1 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['H1'], 0, 100)
                if rates_h1 is None or len(rates_h1) < 50:
                    continue
                
                df_h1 = pd.DataFrame(rates_h1)
                df_h1['time'] = pd.to_datetime(df_h1['time'], unit='s')
                
                # Try all strategies
                strategy_results = []
                
                # Strategy 1: Trend Following
                action, conf, details = self.strategies.strategy_1_trend_following(df_m5, df_h1)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 2: Fibonacci
                action, conf, details = self.strategies.strategy_2_fibonacci_retracement(df_m5, df_h1)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 3: Mean Reversion
                action, conf, details = self.strategies.strategy_3_mean_reversion(df_m5)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 4: Breakout
                action, conf, details = self.strategies.strategy_4_breakout(df_m5, df_h1)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 5: Momentum
                action, conf, details = self.strategies.strategy_5_momentum(df_m5)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 6: Multi-Timeframe (optional, slower)
                if enable_multi_tf:
                    rates_m15 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['M15'], 0, 100)
                    rates_h4 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['H4'], 0, 50)
                    
                    if rates_m15 is not None and rates_h4 is not None:
                        df_m15 = pd.DataFrame(rates_m15)
                        df_h4 = pd.DataFrame(rates_h4)
                        
                        action, conf, details = self.strategies.strategy_6_multi_timeframe_confluence(
                            df_m5, df_m15, df_h1, df_h4
                        )
                        if action:
                            strategy_results.append((action, conf, details))
                
                # Add all signals for this symbol
                for action, conf, details in strategy_results:
                    opportunities.append({
                        'symbol': symbol,
                        'action': action,
                        'confidence': conf,
                        'strategy': details.get('strategy', 'UNKNOWN'),
                        'sl_pips': details.get('sl_pips', 10),
                        'tp_pips': details.get('tp_pips', 20),
                        'reason': details.get('reason', ''),
                        'current_price': df_m5['close'].iloc[-1]
                    })
            
            except Exception as e:
                logger.error(f"Error scanning {symbol}: {str(e)}")
                continue
        
        # Sort by confidence (highest first)
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        self.last_scan_results = opportunities
        return opportunities
    
    def get_detailed_analysis(self, symbol: str) -> Dict:
        """
        Get detailed analysis for a specific symbol
        Shows all indicator values and why/why not trading
        """
        try:
            rates_m5 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['M5'], 0, 200)
            if rates_m5 is None:
                return {'error': 'No data available'}
            
            df_m5 = pd.DataFrame(rates_m5)
            df_m5['time'] = pd.to_datetime(df_m5['time'], unit='s')
            
            rates_h1 = mt5.copy_rates_from_pos(symbol, self.TIMEFRAME_MAP['H1'], 0, 100)
            df_h1 = pd.DataFrame(rates_h1) if rates_h1 is not None else None
            
            # Calculate all indicators
            from indicators import TechnicalIndicators as TI
            ti = TI()
            
            # Trend
            ema9 = ti.ema(df_m5['close'], 9)
            ema21 = ti.ema(df_m5['close'], 21)
            macd_line, signal_line, histogram = ti.macd(df_m5['close'])
            adx = ti.adx(df_m5, 14)
            
            # Momentum
            rsi = ti.rsi(df_m5['close'], 14)
            stoch_k, stoch_d = ti.stochastic(df_m5, 14, 3)
            cci = ti.cci(df_m5, 20)
            williams = ti.williams_r(df_m5, 14)
            
            # Volatility
            bb_upper, bb_middle, bb_lower = ti.bollinger_bands(df_m5['close'], 20, 2.0)
            atr = ti.atr(df_m5, 14)
            
            # Support/Resistance
            sr_levels = ti.support_resistance(df_m5)
            fib_levels = ti.fibonacci_retracement(df_m5)
            pivots = ti.pivot_points(df_m5)
            
            # Current values
            curr_price = df_m5['close'].iloc[-1]
            
            analysis = {
                'symbol': symbol,
                'current_price': curr_price,
                'timestamp': df_m5['time'].iloc[-1].strftime('%Y-%m-%d %H:%M:%S'),
                
                'trend': {
                    'ema9': ema9.iloc[-1],
                    'ema21': ema21.iloc[-1],
                    'ema_trend': 'bullish' if ema9.iloc[-1] > ema21.iloc[-1] else 'bearish',
                    'macd': macd_line.iloc[-1],
                    'macd_signal': signal_line.iloc[-1],
                    'macd_histogram': histogram.iloc[-1],
                    'adx': adx.iloc[-1],
                    'trend_strength': 'strong' if adx.iloc[-1] > 25 else 'weak'
                },
                
                'momentum': {
                    'rsi': rsi.iloc[-1],
                    'rsi_state': 'overbought' if rsi.iloc[-1] > 70 else 'oversold' if rsi.iloc[-1] < 30 else 'neutral',
                    'stochastic_k': stoch_k.iloc[-1],
                    'stochastic_d': stoch_d.iloc[-1],
                    'cci': cci.iloc[-1],
                    'williams_r': williams.iloc[-1]
                },
                
                'volatility': {
                    'atr': atr.iloc[-1],
                    'bb_upper': bb_upper.iloc[-1],
                    'bb_middle': bb_middle.iloc[-1],
                    'bb_lower': bb_lower.iloc[-1],
                    'bb_position': 'upper' if curr_price > bb_upper.iloc[-1] else 'lower' if curr_price < bb_lower.iloc[-1] else 'middle'
                },
                
                'levels': {
                    'support': sr_levels['support'],
                    'resistance': sr_levels['resistance'],
                    'fib_618': fib_levels['fib_618'],
                    'fib_500': fib_levels['fib_500'],
                    'fib_382': fib_levels['fib_382'],
                    'pivot': pivots['pivot'],
                    'r1': pivots['r1'],
                    's1': pivots['s1']
                }
            }
            
            # H1 trend if available
            if df_h1 is not None:
                ema50_h1 = ti.ema(df_h1['close'], 50)
                ema200_h1 = ti.ema(df_h1['close'], 200)
                analysis['h1_trend'] = 'bullish' if ema50_h1.iloc[-1] > ema200_h1.iloc[-1] else 'bearish'
            
            # Try all strategies and show results
            strategy_results = []
            
            action, conf, details = self.strategies.strategy_1_trend_following(df_m5, df_h1)
            strategy_results.append({
                'name': 'Trend Following',
                'signal': action if action else 'None',
                'confidence': conf,
                'reason': details.get('reason', 'No signal')
            })
            
            action, conf, details = self.strategies.strategy_2_fibonacci_retracement(df_m5, df_h1)
            strategy_results.append({
                'name': 'Fibonacci',
                'signal': action if action else 'None',
                'confidence': conf,
                'reason': details.get('reason', 'No signal')
            })
            
            action, conf, details = self.strategies.strategy_3_mean_reversion(df_m5)
            strategy_results.append({
                'name': 'Mean Reversion',
                'signal': action if action else 'None',
                'confidence': conf,
                'reason': details.get('reason', 'No signal')
            })
            
            action, conf, details = self.strategies.strategy_4_breakout(df_m5, df_h1)
            strategy_results.append({
                'name': 'Breakout',
                'signal': action if action else 'None',
                'confidence': conf,
                'reason': details.get('reason', 'No signal')
            })
            
            action, conf, details = self.strategies.strategy_5_momentum(df_m5)
            strategy_results.append({
                'name': 'Momentum',
                'signal': action if action else 'None',
                'confidence': conf,
                'reason': details.get('reason', 'No signal')
            })
            
            analysis['strategy_signals'] = strategy_results
            
            return analysis
        
        except Exception as e:
            return {'error': str(e)}
    
    def find_zero_spread_symbols(self) -> List[str]:
        """
        Auto-detect all available zero-spread symbols
        """
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            return []
        
        zero_spread_symbols = []
        
        for symbol in all_symbols:
            symbol_name = symbol.name
            
            # Look for "zero" in name (case insensitive)
            if 'zero' in symbol_name.lower():
                # Check if it has tick data
                tick = mt5.symbol_info_tick(symbol_name)
                if tick and tick.bid > 0 and tick.ask > 0:
                    zero_spread_symbols.append(symbol_name)
        
        return sorted(zero_spread_symbols)

