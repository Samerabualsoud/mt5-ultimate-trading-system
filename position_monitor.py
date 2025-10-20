"""
Position Monitor
================
Monitors and manages open positions:
- Break-even adjustment
- Partial profit taking
- Emergency exits
- Trailing stop updates
"""

import MetaTrader5 as mt5
import logging
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)


class PositionMonitor:
    """Advanced position management system"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.breakeven_pips = config.get('breakeven_pips', 15)  # Move to BE after 15 pips profit
        self.partial_profit_pips = config.get('partial_profit_pips', 30)  # Take 50% at 30 pips
        self.enable_breakeven = config.get('enable_breakeven', True)
        self.enable_partial_profits = config.get('enable_partial_profits', False)
        
        # Track which positions have been adjusted
        self.breakeven_positions = set()
        self.partial_closed_positions = set()
    
    def get_symbol_pip_size(self, symbol: str) -> float:
        """Get pip size for symbol"""
        if 'JPY' in symbol:
            return 0.01
        elif 'XAU' in symbol or 'GOLD' in symbol:
            return 0.10
        elif 'XAG' in symbol or 'SILVER' in symbol:
            return 0.01
        else:
            return 0.0001
    
    def calculate_position_profit_pips(self, position) -> float:
        """Calculate position profit in pips"""
        pip_size = self.get_symbol_pip_size(position.symbol)
        
        if position.type == mt5.ORDER_TYPE_BUY:
            # BUY: profit = (current_price - open_price) / pip_size
            current_price = mt5.symbol_info_tick(position.symbol).bid
            profit_pips = (current_price - position.price_open) / pip_size
        else:  # SELL
            # SELL: profit = (open_price - current_price) / pip_size
            current_price = mt5.symbol_info_tick(position.symbol).ask
            profit_pips = (position.price_open - current_price) / pip_size
        
        return profit_pips
    
    def move_to_breakeven(self, position) -> bool:
        """
        Move stop loss to break-even (entry price)
        
        Returns True if successful
        """
        if position.ticket in self.breakeven_positions:
            return False  # Already moved to BE
        
        profit_pips = self.calculate_position_profit_pips(position)
        
        if profit_pips < self.breakeven_pips:
            return False  # Not enough profit yet
        
        # Calculate break-even price (entry + spread/commission buffer)
        pip_size = self.get_symbol_pip_size(position.symbol)
        buffer_pips = 2  # 2 pip buffer to avoid premature stop-out
        
        if position.type == mt5.ORDER_TYPE_BUY:
            new_sl = position.price_open + (buffer_pips * pip_size)
        else:  # SELL
            new_sl = position.price_open - (buffer_pips * pip_size)
        
        # Modify position
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": new_sl,
            "tp": position.tp,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.breakeven_positions.add(position.ticket)
            logger.info(f"✅ Moved to break-even: {position.symbol} #{position.ticket} (profit: {profit_pips:.1f} pips)")
            return True
        else:
            error = result.comment if result else "Unknown error"
            logger.error(f"❌ Failed to move to break-even: {position.symbol} #{position.ticket} - {error}")
            return False
    
    def close_partial_position(self, position, close_fraction: float = 0.5) -> bool:
        """
        Close partial position (e.g., 50%)
        
        Returns True if successful
        """
        if position.ticket in self.partial_closed_positions:
            return False  # Already took partial profits
        
        profit_pips = self.calculate_position_profit_pips(position)
        
        if profit_pips < self.partial_profit_pips:
            return False  # Not enough profit yet
        
        # Calculate volume to close
        close_volume = round(position.volume * close_fraction, 2)
        
        # Ensure minimum volume
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info or close_volume < symbol_info.volume_min:
            return False
        
        # Close partial position
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": close_volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
            "deviation": 20,
            "magic": position.magic,
            "comment": f"Partial close {int(close_fraction*100)}%",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            self.partial_closed_positions.add(position.ticket)
            logger.info(f"✅ Partial close ({int(close_fraction*100)}%): {position.symbol} #{position.ticket} (profit: {profit_pips:.1f} pips)")
            return True
        else:
            error = result.comment if result else "Unknown error"
            logger.error(f"❌ Failed partial close: {position.symbol} #{position.ticket} - {error}")
            return False
    
    def check_emergency_exit(self, position) -> bool:
        """
        Check if position should be emergency closed
        
        Conditions:
        - Extreme adverse movement (e.g., -50 pips beyond SL)
        - Symbol trading halted
        - Other emergency conditions
        
        Returns True if position was closed
        """
        # Check if symbol is tradeable
        symbol_info = mt5.symbol_info(position.symbol)
        if not symbol_info or not symbol_info.visible or not symbol_info.trade_mode:
            logger.warning(f"⚠️  Symbol {position.symbol} not tradeable - closing position #{position.ticket}")
            return self.close_position(position, "Symbol not tradeable")
        
        # Check for extreme adverse movement
        profit_pips = self.calculate_position_profit_pips(position)
        
        # If loss exceeds 2x the expected SL, emergency close
        if profit_pips < -100:  # More than 100 pips loss (extreme)
            logger.warning(f"⚠️  Extreme loss detected: {position.symbol} #{position.ticket} ({profit_pips:.1f} pips)")
            return self.close_position(position, f"Emergency exit: {profit_pips:.1f} pips loss")
        
        return False
    
    def close_position(self, position, reason: str = "") -> bool:
        """
        Close a position completely
        
        Returns True if successful
        """
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": mt5.ORDER_TYPE_SELL if position.type == mt5.ORDER_TYPE_BUY else mt5.ORDER_TYPE_BUY,
            "price": mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
            "deviation": 20,
            "magic": position.magic,
            "comment": reason[:31] if reason else "Manual close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"✅ Position closed: {position.symbol} #{position.ticket} - {reason}")
            return True
        else:
            error = result.comment if result else "Unknown error"
            logger.error(f"❌ Failed to close position: {position.symbol} #{position.ticket} - {error}")
            return False
    
    def monitor_positions(self, trailing_stop_positions: Dict = None):
        """
        Monitor all open positions and apply management rules
        
        Args:
            trailing_stop_positions: Dict of positions with trailing stops (from main bot)
        """
        positions = mt5.positions_get()
        if not positions:
            return
        
        for position in positions:
            # Skip positions with trailing stops (managed by main bot)
            if trailing_stop_positions and position.ticket in trailing_stop_positions:
                continue
            
            # Check emergency exit first
            if self.check_emergency_exit(position):
                continue
            
            # Move to break-even if enabled and conditions met
            if self.enable_breakeven:
                if self.move_to_breakeven(position):
                    continue  # Position modified, move to next
            
            # Take partial profits if enabled and conditions met
            if self.enable_partial_profits:
                if self.close_partial_position(position, 0.5):
                    # After partial close, move remaining to break-even
                    time.sleep(0.5)  # Small delay
                    self.move_to_breakeven(position)
    
    def get_position_status(self, position) -> Dict:
        """
        Get detailed status of a position
        
        Returns dict with position metrics
        """
        profit_pips = self.calculate_position_profit_pips(position)
        pip_size = self.get_symbol_pip_size(position.symbol)
        
        # Calculate SL and TP in pips
        if position.type == mt5.ORDER_TYPE_BUY:
            sl_pips = (position.price_open - position.sl) / pip_size if position.sl > 0 else 0
            tp_pips = (position.tp - position.price_open) / pip_size if position.tp > 0 else 0
        else:
            sl_pips = (position.sl - position.price_open) / pip_size if position.sl > 0 else 0
            tp_pips = (position.price_open - position.tp) / pip_size if position.tp > 0 else 0
        
        return {
            'ticket': position.ticket,
            'symbol': position.symbol,
            'type': 'BUY' if position.type == mt5.ORDER_TYPE_BUY else 'SELL',
            'volume': position.volume,
            'open_price': position.price_open,
            'current_price': mt5.symbol_info_tick(position.symbol).bid if position.type == mt5.ORDER_TYPE_BUY else mt5.symbol_info_tick(position.symbol).ask,
            'profit_usd': position.profit,
            'profit_pips': profit_pips,
            'sl': position.sl,
            'tp': position.tp,
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'at_breakeven': position.ticket in self.breakeven_positions,
            'partial_closed': position.ticket in self.partial_closed_positions,
        }
    
    def get_all_positions_status(self) -> List[Dict]:
        """Get status of all open positions"""
        positions = mt5.positions_get()
        if not positions:
            return []
        
        return [self.get_position_status(pos) for pos in positions]
    
    def cleanup_tracking(self):
        """Remove closed positions from tracking sets"""
        positions = mt5.positions_get()
        if not positions:
            self.breakeven_positions.clear()
            self.partial_closed_positions.clear()
            return
        
        open_tickets = {pos.ticket for pos in positions}
        
        # Remove tickets that are no longer open
        self.breakeven_positions = {t for t in self.breakeven_positions if t in open_tickets}
        self.partial_closed_positions = {t for t in self.partial_closed_positions if t in open_tickets}

