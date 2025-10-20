"""
Improved Ultimate Scalping Bot
================================
Enhanced version with dynamic SL/TP and trailing stops
"""

import MetaTrader5 as mt5
import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, List
from opportunity_scanner_improved import ImprovedOpportunityScanner
from risk_manager import RiskManager
from market_analyzer import MarketAnalyzer

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_scalping_bot_improved.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ImprovedUltimateScalpingBot:
    """Enhanced trading system with intelligent risk management"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.start_balance = 0
        self.daily_trades = 0
        self.trade_history = []
        self.strategy_performance = {
            'TREND_FOLLOWING': {'wins': 0, 'losses': 0},
            'FIBONACCI_RETRACEMENT': {'wins': 0, 'losses': 0},
            'MEAN_REVERSION': {'wins': 0, 'losses': 0},
            'BREAKOUT': {'wins': 0, 'losses': 0},
            'MOMENTUM': {'wins': 0, 'losses': 0},
            'MULTI_TIMEFRAME_CONFLUENCE': {'wins': 0, 'losses': 0},
        }
        
        # Track positions with trailing stops
        self.trailing_stop_positions = {}  # ticket: {distance_pips, highest_price/lowest_price}
        
        # Initialize components
        self.scanner = ImprovedOpportunityScanner()
        self.risk_manager = RiskManager(config)
        self.market_analyzer = MarketAnalyzer()
        
        # Initialize MT5
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")
        
        if not mt5.login(config['mt5_login'], password=config['mt5_password'], 
                        server=config['mt5_server']):
            raise Exception(f"MT5 login failed: {mt5.last_error()}")
        
        account_info = mt5.account_info()
        self.start_balance = account_info.balance
        
        # Auto-detect zero-spread symbols if not specified
        if config.get('auto_detect_symbols', True):
            logger.info("🔍 Auto-detecting zero-spread symbols...")
            self.symbols = self.scanner.find_zero_spread_symbols()
            logger.info(f"✅ Found {len(self.symbols)} zero-spread symbols")
        else:
            self.symbols = config['symbols']
        
        self.print_startup_banner(account_info)
    
    def print_startup_banner(self, account_info):
        """Print startup information"""
        logger.info("=" * 100)
        logger.info("🚀 IMPROVED ULTIMATE MT5 SCALPING BOT - ENHANCED EDITION")
        logger.info("=" * 100)
        logger.info(f"Account: {account_info.login}")
        logger.info(f"Balance: ${account_info.balance:,.2f}")
        logger.info(f"Leverage: 1:{account_info.leverage}")
        logger.info(f"Broker: {self.config['mt5_server']}")
        logger.info("")
        logger.info("🎯 ENHANCED CAPABILITIES:")
        logger.info(f"  ✅ Scanning {len(self.symbols)} zero-spread pairs")
        logger.info("  ✅ 6 trading strategies with DYNAMIC SL/TP")
        logger.info("  ✅ Market structure-aware risk management")
        logger.info("  ✅ Volatility regime detection")
        logger.info("  ✅ Session-adjusted parameters")
        logger.info("  ✅ Trailing stop support")
        logger.info("  ✅ Commission-aware break-even calculation")
        logger.info("")
        logger.info("⚙️  CONFIGURATION:")
        logger.info(f"  Risk per trade: {self.config.get('risk_per_trade', 0.005)*100}%")
        logger.info(f"  Max concurrent trades: {self.config.get('max_concurrent_trades', 10)}")
        logger.info(f"  Min confidence: {self.config.get('min_confidence', 50)}%")
        logger.info(f"  Commission: ${self.config.get('commission_per_lot', 6)}/lot")
        logger.info(f"  Scan interval: {self.config.get('scan_interval', 30)}s")
        logger.info("")
        logger.info(f"📊 Symbols: {', '.join(self.symbols[:10])}")
        if len(self.symbols) > 10:
            logger.info(f"           ... and {len(self.symbols) - 10} more")
        logger.info("=" * 100)
    
    def is_active_session(self) -> bool:
        """Check if in active trading session"""
        now_utc = datetime.now(timezone.utc)
        now_local = datetime.now()
        hour_utc = now_utc.hour
        
        # London: 08:00-16:00 UTC, New York: 13:00-21:00 UTC
        is_active = (8 <= hour_utc < 16) or (13 <= hour_utc < 21)
        
        if self.config.get('show_time_info', True):
            session_info = self.market_analyzer.get_session_info()
            logger.info(f"⏰ UTC: {now_utc.strftime('%H:%M:%S')} | "
                       f"Local: {now_local.strftime('%H:%M:%S')} | "
                       f"Session: {session_info['session'].upper()} "
                       f"({'✅ ACTIVE' if is_active else '⏸️  INACTIVE'})")
        
        return is_active
    
    def manage_trailing_stops(self):
        """Update trailing stops for open positions"""
        positions = mt5.positions_get()
        if not positions:
            return
        
        for position in positions:
            ticket = position.ticket
            
            # Check if this position has trailing stop enabled
            if ticket not in self.trailing_stop_positions:
                continue
            
            trailing_info = self.trailing_stop_positions[ticket]
            trailing_distance_pips = trailing_info['distance_pips']
            symbol = position.symbol
            
            # Get current price
            tick = mt5.symbol_info_tick(symbol)
            if not tick:
                continue
            
            # Get pip size
            current_price = tick.bid if position.type == mt5.ORDER_TYPE_BUY else tick.ask
            pip_size = self.market_analyzer.get_symbol_pip_size(symbol, current_price)
            trailing_distance = trailing_distance_pips * pip_size
            
            # Update trailing stop
            if position.type == mt5.ORDER_TYPE_BUY:
                # For BUY: trail stop up as price rises
                current_price = tick.bid
                
                if 'highest_price' not in trailing_info:
                    trailing_info['highest_price'] = position.price_open
                
                if current_price > trailing_info['highest_price']:
                    trailing_info['highest_price'] = current_price
                    new_sl = current_price - trailing_distance
                    
                    # Only update if new SL is higher than current SL
                    if new_sl > position.sl:
                        self.modify_position_sl(ticket, new_sl, position.tp)
                        logger.info(f"📈 Trailing stop updated for {symbol} BUY: "
                                  f"New SL: {new_sl:.5f} (trailing {trailing_distance_pips} pips)")
            
            else:  # SELL
                # For SELL: trail stop down as price falls
                current_price = tick.ask
                
                if 'lowest_price' not in trailing_info:
                    trailing_info['lowest_price'] = position.price_open
                
                if current_price < trailing_info['lowest_price']:
                    trailing_info['lowest_price'] = current_price
                    new_sl = current_price + trailing_distance
                    
                    # Only update if new SL is lower than current SL
                    if new_sl < position.sl:
                        self.modify_position_sl(ticket, new_sl, position.tp)
                        logger.info(f"📉 Trailing stop updated for {symbol} SELL: "
                                  f"New SL: {new_sl:.5f} (trailing {trailing_distance_pips} pips)")
    
    def modify_position_sl(self, ticket: int, new_sl: float, tp: float) -> bool:
        """Modify position stop loss"""
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": new_sl,
            "tp": tp,
        }
        
        result = mt5.order_send(request)
        return result.retcode == mt5.TRADE_RETCODE_DONE
    
    def scan_and_trade(self):
        """Main scanning and trading logic"""
        # First, manage trailing stops for existing positions
        self.manage_trailing_stops()
        
        account_info = mt5.account_info()
        positions = mt5.positions_get()
        open_count = len(positions) if positions else 0
        
        margin_level = account_info.margin_level if account_info.margin > 0 else float('inf')
        margin_display = f"{margin_level:.2f}%" if margin_level != float('inf') else "N/A"
        
        daily_pnl = account_info.balance - self.start_balance
        daily_pnl_pct = (daily_pnl / self.start_balance) * 100
        
        logger.info("\n" + "=" * 100)
        logger.info(f"📊 MARKET SCAN - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info(f"Balance: ${account_info.balance:,.2f} | "
                   f"Equity: ${account_info.equity:,.2f} | "
                   f"Daily P&L: ${daily_pnl:+,.2f} ({daily_pnl_pct:+.2f}%)")
        logger.info(f"Open Positions: {open_count}/{self.config.get('max_concurrent_trades', 10)} | "
                   f"Daily Trades: {self.daily_trades} | "
                   f"Margin: {margin_display}")
        logger.info("=" * 100)
        
        # Safety checks
        if not self.is_active_session():
            logger.info("⏸️  Outside active trading sessions. Waiting...")
            return
        
        if self.risk_manager.check_daily_loss_limit(self.start_balance):
            logger.info("🛑 Daily loss limit reached. Stopping trading for today.")
            return
        
        if not self.risk_manager.check_margin_level():
            logger.info("⚠️  Margin level too low. Skipping scan.")
            return
        
        # Scan all pairs
        logger.info(f"\n🔍 Scanning {len(self.symbols)} pairs with 6 IMPROVED strategies...")
        
        enable_multi_tf = self.config.get('enable_multi_timeframe', False)
        opportunities = self.scanner.scan_all_pairs(self.symbols, enable_multi_tf)
        
        if not opportunities:
            logger.info("⏸️  No opportunities found in this scan.")
            logger.info("=" * 100)
            return
        
        # Filter by minimum confidence
        min_conf = self.config.get('min_confidence', 50)
        opportunities = [opp for opp in opportunities if opp['confidence'] >= min_conf]
        
        if not opportunities:
            logger.info(f"⏸️  No opportunities above {min_conf}% confidence threshold.")
            logger.info("=" * 100)
            return
        
        # Rank by expected value
        opportunities = self.risk_manager.rank_opportunities(opportunities)
        
        logger.info(f"\n🎯 Found {len(opportunities)} trading opportunities:")
        logger.info("-" * 100)
        
        for i, opp in enumerate(opportunities[:10], 1):  # Show top 10
            trailing_indicator = " [TRAILING]" if opp.get('use_trailing_stop') else ""
            logger.info(f"{i}. [{opp['symbol']}] {opp['action']} | "
                       f"Confidence: {opp['confidence']}% | "
                       f"Strategy: {opp['strategy']} | "
                       f"SL: {opp['sl_pips']:.1f}p | TP: {opp['tp_pips']:.1f}p | "
                       f"EV: ${opp['expected_value']:.2f}{trailing_indicator}")
        
        if len(opportunities) > 10:
            logger.info(f"... and {len(opportunities) - 10} more")
        
        logger.info("-" * 100)
        
        # Execute best opportunities
        trades_executed = 0
        max_trades_per_scan = self.config.get('max_trades_per_scan', 3)
        
        for opp in opportunities[:max_trades_per_scan]:
            # Check if we can trade
            can_trade, reason = self.risk_manager.can_open_new_position(
                opp['symbol'], 
                opp['action'], 
                self.start_balance
            )
            
            if not can_trade:
                logger.info(f"⏸️  Skipping {opp['symbol']}: {reason}")
                continue
            
            # Execute trade
            if self.execute_trade(opp):
                trades_executed += 1
                time.sleep(1)  # Small delay between trades
        
        logger.info("\n" + "=" * 100)
        logger.info(f"✅ SCAN COMPLETE: {len(opportunities)} signals | {trades_executed} trades executed")
        self.print_strategy_performance()
        logger.info("=" * 100)
    
    def execute_trade(self, opportunity: Dict) -> bool:
        """Execute a trade based on opportunity"""
        symbol = opportunity['symbol']
        action = opportunity['action']
        lot_size = opportunity['lot_size']
        sl_pips = opportunity['sl_pips']
        tp_pips = opportunity['tp_pips']
        use_trailing = opportunity.get('use_trailing_stop', False)
        trailing_distance_pips = opportunity.get('trailing_distance_pips', None)
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"❌ Cannot get tick for {symbol}")
            return False
        
        price = tick.ask if action == 'BUY' else tick.bid
        
        # Get pip size
        pip_size = self.market_analyzer.get_symbol_pip_size(symbol, price)
        
        # Calculate SL/TP
        if action == 'BUY':
            sl = price - (sl_pips * pip_size)
            tp = price + (tp_pips * pip_size)
            order_type = mt5.ORDER_TYPE_BUY
        else:
            sl = price + (sl_pips * pip_size)
            tp = price - (tp_pips * pip_size)
            order_type = mt5.ORDER_TYPE_SELL
        
        # Prepare order
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": lot_size,
            "type": order_type,
            "price": price,
            "sl": sl,
            "tp": tp,
            "deviation": 20,
            "magic": 999002,  # Different magic number for improved bot
            "comment": f"{opportunity['strategy'][:20]}",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        
        # Send order
        result = mt5.order_send(request)
        
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"❌ Order failed: {result.retcode} - {result.comment}")
            return False
        
        self.daily_trades += 1
        
        # If trailing stop enabled, register this position
        if use_trailing and trailing_distance_pips:
            self.trailing_stop_positions[result.order] = {
                'distance_pips': trailing_distance_pips,
                'symbol': symbol,
                'action': action
            }
        
        # Calculate costs and risk
        commission = lot_size * self.config.get('commission_per_lot', 6)
        
        trailing_info = f" | TRAILING: {trailing_distance_pips:.1f}p" if use_trailing else ""
        
        logger.info("\n" + "🎯" * 30)
        logger.info("✅ TRADE EXECUTED (IMPROVED BOT)")
        logger.info(f"Symbol: {symbol} | Action: {action} | Lots: {lot_size}")
        logger.info(f"Strategy: {opportunity['strategy']} | Confidence: {opportunity['confidence']}%")
        logger.info(f"Price: {price} | SL: {sl} ({sl_pips:.1f}p) | TP: {tp} ({tp_pips:.1f}p){trailing_info}")
        logger.info(f"Commission: ${commission:.2f} | Expected Value: ${opportunity['expected_value']:.2f}")
        logger.info(f"Reason: {opportunity['reason']}")
        logger.info("🎯" * 30)
        
        # Save trade
        trade_record = {
            'time': datetime.now().isoformat(),
            'symbol': symbol,
            'action': action,
            'lots': lot_size,
            'price': price,
            'sl': sl,
            'tp': tp,
            'sl_pips': sl_pips,
            'tp_pips': tp_pips,
            'commission': commission,
            'confidence': opportunity['confidence'],
            'strategy': opportunity['strategy'],
            'expected_value': opportunity['expected_value'],
            'reason': opportunity['reason'],
            'use_trailing_stop': use_trailing,
            'trailing_distance_pips': trailing_distance_pips,
            'ticket': result.order
        }
        self.trade_history.append(trade_record)
        
        with open('ultimate_trade_history_improved.json', 'w') as f:
            json.dump(self.trade_history, f, indent=2)
        
        return True
    
    def print_strategy_performance(self):
        """Print strategy performance statistics"""
        logger.info("\n📈 STRATEGY PERFORMANCE:")
        for strategy, stats in self.strategy_performance.items():
            total = stats['wins'] + stats['losses']
            if total > 0:
                win_rate = (stats['wins'] / total) * 100
                logger.info(f"  {strategy}: {stats['wins']}W / {stats['losses']}L ({win_rate:.1f}%)")
    
    def run(self):
        """Main bot loop"""
        logger.info("\n🚀 Improved Ultimate Scalping Bot Started\n")
        
        scan_interval = self.config.get('scan_interval', 30)
        
        try:
            while True:
                self.scan_and_trade()
                time.sleep(scan_interval)
        except KeyboardInterrupt:
            logger.info("\n⏹️  Bot stopped by user")
        finally:
            mt5.shutdown()


if __name__ == "__main__":
    try:
        from ultimate_config import CONFIG
    except ImportError:
        logger.error("❌ ultimate_config.py not found! Copy ultimate_config_template.py to ultimate_config.py")
        exit(1)
    
    bot = ImprovedUltimateScalpingBot(CONFIG)
    bot.run()

