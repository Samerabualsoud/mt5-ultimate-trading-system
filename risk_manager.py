"""
Risk Manager
============
Handles position sizing, correlation filtering, and risk limits
"""

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RiskManager:
    """Professional risk management system"""
    
    # Correlation groups (highly correlated pairs)
    CORRELATION_GROUPS = [
        ['EURUSDzero', 'GBPUSDzero', 'EURGBPzero'],
        ['AUDUSDzero', 'NZDUSDzero', 'AUDNZDzero'],
        ['USDJPYzero', 'EURJPYzero', 'GBPJPYzero'],
        ['USDCADzero', 'CADJPYzero'],
        ['USDCHFzero', 'CHFJPYzero'],
    ]
    
    def __init__(self, config: Dict):
        self.config = config
        self.risk_per_trade = config.get('risk_per_trade', 0.005)  # 0.5%
        self.max_concurrent_trades = config.get('max_concurrent_trades', 10)
        self.max_daily_loss = config.get('max_daily_loss', 0.03)  # 3%
        self.commission_per_lot = config.get('commission_per_lot', 6)
    
    def calculate_position_size(self, symbol: str, stop_loss_pips: float, 
                                confidence: float = 70) -> float:
        """
        Calculate position size based on risk and confidence
        
        Higher confidence = Larger position (up to 1.5x)
        Lower volatility = Larger position
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
            pip_size = 0.01
            pip_value = symbol_info.trade_tick_value * 1000
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_size = 0.10
            pip_value = symbol_info.trade_tick_value * 10
        else:
            pip_size = 0.0001
            pip_value = symbol_info.trade_tick_value * 10
        
        # Calculate lot size
        lot_size = risk_amount / (stop_loss_pips * pip_value)
        
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
        """
        ranked = []
        
        for opp in opportunities:
            # Estimate win rate from confidence
            # 50% confidence ≈ 55% win rate
            # 100% confidence ≈ 85% win rate
            win_rate = 0.55 + (opp['confidence'] - 50) / 100 * 0.30
            win_rate = max(0.55, min(win_rate, 0.85))
            
            lot_size = self.calculate_position_size(
                opp['symbol'], 
                opp['sl_pips'], 
                opp['confidence']
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

