"""
Configuration Validator
========================
Validates configuration parameters to prevent runtime errors
"""

import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class ConfigValidator:
    """Validates trading bot configuration"""
    
    @staticmethod
    def validate_config(config: Dict) -> Tuple[bool, List[str]]:
        """
        Validate configuration parameters
        
        Returns:
            (is_valid, list_of_errors)
        """
        errors = []
        warnings = []
        
        # Required fields
        required_fields = ['mt5_login', 'mt5_password', 'mt5_server']
        for field in required_fields:
            if field not in config:
                errors.append(f"Missing required field: {field}")
        
        # Validate risk_per_trade
        risk_per_trade = config.get('risk_per_trade', 0.005)
        if not isinstance(risk_per_trade, (int, float)):
            errors.append(f"risk_per_trade must be a number, got {type(risk_per_trade)}")
        elif not 0.001 <= risk_per_trade <= 0.05:
            errors.append(f"risk_per_trade must be between 0.1% and 5%, got {risk_per_trade*100}%")
        elif risk_per_trade > 0.02:
            warnings.append(f"risk_per_trade is high ({risk_per_trade*100}%) - consider reducing for safety")
        
        # Validate max_concurrent_trades
        max_concurrent = config.get('max_concurrent_trades', 10)
        if not isinstance(max_concurrent, int):
            errors.append(f"max_concurrent_trades must be an integer, got {type(max_concurrent)}")
        elif not 1 <= max_concurrent <= 20:
            errors.append(f"max_concurrent_trades must be between 1 and 20, got {max_concurrent}")
        elif max_concurrent > 15:
            warnings.append(f"max_concurrent_trades is high ({max_concurrent}) - may strain margin")
        
        # Validate min_confidence
        min_confidence = config.get('min_confidence', 50)
        if not isinstance(min_confidence, (int, float)):
            errors.append(f"min_confidence must be a number, got {type(min_confidence)}")
        elif not 30 <= min_confidence <= 100:
            errors.append(f"min_confidence must be between 30 and 100, got {min_confidence}")
        elif min_confidence < 45:
            warnings.append(f"min_confidence is low ({min_confidence}) - may generate too many trades")
        elif min_confidence > 75:
            warnings.append(f"min_confidence is high ({min_confidence}) - may miss opportunities")
        
        # Validate max_daily_loss
        max_daily_loss = config.get('max_daily_loss', 0.03)
        if not isinstance(max_daily_loss, (int, float)):
            errors.append(f"max_daily_loss must be a number, got {type(max_daily_loss)}")
        elif not 0.01 <= max_daily_loss <= 0.10:
            errors.append(f"max_daily_loss must be between 1% and 10%, got {max_daily_loss*100}%")
        elif max_daily_loss > 0.05:
            warnings.append(f"max_daily_loss is high ({max_daily_loss*100}%) - consider reducing")
        
        # Validate max_hourly_loss
        max_hourly_loss = config.get('max_hourly_loss', 0.01)
        if max_hourly_loss is not None:
            if not isinstance(max_hourly_loss, (int, float)):
                errors.append(f"max_hourly_loss must be a number, got {type(max_hourly_loss)}")
            elif not 0.005 <= max_hourly_loss <= 0.03:
                errors.append(f"max_hourly_loss must be between 0.5% and 3%, got {max_hourly_loss*100}%")
        
        # Validate max_consecutive_losses
        max_consecutive_losses = config.get('max_consecutive_losses', 5)
        if max_consecutive_losses is not None:
            if not isinstance(max_consecutive_losses, int):
                errors.append(f"max_consecutive_losses must be an integer, got {type(max_consecutive_losses)}")
            elif not 3 <= max_consecutive_losses <= 10:
                errors.append(f"max_consecutive_losses must be between 3 and 10, got {max_consecutive_losses}")
        
        # Validate scan_interval
        scan_interval = config.get('scan_interval', 45)
        if not isinstance(scan_interval, (int, float)):
            errors.append(f"scan_interval must be a number, got {type(scan_interval)}")
        elif not 15 <= scan_interval <= 300:
            errors.append(f"scan_interval must be between 15 and 300 seconds, got {scan_interval}")
        elif scan_interval < 30:
            warnings.append(f"scan_interval is low ({scan_interval}s) - may cause high API load")
        
        # Validate commission_per_lot
        commission_per_lot = config.get('commission_per_lot', 6)
        if not isinstance(commission_per_lot, (int, float)):
            errors.append(f"commission_per_lot must be a number, got {type(commission_per_lot)}")
        elif not 0 <= commission_per_lot <= 20:
            errors.append(f"commission_per_lot must be between 0 and 20, got {commission_per_lot}")
        elif commission_per_lot > 10:
            warnings.append(f"commission_per_lot is high ({commission_per_lot}) - verify with broker")
        
        # Validate min_margin_level
        min_margin_level = config.get('min_margin_level', 500)
        if not isinstance(min_margin_level, (int, float)):
            errors.append(f"min_margin_level must be a number, got {type(min_margin_level)}")
        elif not 200 <= min_margin_level <= 2000:
            errors.append(f"min_margin_level must be between 200% and 2000%, got {min_margin_level}%")
        elif min_margin_level < 300:
            warnings.append(f"min_margin_level is low ({min_margin_level}%) - risk of margin call")
        
        # Validate breakeven_pips
        breakeven_pips = config.get('breakeven_pips', 15)
        if breakeven_pips is not None:
            if not isinstance(breakeven_pips, (int, float)):
                errors.append(f"breakeven_pips must be a number, got {type(breakeven_pips)}")
            elif not 5 <= breakeven_pips <= 50:
                errors.append(f"breakeven_pips must be between 5 and 50, got {breakeven_pips}")
        
        # Validate partial_profit_pips
        partial_profit_pips = config.get('partial_profit_pips', 30)
        if partial_profit_pips is not None:
            if not isinstance(partial_profit_pips, (int, float)):
                errors.append(f"partial_profit_pips must be a number, got {type(partial_profit_pips)}")
            elif not 10 <= partial_profit_pips <= 100:
                errors.append(f"partial_profit_pips must be between 10 and 100, got {partial_profit_pips}")
        
        # Validate boolean flags
        boolean_fields = ['enable_multi_timeframe', 'enable_breakeven', 'enable_partial_profits', 'auto_detect_symbols']
        for field in boolean_fields:
            if field in config and not isinstance(config[field], bool):
                errors.append(f"{field} must be True or False, got {type(config[field])}")
        
        # Validate symbols list (if provided)
        if 'symbols' in config and not config.get('auto_detect_symbols', True):
            symbols = config['symbols']
            if not isinstance(symbols, list):
                errors.append(f"symbols must be a list, got {type(symbols)}")
            elif len(symbols) == 0:
                errors.append("symbols list is empty")
            elif len(symbols) > 100:
                warnings.append(f"symbols list is large ({len(symbols)}) - may slow down scans")
        
        # Cross-validation
        if 'breakeven_pips' in config and 'partial_profit_pips' in config:
            if config['partial_profit_pips'] <= config['breakeven_pips']:
                warnings.append("partial_profit_pips should be greater than breakeven_pips")
        
        if 'max_hourly_loss' in config and 'max_daily_loss' in config:
            if config['max_hourly_loss'] * 8 > config['max_daily_loss']:
                warnings.append("max_hourly_loss * 8 exceeds max_daily_loss - may hit daily limit quickly")
        
        # Log warnings
        for warning in warnings:
            logger.warning(f"⚠️  Config warning: {warning}")
        
        # Return validation result
        is_valid = len(errors) == 0
        
        if not is_valid:
            for error in errors:
                logger.error(f"❌ Config error: {error}")
        
        return is_valid, errors
    
    @staticmethod
    def get_safe_config(config: Dict) -> Dict:
        """
        Return config with safe defaults for missing values
        """
        safe_config = config.copy()
        
        defaults = {
            'risk_per_trade': 0.005,
            'max_concurrent_trades': 10,
            'min_confidence': 50,
            'max_daily_loss': 0.03,
            'max_hourly_loss': 0.01,
            'max_consecutive_losses': 5,
            'scan_interval': 45,
            'commission_per_lot': 6,
            'min_margin_level': 500,
            'breakeven_pips': 15,
            'partial_profit_pips': 30,
            'enable_multi_timeframe': True,
            'enable_breakeven': True,
            'enable_partial_profits': False,
            'auto_detect_symbols': True,
            'symbols': [],
        }
        
        for key, default_value in defaults.items():
            if key not in safe_config:
                safe_config[key] = default_value
                logger.info(f"Using default value for {key}: {default_value}")
        
        return safe_config
    
    @staticmethod
    def print_config_summary(config: Dict):
        """Print a summary of the configuration"""
        logger.info("=" * 80)
        logger.info("📋 CONFIGURATION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Risk per trade: {config.get('risk_per_trade', 0.005)*100:.2f}%")
        logger.info(f"Max concurrent trades: {config.get('max_concurrent_trades', 10)}")
        logger.info(f"Min confidence: {config.get('min_confidence', 50)}%")
        logger.info(f"Max daily loss: {config.get('max_daily_loss', 0.03)*100:.1f}%")
        logger.info(f"Max hourly loss: {config.get('max_hourly_loss', 0.01)*100:.1f}%")
        logger.info(f"Max consecutive losses: {config.get('max_consecutive_losses', 5)}")
        logger.info(f"Scan interval: {config.get('scan_interval', 45)}s")
        logger.info(f"Commission per lot: ${config.get('commission_per_lot', 6)}")
        logger.info(f"Break-even enabled: {config.get('enable_breakeven', True)}")
        logger.info(f"Partial profits enabled: {config.get('enable_partial_profits', False)}")
        logger.info(f"Multi-timeframe enabled: {config.get('enable_multi_timeframe', True)}")
        logger.info("=" * 80)

