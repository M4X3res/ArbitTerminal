"""Классическая стратегия схлопывания спреда"""
from typing import Dict
from datetime import datetime
from models import Trade, MarketData


class SpreadCollapseStrategy:
    """Стратегия закрытия при схлопывании спреда"""
    
    def __init__(self, 
                 collapse_threshold: float = 0.1,  # Спред схлопнулся до 0.1%
                 min_profit_pct: float = 0.05,      # Минимальная прибыль 0.05%
                 max_hold_time_sec: float = 3600):  # Макс 1 час
        
        self.collapse_threshold = collapse_threshold
        self.min_profit_pct = min_profit_pct
        self.max_hold_time_sec = max_hold_time_sec
    
    def calculate_current_spread(self, trade: Trade, market_data: Dict[str, Dict[str, MarketData]]) -> float:
        """Расчёт текущего спреда"""
        long_data = market_data.get(trade.exchange_long, {}).get(trade.symbol)
        short_data = market_data.get(trade.exchange_short, {}).get(trade.symbol)
        
        if not long_data or not short_data:
            return None
        
        # Текущий спред (SHORT bid - LONG ask)
        current_spread = (short_data.bid - long_data.ask) / long_data.ask * 100
        return current_spread
    
    def calculate_pnl_pct(self, trade: Trade, market_data: Dict[str, Dict[str, MarketData]]) -> float:
        """Расчёт PnL в процентах"""
        long_data = market_data.get(trade.exchange_long, {}).get(trade.symbol)
        short_data = market_data.get(trade.exchange_short, {}).get(trade.symbol)
        
        if not long_data or not short_data:
            return 0.0
        
        # PnL на каждой стороне
        pnl_long = (long_data.bid - trade.entry_price_long) / trade.entry_price_long * 100
        pnl_short = (trade.entry_price_short - short_data.ask) / trade.entry_price_short * 100
        
        return pnl_long + pnl_short
    
    def should_close(self, trade: Trade, market_data: Dict[str, Dict[str, MarketData]]) -> tuple[bool, str]:
        """Проверка условий закрытия"""
        current_spread = self.calculate_current_spread(trade, market_data)
        
        if current_spread is None:
            return False, ""
        
        pnl_pct = self.calculate_pnl_pct(trade, market_data)
        time_held = (datetime.now() - trade.open_time).total_seconds()
        
        # === УСЛОВИЕ 1: Спред схлопнулся ===
        if current_spread <= self.collapse_threshold and pnl_pct >= self.min_profit_pct:
            return True, f"Spread collapsed: {current_spread:.3f}% (entry: {trade.entry_spread:.3f}%), PnL: {pnl_pct:.3f}%"
        
        # === УСЛОВИЕ 2: Достигнута целевая прибыль ===
        # Для спреда 5%+ целимся на 70% от него
        target_profit = trade.entry_spread * 0.7
        if pnl_pct >= target_profit:
            return True, f"Target profit: {pnl_pct:.3f}% >= {target_profit:.3f}%"
        
        # === УСЛОВИЕ 3: Stop-loss при развороте ===
        if current_spread < 0 and trade.entry_spread > 0:
            return True, f"Spread reversal: {current_spread:.3f}% (was {trade.entry_spread:.3f}%)"
        
        # === УСЛОВИЕ 4: Timeout ===
        if time_held > self.max_hold_time_sec:
            return True, f"Timeout: {time_held:.0f}s (PnL: {pnl_pct:.3f}%)"
        
        return False, ""
    
    def get_statistics(self, symbol: str) -> Dict:
        """Статистика (для совместимости с AmplitudeStrategy)"""
        return {
            "samples": 0,
            "avg_amplitude": 0,
            "max_amplitude": 0,
            "threshold": self.collapse_threshold
        }
