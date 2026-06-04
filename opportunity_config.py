"""Конфигурация для Opportunity Analyzer"""

# Net Edge Strategy Thresholds
OPPORTUNITY_CONFIG = {
    # Spread thresholds
    'MIN_GROSS_SPREAD': 0.35,      # Минимальный gross spread (%)
    'MIN_NET_EDGE': 0.15,          # Минимальный net edge после всех издержек (%)
    'MAX_GROSS_SPREAD': 2.5,       # Максимальный gross spread (аномалия) (%)
    
    # Market quality
    'MAX_BID_ASK_SPREAD_PER_LEG': 0.12,  # Максимальный bid-ask spread на одну позицию (%)
    'MAX_DATA_AGE_MS': 1000,       # Максимальный возраст данных (ms)
    
    # Trading costs
    'TAKER_FEE_PCT': 0.05,         # Комиссия taker на сделку (%)
    'SLIPPAGE_PCT': 0.02,          # Ожидаемое проскальзывание на сделку (%)
    
    # Exit strategy
    'TAKE_PROFIT_NET': 0.15,       # Take profit на net edge (%)
    'STOP_LOSS_NET': -0.30,        # Stop loss на net edge (%)
}
