"""Strategy Selector — динамический выбор стратегии по спреду"""
from strategies import AmplitudeStrategy, BalancedStrategy, SpreadCollapseStrategy


class StrategySelector:
    """Выбор стратегии закрытия в зависимости от размера спреда"""
    
    def __init__(self):
        # Инициализируем все стратегии
        self.amplitude = AmplitudeStrategy()
        self.balanced = BalancedStrategy()
        self.collapse = SpreadCollapseStrategy()
    
    def select_strategy(self, spread: float):
        """
        Выбор стратегии по спреду:
        - 0.7-2%: amplitude (быстрый скальпинг)
        - 2-5%: balanced (средняя)
        - 5%+: collapse (схлопывание)
        """
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
        
        if strategy_name == 'amplitude':
            return self.amplitude.should_close(trade, market_data)
        elif strategy_name == 'collapse':
            return self.collapse.should_close(trade, market_data)
        else:
            return self.balanced.should_close(trade, market_data)
