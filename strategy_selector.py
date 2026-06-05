"""Strategy Selector — динамический выбор стратегии по спреду"""
from strategies import AmplitudeStrategy, BalancedStrategy, SpreadCollapseStrategy
from strategies.rest_optimized_strategy import RestOptimizedStrategy
from config import STRATEGY_TYPE, REST_TAKE_PROFIT_PCT, REST_STOP_LOSS_PCT, REST_MAX_HOLD_TIME, REST_TRAILING_ACTIVATION


class StrategySelector:
    """Выбор стратегии закрытия в зависимости от размера спреда"""
    
    def __init__(self):
        # Инициализируем все стратегии
        self.amplitude = AmplitudeStrategy()
        self.balanced = BalancedStrategy()
        self.collapse = SpreadCollapseStrategy()
        self.rest_optimized = RestOptimizedStrategy(
            take_profit_pct=REST_TAKE_PROFIT_PCT,
            stop_loss_pct=REST_STOP_LOSS_PCT,
            max_hold_time_sec=REST_MAX_HOLD_TIME,
            trailing_stop_activation=REST_TRAILING_ACTIVATION
        )
    
    def select_strategy(self, spread: float):
        """
        Выбор стратегии по конфигурации или по спреду:
        - rest_optimized: REST-оптимизированная (рекомендуется)
        - amplitude: амплитудная (0.7-2%)
        - balanced: сбалансированная (2-5%)
        - collapse: схлопывание (5%+)
        """
        # Если в конфиге указана rest_optimized - используем её всегда
        if STRATEGY_TYPE == 'rest_optimized':
            return self.rest_optimized, "rest_optimized"
        
        # Иначе выбираем по спреду
        if spread < 2.0:
            return self.amplitude, "amplitude"
        elif spread < 5.0:
            return self.balanced, "balanced"
        else:
            return self.collapse, "collapse"
    
    def should_close(self, trade, market_data):
        """Проверка закрытия через стратегию которая была при открытии"""
        # Используем стратегию сохраненную в trade
        strategy_name = getattr(trade, 'strategy_name', 'balanced')
        
        if strategy_name == 'rest_optimized':
            return self.rest_optimized.should_close(trade, market_data)
        elif strategy_name == 'amplitude':
            return self.amplitude.should_close(trade, market_data)
        elif strategy_name == 'collapse':
            return self.collapse.should_close(trade, market_data)
        else:
            return self.balanced.should_close(trade, market_data)
