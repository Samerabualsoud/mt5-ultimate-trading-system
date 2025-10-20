"""
Ultimate Trading Bot V2
=======================
Comprehensive trading bot with all improvements:
- Enhanced risk management (correlation-aware, drawdown protection)
- Position monitoring (break-even, partial profits)
- Improved SL/TP calculations (dynamic, structure-aware)
- Trailing stops
- Configuration validation
- Robust error handling
"""

import MetaTrader5 as mt5
import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, List
import os

# Import enhanced modules
from risk_manager_enhanced import EnhancedRiskManager
from position_monitor import PositionMonitor
from config_validator import ConfigValidator

# Try to import improved scanner, fall back to original
try:
    from opportunity_scanner_improved import ImprovedOpportunityScanner as OpportunityScanner
    logger_msg = "Using improved opportunity scanner"
except ImportError:
    from opportunity_scanner import OpportunityScanner
    logger_msg = "Using original opportunity scanner"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_bot_v2.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UltimateTradingBotV2:
    """
    Professional trading bot with comprehensive risk management
    """
    
    def __init__(self, config: Dict):
        # Validate configuration
        is_valid, errors = ConfigValidator.validate_config(config)
        if not is_valid:
            raise ValueError(f"Invalid configuration:\n" + "\n".join(errors))
        
        self.config = ConfigValidator.get_safe_config(config)
        ConfigValidator.print_config_summary(self.config)
        
        # Initialize MT5
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")
        
        if not mt5.login(self.config['mt5_login'], 
                        password=self.config['mt5_password'],
                        server=self.config['mt5_server']):
            raise Exception(f"MT5 login failed: {mt5.last_error()}")
        
        # Initialize components
        self.risk_manager = EnhancedRiskManager(self.config)
        self.position_monitor = PositionMonitor(self.config)
        self.scanner = OpportunityScanner()
        
        # Auto-detect symbols
        if self.config.get('auto_detect_symbols', True):
            self.symbols = self.scanner.find_zero_spread_symbols()
            logger.info(f"Auto-detected {len(self.symbols)} zero-spread symbols")
        else:
            self.symbols = self.config['symbols']
        
        # Trading state
        self.start_balance = mt5.account_info().balance
        self.trade_history = []
        self.trailing_stop_positions = {}
        self.magic_number = 999003  # Unique magic number for V2
        
        # Load trade history if exists
        self.history_file = 'ultimate_trade_history_v2.json'
        self.load_trade_history()
        
        logger.info("=" * 80)
        logger.info("🚀 ULTIMATE TRADING BOT V2 - INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"Account: {self.config['mt5_login']} | Server: {self.config['mt5_server']}")
        logger.info(f"Start Balance: ${self.start_balance:,.2f}")
        logger.info(f"Symbols: {len(self.symbols)}")
        logger.info(f"Magic Number: {self.magic_number}")
        logger.info(logger_msg)
        logger.info("=" * 80)
    
    def load_trade_history(self):
        """Load trade history from file"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.trade_history = json.load(f)
                logger.info(f"Loaded {len(self.trade_history)} trades from history")
                
                # Update risk manager's trade history for drawdown protection
                self.risk_manager.trade_history = self.trade_history[-100:]
            except Exception as e:
                logger.error(f"Error loading trade history: {e}")
    
    def save_trade_history(self):
        """Save trade history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.trade_history, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving trade history: {e}")
    
    def scan_and_trade(self):
        """Main trading logic"""
        logger.info(f"\n{'='*80}")
        logger.info(f"🔍 SCANNING {len(self.symbols)} PAIRS")
        logger.info(f"Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"{'='*80}")
        
        # Check if we can trade
        can_trade, reason = self.risk_manager.can_open_new_position(
            '', '', self.start_balance
        )
        
        if not can_trade:
            logger.warning(f"🛑 Cannot trade: {reason}")
            return
        
        # Scan for opportunities
        enable_multi_tf = self.config.get('enable_multi_timeframe', True)
        opportunities = self.scanner.scan_all_pairs(self.symbols, enable_multi_tf=enable_multi_tf)
        
        if not opportunities:
            logger.info("⏸️  No opportunities found")
            return
        
        logger.info(f"✅ Found {len(opportunities)} potential opportunities")
        
        # Filter by minimum confidence
        min_confidence = self.config.get('min_confidence', 50)
        opportunities = [opp for opp in opportunities if opp['confidence'] >= min_confidence]
        
        if not opportunities:
            logger.info(f"⏸️  No opportunities above {min_confidence}% confidence")
            return
        
        logger.info(f"📊 {len(opportunities)} opportunities above {min_confidence}% confidence")
        
        # Rank opportunities by expected value
        ranked_opportunities = self.risk_manager.rank_opportunities(opportunities)
        
        # Display top opportunities
        logger.info("\n🎯 TOP OPPORTUNITIES:")
        logger.info("-" * 80)
        for i, opp in enumerate(ranked_opportunities[:5], 1):
            logger.info(
                f"{i}. [{opp['symbol']}] {opp['action']} | "
                f"Conf: {opp['confidence']}% | "
                f"Strategy: {opp['strategy']} | "
                f"EV: ${opp['expected_value']:.2f} | "
                f"Win Rate: {opp['estimated_win_rate']*100:.1f}% | "
                f"Lot: {opp['lot_size']}"
            )
        logger.info("-" * 80)
        
        # Try to execute best opportunity
        positions = mt5.positions_get()
        
        for opp in ranked_opportunities:
            # Check if we can still open positions
            can_trade, reason = self.risk_manager.can_open_new_position(
                opp['symbol'], opp['action'], self.start_balance
            )
            
            if not can_trade:
                logger.info(f"⏸️  Skipping {opp['symbol']}: {reason}")
                continue
            
            # Execute trade
            success = self.execute_trade(opp)
            
            if success:
                break  # Only open one trade per scan
    
    def execute_trade(self, opportunity: Dict) -> bool:
        """Execute a trade"""
        symbol = opportunity['symbol']
        action = opportunity['action']
        lot_size = opportunity['lot_size']
        sl_pips = opportunity['sl_pips']
        tp_pips = opportunity['tp_pips']
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"❌ Cannot get tick for {symbol}")
            return False
        
        price = tick.ask if action == 'BUY' else tick.bid
        
        # Calculate SL and TP prices
        pip_size = self.get_symbol_pip_size(symbol)
        
        if action == 'BUY':
            sl_price = price - (sl_pips * pip_size)
            tp_price = price + (tp_pips * pip_size)
            order_type = mt5.ORDER_TYPE_BUY
        else:  # SELL
            sl_price = price + (sl_pips * pip_size)
            tp_price = price - (tp_pips * pip_size)
            order_type = mt5.ORDER_TYPE_SELL
        
        # Prepare order request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl_price,
            "tp": tp_price,
            "deviation": 20,
            "magic": self.magic_number,
            "comment": f"V2_{opportunity['strategy']}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"✅ TRADE EXECUTED: {symbol} {action}")
            logger.info(f"   Lot Size: {lot_size} | Price: {price:.5f}")
            logger.info(f"   SL: {sl_price:.5f} ({sl_pips:.1f} pips) | TP: {tp_price:.5f} ({tp_pips:.1f} pips)")
            logger.info(f"   Strategy: {opportunity['strategy']} | Confidence: {opportunity['confidence']}%")
            logger.info(f"   Expected Value: ${opportunity['expected_value']:.2f}")
            logger.info(f"   Ticket: #{result.order}")
            
            # Track trailing stop if applicable
            if opportunity.get('use_trailing_stop', False):
                self.trailing_stop_positions[result.order] = {
                    'symbol': symbol,
                    'action': action,
                    'trailing_distance_pips': opportunity.get('trailing_distance_pips', 20),
                    'highest_price': price if action == 'BUY' else None,
                    'lowest_price': price if action == 'SELL' else None,
                }
                logger.info(f"   🔄 Trailing stop enabled ({opportunity.get('trailing_distance_pips', 20)} pips)")
            
            # Record trade
            trade_record = {
                'timestamp': time.time(),
                'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'ticket': result.order,
                'symbol': symbol,
                'action': action,
                'lot_size': lot_size,
                'price': price,
                'sl': sl_price,
                'tp': tp_price,
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'strategy': opportunity['strategy'],
                'confidence': opportunity['confidence'],
                'expected_value': opportunity['expected_value'],
            }
            
            self.trade_history.append(trade_record)
            self.save_trade_history()
            
            return True
        else:
            error = result.comment if result else "Unknown error"
            logger.error(f"❌ Trade failed: {symbol} {action} - {error}")
            return False
    
    def manage_trailing_stops(self):
        """Update trailing stops for active positions"""
        if not self.trailing_stop_positions:
            return
        
        positions = mt5.positions_get()
        if not positions:
            self.trailing_stop_positions.clear()
            return
        
        position_tickets = {pos.ticket: pos for pos in positions}
        
        # Remove closed positions from tracking
        closed_tickets = [ticket for ticket in self.trailing_stop_positions.keys() 
                         if ticket not in position_tickets]
        for ticket in closed_tickets:
            del self.trailing_stop_positions[ticket]
        
        # Update trailing stops
        for ticket, trail_data in list(self.trailing_stop_positions.items()):
            if ticket not in position_tickets:
                continue
            
            position = position_tickets[ticket]
            symbol = position.symbol
            action = trail_data['action']
            trailing_distance_pips = trail_data['trailing_distance_pips']
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue
            
            current_price = tick.bid if action == 'BUY' else tick.ask
            pip_size = self.get_symbol_pip_size(symbol)
            
            if action == 'BUY':
                # Update highest price
                if trail_data['highest_price'] is None or current_price > trail_data['highest_price']:
                    trail_data['highest_price'] = current_price
                
                # Calculate new trailing stop
                new_sl = trail_data['highest_price'] - (trailing_distance_pips * pip_size)
                
                # Only update if new SL is higher than current SL
                if new_sl > position.sl:
                    self.modify_position_sl(position, new_sl)
            
            else:  # SELL
                # Update lowest price
                if trail_data['lowest_price'] is None or current_price < trail_data['lowest_price']:
                    trail_data['lowest_price'] = current_price
                
                # Calculate new trailing stop
                new_sl = trail_data['lowest_price'] + (trailing_distance_pips * pip_size)
                
                # Only update if new SL is lower than current SL
                if new_sl < position.sl or position.sl == 0:
                    self.modify_position_sl(position, new_sl)
    
    def modify_position_sl(self, position, new_sl: float) -> bool:
        """Modify position stop loss"""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": position.ticket,
            "symbol": position.symbol,
            "sl": new_sl,
            "tp": position.tp,
        }
        
        result = mt5.order_send(request)
        
        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info(f"🔄 Trailing stop updated: {position.symbol} #{position.ticket} - New SL: {new_sl:.5f}")
            return True
        else:
            error = result.comment if result else "Unknown error"
            logger.error(f"❌ Failed to update trailing stop: {position.symbol} #{position.ticket} - {error}")
            return False
    
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
    
    def update_closed_positions(self):
        """Update trade history with closed positions"""
        # Get recent deals (closed positions)
        from_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        deals = mt5.history_deals_get(from_date, datetime.now())
        
        if not deals:
            return
        
        # Update trade history with results
        for deal in deals:
            if deal.magic != self.magic_number:
                continue
            
            # Find corresponding trade in history
            for trade in self.trade_history:
                if trade.get('ticket') == deal.position_id and 'profit' not in trade:
                    trade['profit'] = deal.profit
                    trade['close_time'] = datetime.fromtimestamp(deal.time).strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Record in risk manager for drawdown protection
                    self.risk_manager.record_trade(trade)
                    
                    logger.info(f"💰 Position closed: {trade['symbol']} #{deal.position_id} - "
                              f"Profit: ${deal.profit:.2f}")
        
        self.save_trade_history()
    
    def print_status(self):
        """Print current status"""
        account_info = mt5.account_info()
        if not account_info:
            return
        
        positions = mt5.positions_get()
        num_positions = len(positions) if positions else 0
        
        # Calculate daily P&L
        daily_pnl = account_info.balance - self.start_balance
        daily_pnl_pct = (daily_pnl / self.start_balance) * 100
        
        # Calculate today's trades
        today = datetime.now().strftime('%Y-%m-%d')
        today_trades = [t for t in self.trade_history if t.get('datetime', '').startswith(today)]
        today_wins = [t for t in today_trades if t.get('profit', 0) > 0]
        today_losses = [t for t in today_trades if t.get('profit', 0) < 0]
        
        logger.info("\n" + "=" * 80)
        logger.info("📊 STATUS REPORT")
        logger.info("=" * 80)
        logger.info(f"Balance: ${account_info.balance:,.2f} | Equity: ${account_info.equity:,.2f}")
        logger.info(f"Daily P&L: ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)")
        logger.info(f"Open Positions: {num_positions}/{self.config['max_concurrent_trades']}")
        
        if num_positions > 0:
            total_profit = sum(pos.profit for pos in positions)
            logger.info(f"Floating P&L: ${total_profit:+,.2f}")
        
        logger.info(f"Today's Trades: {len(today_trades)} | Wins: {len(today_wins)} | Losses: {len(today_losses)}")
        
        if today_trades:
            win_rate = len(today_wins) / len(today_trades) * 100
            logger.info(f"Today's Win Rate: {win_rate:.1f}%")
        
        logger.info("=" * 80)
    
    def run(self):
        """Main bot loop"""
        scan_interval = self.config.get('scan_interval', 45)
        
        try:
            while True:
                # Update closed positions
                self.update_closed_positions()
                
                # Manage trailing stops
                self.manage_trailing_stops()
                
                # Monitor positions (break-even, partial profits)
                self.position_monitor.monitor_positions(self.trailing_stop_positions)
                
                # Clean up position monitor tracking
                self.position_monitor.cleanup_tracking()
                
                # Scan and trade
                self.scan_and_trade()
                
                # Print status
                self.print_status()
                
                # Wait for next scan
                logger.info(f"\n⏰ Next scan in {scan_interval} seconds...\n")
                time.sleep(scan_interval)
        
        except KeyboardInterrupt:
            logger.info("\n⏹️  Bot stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error: {e}", exc_info=True)
        finally:
            mt5.shutdown()
            logger.info("👋 MT5 connection closed")


if __name__ == "__main__":
    try:
        from ultimate_config import CONFIG
    except ImportError:
        logger.error("❌ ultimate_config.py not found!")
        logger.error("Please create ultimate_config.py with your MT5 credentials")
        exit(1)
    
    bot = UltimateTradingBotV2(CONFIG)
    bot.run()

