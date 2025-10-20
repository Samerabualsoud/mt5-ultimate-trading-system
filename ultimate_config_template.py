"""
Ultimate Trading System Configuration Template
==============================================
Copy this file to ultimate_config.py and fill in your details
"""

CONFIG = {
    # ==================== MT5 CONNECTION ====================
    'mt5_login': 12345678,  # Your MT5 account number
    'mt5_password': 'your_password_here',  # Your MT5 password
    'mt5_server': 'ACYSecurities-Demo',  # Your broker server name
    
    # ==================== SYMBOL SELECTION ====================
    # Option 1: Auto-detect all zero-spread symbols (RECOMMENDED)
    'auto_detect_symbols': True,
    
    # Option 2: Manually specify symbols (set auto_detect_symbols to False)
    'symbols': [
        'EURUSDzero',
        'GBPUSDzero',
        'AUDUSDzero',
        'USDCADzero',
        'USDCHFzero',
        'NZDUSDzero',
        'USDJPYzero',
        # Add more zero-spread pairs as needed
    ],
    
    # ==================== RISK MANAGEMENT ====================
    'risk_per_trade': 0.005,  # 0.5% of balance per trade (CONSERVATIVE)
                              # Increase to 0.01 (1%) for more aggressive
                              # NEVER exceed 0.02 (2%)
    
    'max_concurrent_trades': 10,  # Maximum number of open positions
                                  # 10 = aggressive, 5 = moderate, 3 = conservative
    
    'max_daily_loss': 0.03,  # Stop trading if lose 3% in a day
    
    'min_margin_level': 500,  # Minimum margin level (%) to continue trading
    
    # ==================== TRADING PARAMETERS ====================
    'min_confidence': 50,  # Minimum signal confidence to trade (50-100)
                          # 50 = aggressive (more trades, lower quality)
                          # 60 = moderate
                          # 70 = conservative (fewer trades, higher quality)
    
    'max_trades_per_scan': 3,  # Max trades to execute per scan
                               # Prevents over-trading in volatile conditions
    
    'commission_per_lot': 6,  # Commission in USD per lot (ACY ProZero = $6)
    
    # ==================== SCANNING SETTINGS ====================
    'scan_interval': 30,  # Seconds between scans (30 = aggressive, 60 = moderate)
    
    'enable_multi_timeframe': False,  # Enable Strategy 6 (slower but higher quality)
                                      # Set to True for best signals, False for speed
    
    'analysis_interval': 60,  # Seconds between detailed analysis scans
    
    # ==================== DISPLAY SETTINGS ====================
    'show_time_info': True,  # Show UTC and local time in logs
    
    # ==================== ADVANCED SETTINGS ====================
    # Session filters (UTC hours)
    'london_session': (8, 16),  # London: 08:00-16:00 UTC
    'ny_session': (13, 21),     # New York: 13:00-21:00 UTC
    
    # Only trade during these sessions
    'trade_only_active_sessions': True,
}


# ==================== CONFIGURATION NOTES ====================
"""
RECOMMENDED SETTINGS FOR DIFFERENT TRADING STYLES:

1. CONSERVATIVE (Beginner-Friendly):
   - risk_per_trade: 0.003 (0.3%)
   - max_concurrent_trades: 3
   - min_confidence: 65
   - scan_interval: 60
   - enable_multi_timeframe: True
   Expected: 10-20 trades/day, 70-75% win rate

2. MODERATE (Balanced):
   - risk_per_trade: 0.005 (0.5%)
   - max_concurrent_trades: 5
   - min_confidence: 55
   - scan_interval: 45
   - enable_multi_timeframe: False
   Expected: 20-35 trades/day, 65-70% win rate

3. AGGRESSIVE (Experienced):
   - risk_per_trade: 0.01 (1%)
   - max_concurrent_trades: 10
   - min_confidence: 50
   - scan_interval: 30
   - enable_multi_timeframe: False
   Expected: 30-60 trades/day, 60-65% win rate

ACCOUNT SIZE RECOMMENDATIONS:
- $10k-25k: Use CONSERVATIVE settings
- $25k-75k: Use MODERATE settings
- $75k+: Can use AGGRESSIVE settings

IMPORTANT:
- Always test on DEMO first for 2-4 weeks
- Start with CONSERVATIVE settings
- Gradually increase aggressiveness if profitable
- NEVER risk more than 1% per trade until proven profitable
"""

