"""Risk Manager — управление рисками"""
from typing import Dict
from models import ArbitragePair
from config import (
    MAX_POSITION_SIZE, 
    MAX_OPEN_POSITIONS, 
    MAX_SPREAD_OPEN,
    POSITION_SIZE_FRACTION,
    MAX_POSITIONS_PER_EXCHANGE
)

# Минимальный объём ордера на каждой бирже (USD)
EXCHANGE_MIN_ORDER = {
    'mexc': 5,
    'gate': 5,
    'bybit': 10,
    'asterdex': 10
}


class RiskManager:
    """Управление рисками арбитража"""
    
    def __init__(self, initial_balance: float = 1000):
        self.balance = initial_balance
        self.open_positions = []
        self.positions_per_exchange = {}  # Подсчет позиций по биржам
    
    def calculate_position_size(self) -> float:
        """Расчёт размера позиции (1/10 от баланса)"""
        return self.balance * POSITION_SIZE_FRACTION
    
    def check_opportunity(self, opportunity: ArbitragePair, market_data: Dict) -> Dict:
        """Проверка арбитражной возможности на риски"""
        
        # 1. Проверка количества открытых позиций (общее)
        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return {"approved": False, "reason": f"Max positions reached ({MAX_OPEN_POSITIONS})"}
        
        # 2. Проверка лимита позиций на биржах
        long_positions = self.positions_per_exchange.get(opportunity.exchange_long, 0)
        short_positions = self.positions_per_exchange.get(opportunity.exchange_short, 0)
        
        if long_positions >= MAX_POSITIONS_PER_EXCHANGE:
            return {"approved": False, "reason": f"Max positions on {opportunity.exchange_long} ({MAX_POSITIONS_PER_EXCHANGE})"}
        
        if short_positions >= MAX_POSITIONS_PER_EXCHANGE:
            return {"approved": False, "reason": f"Max positions on {opportunity.exchange_short} ({MAX_POSITIONS_PER_EXCHANGE})"}
        
        # 3. Проверка спреда (минимум и максимум)
        if opportunity.spread < 0.1:
            return {"approved": False, "reason": "Spread too low (<0.1%)"}
        
        if opportunity.spread > MAX_SPREAD_OPEN:
            return {"approved": False, "reason": f"Spread too high (>{MAX_SPREAD_OPEN}%) - anomaly"}
        
        # 4. Проверка funding rate
        if abs(opportunity.funding_diff) > 0.01:  # 1%
            return {"approved": False, "reason": "Funding rate diff too high (>1%)"}
        
        # 5. Проверка баланса
        position_size = self.calculate_position_size()
        if position_size < 10:  # Минимум 10 USD
            return {"approved": False, "reason": "Insufficient balance"}
        
        # 5.1. Проверка минимального объёма ордера по биржам
        min_long = EXCHANGE_MIN_ORDER.get(opportunity.exchange_long, 10)
        min_short = EXCHANGE_MIN_ORDER.get(opportunity.exchange_short, 10)
        min_required = max(min_long, min_short)
        
        if position_size < min_required:
            return {"approved": False, "reason": f"Position size ${position_size:.2f} below exchange minimum ${min_required}"}
        
        # 6. Проверка спреда bid-ask (ликвидность)
        long_data = market_data.get(opportunity.exchange_long, {}).get(opportunity.symbol)
        short_data = market_data.get(opportunity.exchange_short, {}).get(opportunity.symbol)
        
        if long_data and short_data:
            spread_long = (long_data.ask - long_data.bid) / long_data.bid * 100
            spread_short = (short_data.ask - short_data.bid) / short_data.bid * 100
            
            if spread_long > 0.5 or spread_short > 0.5:
                return {"approved": False, "reason": "Bid-ask spread too wide (low liquidity)"}
        
        # ✅ Одобрено
        return {
            "approved": True,
            "reason": "All checks passed",
            "position_size": position_size
        }
    
    def register_position(self, symbol: str, exchange_long: str, exchange_short: str):
        """Регистрация открытой позиции"""
        self.open_positions.append(symbol)
        # Увеличиваем счетчики для обеих бирж
        self.positions_per_exchange[exchange_long] = self.positions_per_exchange.get(exchange_long, 0) + 1
        self.positions_per_exchange[exchange_short] = self.positions_per_exchange.get(exchange_short, 0) + 1
    
    def unregister_position(self, symbol: str, exchange_long: str = None, exchange_short: str = None):
        """Удаление закрытой позиции"""
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
        
        # Уменьшаем счетчики для бирж
        if exchange_long and exchange_long in self.positions_per_exchange:
            self.positions_per_exchange[exchange_long] -= 1
            if self.positions_per_exchange[exchange_long] <= 0:
                del self.positions_per_exchange[exchange_long]
        
        if exchange_short and exchange_short in self.positions_per_exchange:
            self.positions_per_exchange[exchange_short] -= 1
            if self.positions_per_exchange[exchange_short] <= 0:
                del self.positions_per_exchange[exchange_short]
    
    def update_balance(self, pnl: float):
        """Обновление баланса после закрытия позиции"""
        self.balance += pnl
        print(f"💰 Balance updated: {self.balance:.2f} USD (PnL: {pnl:+.2f} USD)")

