"""
Cryptocurrency Support Module
==============================
Adds Bitcoin, Ethereum, and other crypto trading to MT5 bot
"""

import MetaTrader5 as mt5
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class CryptoSupport:
    """
    Cryptocurrency trading support for MT5
    
    Handles crypto-specific:
    - Symbol detection (BTCUSD, ETHUSD, etc.)
    - Pip size calculation
    - Volatility adjustments
    - 24/7 trading (no session filters)
    """
    
    # Major cryptocurrencies supported by most MT5 brokers
    CRYPTO_SYMBOLS = [
        'BTCUSD',   # Bitcoin
        'ETHUSD',   # Ethereum
        'LTCUSD',   # Litecoin
        'XRPUSD',   # Ripple
        'BCHUSD',   # Bitcoin Cash
        'EOSUSD',   # EOS
        'ADAUSD',   # Cardano
        'DOTUSD',   # Polkadot
        'LINKUSD',  # Chainlink
        'UNIUSD',   # Uniswap
    ]
    
    # Crypto symbols with different naming conventions
    CRYPTO_VARIANTS = {
        'BITCOIN': ['BTCUSD', 'BTCUSDT', 'XBTUSD', 'Bitcoin'],
        'ETHEREUM': ['ETHUSD', 'ETHUSDT', 'Ethereum'],
        'LITECOIN': ['LTCUSD', 'LTCUSDT', 'Litecoin'],
        'RIPPLE': ['XRPUSD', 'XRPUSDT', 'Ripple'],
    }
    
    def __init__(self):
        self.available_cryptos = []
        self.crypto_info = {}
    
    def detect_crypto_symbols(self) -> List[str]:
        """
        Detect available cryptocurrency symbols in MT5
        
        Returns:
            List of available crypto symbols
        """
        all_symbols = mt5.symbols_get()
        if not all_symbols:
            logger.warning("No symbols found in MT5")
            return []
        
        crypto_symbols = []
        
        for symbol in all_symbols:
            symbol_name = symbol.name
            
            # Check if it's a known crypto
            if any(crypto in symbol_name.upper() for crypto in ['BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'EOS', 'ADA', 'DOT', 'LINK', 'UNI']):
                # Verify it's tradeable
                if symbol.visible and symbol.trade_mode != mt5.SYMBOL_TRADE_MODE_DISABLED:
                    crypto_symbols.append(symbol_name)
                    
                    # Store symbol info
                    self.crypto_info[symbol_name] = {
                        'description': symbol.description,
                        'digits': symbol.digits,
                        'point': symbol.point,
                        'trade_contract_size': symbol.trade_contract_size,
                        'volume_min': symbol.volume_min,
                        'volume_max': symbol.volume_max,
                        'volume_step': symbol.volume_step,
                    }
        
        self.available_cryptos = crypto_symbols
        
        logger.info(f"Detected {len(crypto_symbols)} cryptocurrency symbols:")
        for symbol in crypto_symbols:
            logger.info(f"  - {symbol}: {self.crypto_info[symbol]['description']}")
        
        return crypto_symbols
    
    def is_crypto(self, symbol: str) -> bool:
        """Check if symbol is a cryptocurrency"""
        symbol_upper = symbol.upper()
        
        # Check common crypto identifiers
        crypto_keywords = ['BTC', 'ETH', 'LTC', 'XRP', 'BCH', 'EOS', 'ADA', 'DOT', 'LINK', 'UNI', 'CRYPTO']
        
        return any(keyword in symbol_upper for keyword in crypto_keywords)
    
    def get_crypto_pip_size(self, symbol: str) -> float:
        """
        Get pip size for cryptocurrency
        
        Cryptos have different pip sizes than forex:
        - BTCUSD: 1.0 (price ~$40,000)
        - ETHUSD: 0.1 (price ~$2,000)
        - Others: typically 0.01 or 0.001
        """
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.warning(f"Cannot get info for {symbol}, using default")
            return 1.0
        
        # Get current price to determine appropriate pip size
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return 1.0
        
        price = tick.bid
        
        # Bitcoin: large price, use 1.0 as pip
        if 'BTC' in symbol.upper() and price > 10000:
            return 1.0
        
        # Ethereum: medium price, use 0.1 as pip
        elif 'ETH' in symbol.upper() and price > 1000:
            return 0.1
        
        # Other cryptos: use point * 10 as pip
        else:
            return symbol_info.point * 10
    
    def get_crypto_volatility_multiplier(self, symbol: str) -> float:
        """
        Get volatility multiplier for crypto
        
        Cryptos are more volatile than forex:
        - BTC: 2.5x more volatile
        - ETH: 3.0x more volatile
        - Altcoins: 4.0x more volatile
        
        This is used to adjust SL/TP distances
        """
        symbol_upper = symbol.upper()
        
        if 'BTC' in symbol_upper:
            return 2.5
        elif 'ETH' in symbol_upper:
            return 3.0
        else:
            # Altcoins are very volatile
            return 4.0
    
    def adjust_crypto_parameters(self, symbol: str, sl_pips: float, tp_pips: float, 
                                 confidence: float) -> Dict:
        """
        Adjust trading parameters for cryptocurrency
        
        Returns:
            {
                'sl_pips': adjusted SL,
                'tp_pips': adjusted TP,
                'confidence': adjusted confidence,
                'risk_multiplier': risk adjustment
            }
        """
        if not self.is_crypto(symbol):
            return {
                'sl_pips': sl_pips,
                'tp_pips': tp_pips,
                'confidence': confidence,
                'risk_multiplier': 1.0
            }
        
        volatility_mult = self.get_crypto_volatility_multiplier(symbol)
        
        # Wider stops for cryptos due to volatility
        adjusted_sl = sl_pips * volatility_mult
        adjusted_tp = tp_pips * volatility_mult
        
        # Slightly lower confidence due to higher unpredictability
        adjusted_confidence = confidence * 0.95
        
        # Reduce position size due to higher risk
        risk_multiplier = 1.0 / volatility_mult
        
        logger.info(f"Crypto adjustments for {symbol}:")
        logger.info(f"  SL: {sl_pips:.1f} -> {adjusted_sl:.1f} pips")
        logger.info(f"  TP: {tp_pips:.1f} -> {adjusted_tp:.1f} pips")
        logger.info(f"  Confidence: {confidence:.1f}% -> {adjusted_confidence:.1f}%")
        logger.info(f"  Risk multiplier: {risk_multiplier:.2f}x")
        
        return {
            'sl_pips': adjusted_sl,
            'tp_pips': adjusted_tp,
            'confidence': adjusted_confidence,
            'risk_multiplier': risk_multiplier
        }
    
    def is_crypto_trading_hours(self) -> bool:
        """
        Check if it's crypto trading hours
        
        Cryptos trade 24/7, so always returns True
        But can be used to filter out low-liquidity periods
        """
        # Crypto trades 24/7
        return True
    
    def get_crypto_session_multiplier(self) -> float:
        """
        Get session multiplier for crypto
        
        Unlike forex, crypto doesn't have sessions
        But liquidity varies:
        - US hours (13:00-22:00 UTC): highest liquidity (1.0x)
        - Asian hours (00:00-08:00 UTC): medium liquidity (0.9x)
        - Off-peak (08:00-13:00 UTC): lower liquidity (0.8x)
        """
        from datetime import datetime, timezone
        
        current_hour = datetime.now(timezone.utc).hour
        
        # US trading hours (highest liquidity)
        if 13 <= current_hour < 22:
            return 1.0
        
        # Asian hours (medium liquidity)
        elif 0 <= current_hour < 8:
            return 0.9
        
        # Off-peak (lower liquidity)
        else:
            return 0.8
    
    def calculate_crypto_position_size(self, symbol: str, account_balance: float,
                                      risk_per_trade: float, sl_pips: float) -> float:
        """
        Calculate position size for cryptocurrency
        
        Takes into account:
        - Higher volatility
        - Different contract sizes
        - Risk per trade
        """
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            logger.error(f"Cannot get symbol info for {symbol}")
            return 0.0
        
        # Get crypto-specific parameters
        adjustments = self.adjust_crypto_parameters(symbol, sl_pips, 0, 100)
        adjusted_sl = adjustments['sl_pips']
        risk_multiplier = adjustments['risk_multiplier']
        
        # Calculate risk amount
        risk_amount = account_balance * risk_per_trade * risk_multiplier
        
        # Get pip value
        pip_size = self.get_crypto_pip_size(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return 0.0
        
        # For crypto, pip value = pip_size * contract_size / price
        contract_size = symbol_info.trade_contract_size
        price = tick.bid
        
        pip_value = (pip_size * contract_size) / price
        
        # Calculate lot size
        lot_size = risk_amount / (adjusted_sl * pip_value)
        
        # Round to volume step
        volume_step = symbol_info.volume_step
        lot_size = round(lot_size / volume_step) * volume_step
        
        # Clamp to min/max
        lot_size = max(symbol_info.volume_min, min(symbol_info.volume_max, lot_size))
        
        logger.info(f"Crypto position size for {symbol}:")
        logger.info(f"  Risk amount: ${risk_amount:.2f}")
        logger.info(f"  Adjusted SL: {adjusted_sl:.1f} pips")
        logger.info(f"  Pip value: ${pip_value:.2f}")
        logger.info(f"  Lot size: {lot_size:.2f}")
        
        return lot_size
    
    def get_crypto_commission(self, symbol: str, lot_size: float) -> float:
        """
        Get commission for crypto trade
        
        Crypto commissions are typically higher than forex:
        - Spot crypto: 0.1-0.5% per side
        - CFD crypto: similar to forex
        """
        symbol_info = mt5.symbol_info(symbol)
        if not symbol_info:
            return 0.0
        
        # Get current price
        tick = mt5.symbol_info_tick(symbol)
        if not tick:
            return 0.0
        
        price = tick.bid
        contract_size = symbol_info.trade_contract_size
        
        # Calculate trade value
        trade_value = lot_size * contract_size * price
        
        # Assume 0.2% commission (typical for crypto CFDs)
        commission_rate = 0.002
        commission = trade_value * commission_rate * 2  # Round-trip
        
        return commission


def integrate_crypto_support(bot):
    """
    Integrate crypto support into existing bot
    
    Usage:
        crypto_support = CryptoSupport()
        integrate_crypto_support(bot)
    """
    bot.crypto_support = CryptoSupport()
    
    # Detect available cryptos
    crypto_symbols = bot.crypto_support.detect_crypto_symbols()
    
    # Add to bot's symbol list
    if hasattr(bot, 'symbols'):
        bot.symbols.extend(crypto_symbols)
        logger.info(f"Added {len(crypto_symbols)} crypto symbols to bot")
    
    # Override pip size calculation for cryptos
    original_get_pip_size = bot.get_symbol_pip_size
    
    def get_symbol_pip_size_with_crypto(symbol):
        if bot.crypto_support.is_crypto(symbol):
            return bot.crypto_support.get_crypto_pip_size(symbol)
        else:
            return original_get_pip_size(symbol)
    
    bot.get_symbol_pip_size = get_symbol_pip_size_with_crypto
    
    logger.info("✅ Cryptocurrency support integrated")


# Example usage in ultimate_bot_v2.py:
"""
from crypto_support import CryptoSupport, integrate_crypto_support

class UltimateTradingBotV2:
    def __init__(self, config):
        # ... existing initialization ...
        
        # Add crypto support
        if config.get('enable_crypto', False):
            self.crypto_support = CryptoSupport()
            integrate_crypto_support(self)
            logger.info("🪙 Cryptocurrency trading enabled")
"""

