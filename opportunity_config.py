"""Конфигурация для Opportunity Analyzer"""

# Импортируем пороги из главного конфига для синхронизации
from config import OPEN_THRESHOLD, MAX_SPREAD_OPEN, MIN_NET_EDGE

# Net Edge Strategy Thresholds
OPPORTUNITY_CONFIG = {
    # Spread thresholds (синхронизировано с config.py)
    'MIN_GROSS_SPREAD': OPEN_THRESHOLD,   # = 1.0%
    'MIN_NET_EDGE': MIN_NET_EDGE,         # = 0.3%
    'MAX_GROSS_SPREAD': MAX_SPREAD_OPEN,  # = 3.0%
    
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
