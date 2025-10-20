"""
Improved Opportunity Scanner
============================
Scans 50+ pairs with enhanced strategies and dynamic SL/TP
"""

import MetaTrader5 as mt5
import pandas as pd
from typing import List, Dict, Tuple
from strategies_improved import ImprovedTradingStrategies
import logging

logger = logging.getLogger(__name__)


class ImprovedOpportunityScanner:
    """Enhanced scanner with dynamic risk management"""
    
    TIMEFRAME_MAP = {
        'M5': mt5.TIMEFRAME_M5,
        'M15': mt5.TIMEFRAME_M15,
        'H1': mt5.TIMEFRAME_H1,
        'H4': mt5.TIMEFRAME_H4,
    }
    
    def __init__(self):
        self.strategies = ImprovedTradingStrategies()
        self.last_scan_results = []
    
    def scan_all_pairs(self, symbols: List[str], enable_multi_tf: bool = False) -> List[Dict]:
        """
        Scan all pairs with all improved strategies
        
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
                action, conf, details = self.strategies.strategy_1_trend_following(df_m5, df_h1, symbol)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 2: Fibonacci
                action, conf, details = self.strategies.strategy_2_fibonacci_retracement(df_m5, df_h1, symbol)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 3: Mean Reversion
                action, conf, details = self.strategies.strategy_3_mean_reversion(df_m5, symbol)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 4: Breakout
                action, conf, details = self.strategies.strategy_4_breakout(df_m5, df_h1, symbol)
                if action:
                    strategy_results.append((action, conf, details))
                
                # Strategy 5: Momentum
                action, conf, details = self.strategies.strategy_5_momentum(df_m5, symbol)
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
                            df_m5, df_m15, df_h1, df_h4, symbol
                        )
                        if action:
                            strategy_results.append((action, conf, details))
                
                # Add all signals for this symbol
                for action, conf, details in strategy_results:
                    opportunities.append({
                        'symbol': symbol,
                        'action': action,
                        'confidence': conf,
                        'strategy': details['strategy'],
                        'sl_pips': details['sl_pips'],
                        'tp_pips': details['tp_pips'],
                        'use_trailing_stop': details.get('use_trailing_stop', False),
                        'trailing_distance_pips': details.get('trailing_distance_pips', None),
                        'reason': details['reason'],
                        'market_structure': details.get('market_structure', {})
                    })
            
            except Exception as e:
                logger.debug(f"Error scanning {symbol}: {e}")
                continue
        
        # Sort by confidence (highest first)
        opportunities.sort(key=lambda x: x['confidence'], reverse=True)
        
        self.last_scan_results = opportunities
        return opportunities
    
    def find_zero_spread_symbols(self) -> List[str]:
        """
        Auto-detect zero-spread symbols
        
        Returns list of symbols with 'zero' in name
        """
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.warning("Could not get symbols list")
            return []
        
        zero_spread_symbols = []
        
        for symbol in all_symbols:
            symbol_name = symbol.name
            
            # Look for zero-spread indicators
            if 'zero' in symbol_name.lower() or 'raw' in symbol_name.lower():
                # Verify it's tradeable
                if symbol.visible and symbol.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL:
                    zero_spread_symbols.append(symbol_name)
        
        # If no zero-spread symbols found, return standard majors
        if not zero_spread_symbols:
            logger.info("No zero-spread symbols found, using standard majors")
            standard_symbols = [
                'EURUSD', 'GBPUSD', 'USDJPY', 'USDCHF', 'AUDUSD', 'USDCAD', 'NZDUSD',
                'EURJPY', 'GBPJPY', 'EURGBP', 'AUDJPY', 'EURAUD', 'EURCHF', 'AUDNZD',
                'NZDJPY', 'GBPAUD', 'GBPCAD', 'EURNZD', 'AUDCAD', 'GBPCHF', 'AUDCHF',
                'EURCAD', 'CADJPY', 'GBPNZD', 'CADCHF', 'CHFJPY', 'NZDCAD', 'NZDCHF'
            ]
            
            # Filter to only available symbols
            available_symbols = [s.name for s in all_symbols]
            zero_spread_symbols = [s for s in standard_symbols if s in available_symbols]
        
        logger.info(f"Found {len(zero_spread_symbols)} tradeable symbols")
        return zero_spread_symbols

