"""
Enhanced Risk Manager
=====================
Advanced risk management with:
- Correlation-aware position sizing
- Drawdown protection (consecutive losses, hourly limits)
- Strategy-specific win rate estimation
- Position monitoring capabilities
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class EnhancedRiskManager:
    """Professional risk management with advanced features"""
    
    # Correlation groups (highly correlated pairs)
    CORRELATION_GROUPS = [
        ['EURUSDzero', 'GBPUSDzero', 'EURGBPzero'],
        ['AUDUSDzero', 'NZDUSDzero', 'AUDNZDzero'],
        ['USDJPYzero', 'EURJPYzero', 'GBPJPYzero'],
        ['USDCADzero', 'CADJPYzero'],
        ['USDCHFzero', 'CHFJPYzero'],
    ]
    
    # Currency exposure mapping
    CURRENCY_PAIRS = {
        'EURUSD': ('EUR', 'USD'),
        'GBPUSD': ('GBP', 'USD'),
        'USDJPY': ('USD', 'JPY'),
        'AUDUSD': ('AUD', 'USD'),
        'NZDUSD': ('NZD', 'USD'),
        'USDCAD': ('USD', 'CAD'),
        'USDCHF': ('USD', 'CHF'),
        'EURGBP': ('EUR', 'GBP'),
        'EURJPY': ('EUR', 'JPY'),
        'GBPJPY': ('GBP', 'JPY'),
        'AUDJPY': ('AUD', 'JPY'),
        'CADJPY': ('CAD', 'JPY'),
        'CHFJPY': ('CHF', 'JPY'),
        'AUDNZD': ('AUD', 'NZD'),
        'XAUUSD': ('XAU', 'USD'),  # Gold
    }
    
    # Strategy-specific base win rates (from historical data)
    STRATEGY_WIN_RATES = {
        'TREND_FOLLOWING': 0.48,
        'FIBONACCI_RETRACEMENT': 0.52,
        'MEAN_REVERSION': 0.68,
        'BREAKOUT': 0.55,
        'MOMENTUM': 0.62,
        'MULTI_TIMEFRAME_CONFLUENCE': 0.72
    }
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_per_trade = config.get('risk_per_trade', 0.005)  # 0.5%
        self.max_concurrent_trades = config.get('max_concurrent_trades', 10)
        self.max_daily_loss = config.get('max_daily_loss', 0.03)  # 3%
        self.max_hourly_loss = config.get('max_hourly_loss', 0.01)  # 1%
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        self.commission_per_lot = config.get('commission_per_lot', 6)
        
        # Track trade history for drawdown protection
        self.trade_history = []
        self.pause_until = None
    
    def get_currency_exposure(self, symbol: str, action: str, lot_size: float) -> Dict[str, float]:
        """
        Calculate currency exposure for a position
        Returns dict of {currency: exposure_in_lots}
        """
        # Remove 'zero' suffix if present
        clean_symbol = symbol.replace('zero', '').replace('Zero', '')
        
        currencies = self.CURRENCY_PAIRS.get(clean_symbol.upper(), (None, None))
        if not currencies[0]:
            return {}
        
        base_currency, quote_currency = currencies
        
        if action == 'BUY':
            # Buying base currency, selling quote currency
            return {
                base_currency: lot_size,
                quote_currency: -lot_size
            }
        else:  # SELL
            # Selling base currency, buying quote currency
            return {
                base_currency: -lot_size,
                quote_currency: lot_size
            }
    
    def calculate_total_currency_exposure(self, positions: List) -> Dict[str, float]:
        """
        Calculate total exposure per currency across all positions
        """
        exposure = {}
        
        for pos in positions:
            action = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
            pos_exposure = self.get_currency_exposure(pos.symbol, action, pos.volume)
            
            for currency, amount in pos_exposure.items():
                exposure[currency] = exposure.get(currency, 0) + amount
        
        return exposure
    
    def get_correlation_factor(self, symbol: str, action: str, positions: List) -> float:
        """
        Calculate correlation factor (0.0 to 1.0)
        Higher = more correlated exposure
        
        Returns:
        - 0.0: No correlation
        - 0.5: Moderate correlation
        - 1.0: High correlation
        """
        if not positions:
            return 0.0
        
        # Calculate proposed position exposure
        temp_lot = 0.1  # Temporary lot size for calculation
        new_exposure = self.get_currency_exposure(symbol, action, temp_lot)
        
        # Calculate existing exposure
        existing_exposure = self.calculate_total_currency_exposure(positions)
        
        # Calculate correlation score
        correlation_score = 0.0
        
        for currency, new_amount in new_exposure.items():
            existing_amount = existing_exposure.get(currency, 0)
            
            # Same direction = correlation
            if (new_amount > 0 and existing_amount > 0) or (new_amount < 0 and existing_amount < 0):
                # Normalize by total exposure
                correlation_score += abs(existing_amount) / temp_lot
        
        # Normalize to 0-1 range
        correlation_factor = min(1.0, correlation_score / 2.0)
        
        return correlation_factor
    
    def calculate_position_size(self, symbol: str, stop_loss_pips: float, 
                                confidence: float = 70, positions: List = None) -> float:
        """
        Calculate position size with correlation awareness
        
        Features:
        - Base size from risk amount
        - Confidence multiplier
        - Correlation reduction
        """
        account_info = mt5.account_info()
        if not account_info:
            return 0.01
        
        balance = account_info.balance
        
        # Base risk amount
        risk_amount = balance * self.risk_per_trade
        
        # Adjust for confidence (50-100% confidence → 0.7x to 1.3x multiplier)
        confidence_multiplier = 0.7 + (confidence - 50) / 100
        confidence_multiplier = max(0.7, min(confidence_multiplier, 1.3))
        
        risk_amount *= confidence_multiplier
        
        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0.01
        
        # Calculate pip value
        if 'JPY' in symbol:
            pip_value = symbol_info.trade_tick_value * 1000
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_value = symbol_info.trade_tick_value * 10
        else:
            pip_value = symbol_info.trade_tick_value * 10
        
        # Calculate base lot size
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
        # Apply correlation reduction
        if positions:
            correlation_factor = self.get_correlation_factor(symbol, 'BUY', positions)
            if correlation_factor > 0.3:
                reduction = 1.0 - (correlation_factor * 0.5)  # Reduce up to 50%
                lot_size *= reduction
                logger.info(f"📉 Correlation factor {correlation_factor:.2f} - reducing position size by {(1-reduction)*100:.0f}%")
        
        # Round and enforce limits
        lot_size = round(lot_size, 2)
        lot_size = max(symbol_info.volume_min, lot_size)
        lot_size = min(symbol_info.volume_max, lot_size)
        lot_size = min(5.0, lot_size)  # Max 5 lots per trade
        
        return lot_size
    
    def check_correlation_conflict(self, symbol: str, action: str, 
                                   open_positions: List) -> bool:
        """
        Check if new trade conflicts with existing positions
        Returns True if conflict (should not trade)
        """
        if not open_positions:
            return False
        
        # Find correlation group for this symbol
        symbol_group = None
        for group in self.CORRELATION_GROUPS:
            if symbol in group:
                symbol_group = group
                break
        
        if not symbol_group:
            return False  # Not in any correlation group
        
        # Check if we already have positions in this group
        for pos in open_positions:
            if pos.symbol in symbol_group:
                # Same direction = OK (correlation works for us)
                # Opposite direction = CONFLICT (correlation works against us)
                pos_type = 'BUY' if pos.type == mt5.ORDER_TYPE_BUY else 'SELL'
                
                if pos_type != action:
                    logger.info(f"⚠️  Correlation conflict: {symbol} {action} conflicts with {pos.symbol} {pos_type}")
                    return True
        
        return False
    
    def check_drawdown_protection(self) -> Tuple[bool, str]:
        """
        Check if drawdown protection triggered
        
        Returns (can_trade, reason)
        """
        # Check if paused
        if self.pause_until and time.time() < self.pause_until:
            remaining = int(self.pause_until - time.time())
            return False, f"Trading paused for {remaining//60} more minutes"
        
        if not self.trade_history:
            return True, "OK"
        
        # Check consecutive losses
        consecutive_losses = 0
        for trade in reversed(self.trade_history):
            if trade.get('profit', 0) < 0:
                consecutive_losses += 1
            else:
                break
        
        if consecutive_losses >= self.max_consecutive_losses:
            # Pause trading for 1 hour
            self.pause_until = time.time() + 3600
            logger.warning(f"🛑 {consecutive_losses} consecutive losses - Pausing trading for 1 hour")
            return False, f"{consecutive_losses} consecutive losses - paused"
        
        # Check hourly drawdown
        one_hour_ago = time.time() - 3600
        recent_trades = [t for t in self.trade_history if t.get('timestamp', 0) > one_hour_ago]
        
        if recent_trades:
            account_info = mt5.account_info()
            if account_info:
                hourly_pnl = sum(t.get('profit', 0) for t in recent_trades)
                hourly_pnl_pct = hourly_pnl / account_info.balance
                
                if hourly_pnl_pct < -self.max_hourly_loss:
                    # Pause trading for 1 hour
                    self.pause_until = time.time() + 3600
                    logger.warning(f"🛑 Hourly loss limit ({hourly_pnl_pct*100:.2f}%) - Pausing trading for 1 hour")
                    return False, f"Hourly loss limit reached ({hourly_pnl_pct*100:.2f}%)"
        
        return True, "OK"
    
    def check_daily_loss_limit(self, start_balance: float) -> bool:
        """
        Check if daily loss limit has been reached
        Returns True if should stop trading
        """
        account_info = mt5.account_info()
        if not account_info:
            return True
        
        current_balance = account_info.balance
        daily_pnl_pct = (current_balance - start_balance) / start_balance
        
        if daily_pnl_pct <= -self.max_daily_loss:
            logger.warning(f"🛑 Daily loss limit reached: {daily_pnl_pct*100:.2f}%")
            return True
        
        return False
    
    def check_margin_level(self) -> bool:
        """
        Check if margin level is sufficient
        Returns True if OK to trade
        """
        account_info = mt5.account_info()
        if not account_info:
            return False
        
        if account_info.margin == 0:
            return True  # No positions, margin OK
        
        margin_level = account_info.margin_level
        min_margin = self.config.get('min_margin_level', 500)
        
        if margin_level < min_margin:
            logger.warning(f"⚠️  Low margin level: {margin_level:.2f}%")
            return False
        
        return True
    
    def can_open_new_position(self, symbol: str, action: str, 
                             start_balance: float) -> Tuple[bool, str]:
        """
        Comprehensive check if we can open a new position
        
        Returns (can_trade, reason)
        """
        # Check drawdown protection first
        can_trade, reason = self.check_drawdown_protection()
        if not can_trade:
            return False, reason
        
        # Check daily loss limit
        if self.check_daily_loss_limit(start_balance):
            return False, "Daily loss limit reached"
        
        # Check margin
        if not self.check_margin_level():
            return False, "Insufficient margin"
        
        # Check max concurrent trades
        positions = mt5.positions_get()
        if positions and len(positions) >= self.max_concurrent_trades:
            return False, f"Max concurrent trades ({self.max_concurrent_trades}) reached"
        
        # Check correlation conflicts
        if positions and self.check_correlation_conflict(symbol, action, positions):
            return False, "Correlation conflict with existing position"
        
        return True, "OK"
    
    def record_trade(self, trade_data: Dict):
        """Record trade for drawdown protection"""
        trade_data['timestamp'] = time.time()
        self.trade_history.append(trade_data)
        
        # Keep only last 100 trades
        if len(self.trade_history) > 100:
            self.trade_history = self.trade_history[-100:]
    
    def estimate_win_rate(self, strategy: str, confidence: float) -> float:
        """
        Estimate win rate based on strategy and confidence
        
        Uses strategy-specific base rates + confidence adjustment
        """
        base_rate = self.STRATEGY_WIN_RATES.get(strategy, 0.55)
        
        # Adjust based on confidence (50-100 → -5% to +10%)
        adjustment = (confidence - 75) / 100 * 0.15
        
        win_rate = base_rate + adjustment
        
        # Clamp to reasonable range
        return max(0.40, min(0.85, win_rate))
    
    def calculate_expected_profit(self, lot_size: float, tp_pips: float, 
                                  symbol: str) -> float:
        """Calculate expected profit for a trade"""
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0
        
        if 'JPY' in symbol:
            pip_value = symbol_info.trade_tick_value * 1000
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_value = symbol_info.trade_tick_value * 10
        else:
            pip_value = symbol_info.trade_tick_value * 10
        
        gross_profit = lot_size * tp_pips * pip_value
        commission = lot_size * self.commission_per_lot
        net_profit = gross_profit - commission
        
        return net_profit
    
    def calculate_expected_loss(self, lot_size: float, sl_pips: float, 
                               symbol: str) -> float:
        """Calculate expected loss for a trade"""
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0
        
        if 'JPY' in symbol:
            pip_value = symbol_info.trade_tick_value * 1000
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_value = symbol_info.trade_tick_value * 10
        else:
            pip_value = symbol_info.trade_tick_value * 10
        
        gross_loss = lot_size * sl_pips * pip_value
        commission = lot_size * self.commission_per_lot
        total_loss = gross_loss + commission
        
        return total_loss
    
    def rank_opportunities(self, opportunities: List[Dict]) -> List[Dict]:
        """
        Rank opportunities by expected value
        
        Expected Value = (Win Rate × Expected Profit) - (Loss Rate × Expected Loss)
        Uses strategy-specific win rates
        """
        ranked = []
        positions = mt5.positions_get() or []
        
        for opp in opportunities:
            # Use strategy-specific win rate estimation
            strategy = opp.get('strategy', 'UNKNOWN')
            win_rate = self.estimate_win_rate(strategy, opp['confidence'])
            
            # Calculate position size with correlation awareness
            lot_size = self.calculate_position_size(
                opp['symbol'], 
                opp['sl_pips'], 
                opp['confidence'],
                positions
            )
            
            expected_profit = self.calculate_expected_profit(
                lot_size, 
                opp['tp_pips'], 
                opp['symbol']
            )
            
            expected_loss = self.calculate_expected_loss(
                lot_size, 
                opp['sl_pips'], 
                opp['symbol']
            )
            
            expected_value = (win_rate * expected_profit) - ((1 - win_rate) * expected_loss)
            
            opp['expected_value'] = expected_value
            opp['estimated_win_rate'] = win_rate
            opp['lot_size'] = lot_size
            
            ranked.append(opp)
        
        # Sort by expected value (highest first)
        ranked.sort(key=lambda x: x['expected_value'], reverse=True)
        
        return ranked

