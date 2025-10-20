"""
Ultimate Scalping Bot - Main Aggressive Trader
===============================================
Multi-strategy, multi-pair trading system
Target: 30-60 trades per day with 65-70% win rate
"""

import MetaTrader5 as mt5
import logging
import time
import json
from datetime import datetime, timezone
from typing import Dict, List
from opportunity_scanner import OpportunityScanner
from risk_manager import RiskManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultimate_scalping_bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class UltimateScalpingBot:
    """Ultimate professional trading system"""
    
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
        
        # Initialize components
        self.scanner = OpportunityScanner()
        self.risk_manager = RiskManager(config)
        
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
        logger.info("🚀 ULTIMATE MT5 SCALPING BOT - PROFESSIONAL EDITION")
        logger.info("=" * 100)
        logger.info(f"Account: {account_info.login}")
        logger.info(f"Balance: ${account_info.balance:,.2f}")
        logger.info(f"Leverage: 1:{account_info.leverage}")
        logger.info(f"Broker: {self.config['mt5_server']}")
        logger.info("")
        logger.info("🎯 SYSTEM CAPABILITIES:")
        logger.info(f"  ✅ Scanning {len(self.symbols)} zero-spread pairs")
        logger.info("  ✅ 6 trading strategies running simultaneously")
        logger.info("  ✅ 17 technical indicators")
        logger.info("  ✅ Correlation filter active")
        logger.info("  ✅ Dynamic position sizing")
        logger.info("  ✅ Multi-timeframe analysis")
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
            logger.info(f"⏰ UTC: {now_utc.strftime('%H:%M:%S')} | "
                       f"Local: {now_local.strftime('%H:%M:%S')} | "
                       f"Session: {'✅ ACTIVE' if is_active else '⏸️  INACTIVE'}")
        
        return is_active
    
    def scan_and_trade(self):
        """Main scanning and trading logic"""
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
        logger.info(f"\n🔍 Scanning {len(self.symbols)} pairs with 6 strategies...")
        
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
            logger.info(f"{i}. [{opp['symbol']}] {opp['action']} | "
                       f"Confidence: {opp['confidence']}% | "
                       f"Strategy: {opp['strategy']} | "
                       f"EV: ${opp['expected_value']:.2f} | "
                       f"Lots: {opp['lot_size']}")
        
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
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            logger.error(f"❌ Cannot get tick for {symbol}")
            return False
        
        price = tick.ask if action == 'BUY' else tick.bid
        
        # Calculate pip size
        if 'JPY' in symbol:
            pip_size = 0.01
        elif 'XAU' in symbol or 'GOLD' in symbol:
            pip_size = 0.10
        else:
            pip_size = 0.0001
        
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
            "magic": 999001,
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
        
        # Calculate costs and risk
        commission = lot_size * self.config.get('commission_per_lot', 6)
        risk_amount = opportunity.get('expected_value', 0)  # Simplified
        
        logger.info("\n" + "🎯" * 30)
        logger.info("✅ TRADE EXECUTED")
        logger.info(f"Symbol: {symbol} | Action: {action} | Lots: {lot_size}")
        logger.info(f"Strategy: {opportunity['strategy']} | Confidence: {opportunity['confidence']}%")
        logger.info(f"Price: {price} | SL: {sl} ({sl_pips:.1f} pips) | TP: {tp} ({tp_pips:.1f} pips)")
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
            'reason': opportunity['reason']
        }
        self.trade_history.append(trade_record)
        
        with open('ultimate_trade_history.json', 'w') as f:
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
        logger.info("\n🚀 Ultimate Scalping Bot Started\n")
        
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
    
    bot = UltimateScalpingBot(CONFIG)
    bot.run()

