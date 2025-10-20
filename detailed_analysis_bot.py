"""
Detailed Analysis Bot
=====================
Shows complete analysis for each pair
Helps understand what the bot is thinking
"""

import MetaTrader5 as mt5
import logging
import time
from datetime import datetime, timezone
from typing import Dict
from opportunity_scanner import OpportunityScanner

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[
        logging.FileHandler('detailed_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DetailedAnalysisBot:
    """Shows detailed analysis for all pairs"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.scanner = OpportunityScanner()
        
        if not mt5.initialize():
            raise Exception("MT5 initialization failed")
        
        if not mt5.login(config['mt5_login'], password=config['mt5_password'], 
                        server=config['mt5_server']):
            raise Exception(f"MT5 login failed")
        
        # Auto-detect symbols
        if config.get('auto_detect_symbols', True):
            self.symbols = self.scanner.find_zero_spread_symbols()
        else:
            self.symbols = config['symbols']
        
        logger.info("=" * 120)
        logger.info("🔍 DETAILED ANALYSIS BOT - Market Intelligence System")
        logger.info("=" * 120)
        logger.info(f"Analyzing {len(self.symbols)} zero-spread pairs")
        logger.info("=" * 120)
    
    def analyze_symbol(self, symbol: str):
        """Show complete analysis for a symbol"""
        logger.info("\n" + "=" * 120)
        logger.info(f"📊 DETAILED ANALYSIS: {symbol}")
        logger.info(f"Timestamp: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
        logger.info("=" * 120)
        
        analysis = self.scanner.get_detailed_analysis(symbol)
        
        if 'error' in analysis:
            logger.info(f"❌ Error: {analysis['error']}")
            return
        
        # Current price
        logger.info(f"\n💰 CURRENT PRICE: {analysis['current_price']:.5f}")
        
        # Trend analysis
        logger.info("\n📈 TREND ANALYSIS:")
        trend = analysis['trend']
        logger.info(f"  EMA(9): {trend['ema9']:.5f} | EMA(21): {trend['ema21']:.5f}")
        logger.info(f"  Trend: {trend['ema_trend'].upper()} {'🟢' if trend['ema_trend'] == 'bullish' else '🔴'}")
        logger.info(f"  MACD: {trend['macd']:.5f} | Signal: {trend['macd_signal']:.5f} | Histogram: {trend['macd_histogram']:.5f}")
        logger.info(f"  ADX: {trend['adx']:.2f} | Strength: {trend['trend_strength'].upper()}")
        
        if 'h1_trend' in analysis:
            logger.info(f"  H1 Trend: {analysis['h1_trend'].upper()} {'🟢' if analysis['h1_trend'] == 'bullish' else '🔴'}")
        
        # Momentum
        logger.info("\n⚡ MOMENTUM INDICATORS:")
        momentum = analysis['momentum']
        logger.info(f"  RSI(14): {momentum['rsi']:.2f} - {momentum['rsi_state'].upper()}")
        logger.info(f"  Stochastic: K={momentum['stochastic_k']:.2f} | D={momentum['stochastic_d']:.2f}")
        logger.info(f"  CCI: {momentum['cci']:.2f}")
        logger.info(f"  Williams %R: {momentum['williams_r']:.2f}")
        
        # Volatility
        logger.info("\n📊 VOLATILITY:")
        vol = analysis['volatility']
        logger.info(f"  ATR: {vol['atr']:.5f}")
        logger.info(f"  Bollinger Bands:")
        logger.info(f"    Upper: {vol['bb_upper']:.5f}")
        logger.info(f"    Middle: {vol['bb_middle']:.5f}")
        logger.info(f"    Lower: {vol['bb_lower']:.5f}")
        logger.info(f"    Position: {vol['bb_position'].upper()}")
        
        # Support/Resistance
        logger.info("\n📍 SUPPORT & RESISTANCE:")
        levels = analysis['levels']
        logger.info(f"  Pivot: {levels['pivot']:.5f}")
        logger.info(f"  R1: {levels['r1']:.5f} | S1: {levels['s1']:.5f}")
        logger.info(f"  Fibonacci 61.8%: {levels['fib_618']:.5f}")
        logger.info(f"  Fibonacci 50.0%: {levels['fib_500']:.5f}")
        logger.info(f"  Fibonacci 38.2%: {levels['fib_382']:.5f}")
        
        if levels['support']:
            logger.info(f"  Support levels: {', '.join([f'{s:.5f}' for s in levels['support'][:3]])}")
        if levels['resistance']:
            logger.info(f"  Resistance levels: {', '.join([f'{r:.5f}' for r in levels['resistance'][:3]])}")
        
        # Strategy signals
        logger.info("\n🎯 STRATEGY SIGNALS:")
        logger.info("-" * 120)
        
        for strat in analysis['strategy_signals']:
            signal_icon = "🟢" if strat['signal'] == 'BUY' else "🔴" if strat['signal'] == 'SELL' else "⏸️ "
            logger.info(f"{signal_icon} {strat['name']:30s} | "
                       f"Signal: {strat['signal']:4s} | "
                       f"Confidence: {strat['confidence']:3d}% | "
                       f"Reason: {strat['reason']}")
        
        logger.info("-" * 120)
        
        # Summary
        active_signals = [s for s in analysis['strategy_signals'] if s['signal'] != 'None']
        if active_signals:
            best_signal = max(active_signals, key=lambda x: x['confidence'])
            logger.info(f"\n💡 BEST SIGNAL: {best_signal['signal']} via {best_signal['name']} ({best_signal['confidence']}%)")
        else:
            logger.info(f"\n⏸️  NO ACTIVE SIGNALS - Waiting for setup")
        
        logger.info("=" * 120)
    
    def analyze_all(self):
        """Analyze all symbols"""
        logger.info(f"\n🔍 SCANNING {len(self.symbols)} PAIRS...")
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Quick scan for signals
        opportunities = self.scanner.scan_all_pairs(self.symbols, enable_multi_tf=False)
        
        if opportunities:
            logger.info(f"\n✅ Found {len(opportunities)} trading signals:")
            for opp in opportunities[:5]:
                logger.info(f"  [{opp['symbol']}] {opp['action']} | "
                           f"{opp['confidence']}% | {opp['strategy']}")
        else:
            logger.info("\n⏸️  No signals found across all pairs")
        
        # Detailed analysis for pairs with signals
        if opportunities:
            logger.info("\n📊 DETAILED ANALYSIS FOR TOP OPPORTUNITIES:")
            for opp in opportunities[:3]:  # Top 3
                self.analyze_symbol(opp['symbol'])
                time.sleep(0.5)
    
    def run(self):
        """Main loop"""
        scan_interval = self.config.get('analysis_interval', 60)
        
        try:
            while True:
                self.analyze_all()
                logger.info(f"\n⏰ Next scan in {scan_interval} seconds...\n")
                time.sleep(scan_interval)
        except KeyboardInterrupt:
            logger.info("\n⏹️  Analysis bot stopped")
        finally:
            mt5.shutdown()


if __name__ == "__main__":
    try:
        from ultimate_config import CONFIG
    except ImportError:
        logger.error("❌ ultimate_config.py not found!")
        exit(1)
    
    bot = DetailedAnalysisBot(CONFIG)
    bot.run()

