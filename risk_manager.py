"""Risk Manager — управление рисками"""
from typing import Dict
from models import ArbitragePair
from config import (
    MAX_POSITION_SIZE, 
    MAX_OPEN_POSITIONS, 
    MAX_SPREAD_OPEN,
    POSITION_SIZE_FRACTION,
    MAX_ORDERS_PER_COIN
)


class RiskManager:
    """Управление рисками арбитража"""
    
    def __init__(self, initial_balance: float = 1000):
        self.balance = initial_balance
        self.open_positions = []
        self.orders_per_coin = {}
    
    def calculate_position_size(self) -> float:
        """Расчёт размера позиции (1/10 от баланса)"""
        return self.balance * POSITION_SIZE_FRACTION
    
    def check_opportunity(self, opportunity: ArbitragePair, market_data: Dict) -> Dict:
        """Проверка арбитражной возможности на риски"""
        
        # 1. Проверка количества открытых позиций
        if len(self.open_positions) >= MAX_OPEN_POSITIONS:
            return {"approved": False, "reason": f"Max positions reached ({MAX_OPEN_POSITIONS})"}
        
        # 2. Проверка лимита ордеров на монету
        coin_orders = self.orders_per_coin.get(opportunity.symbol, 0)
        if coin_orders >= MAX_ORDERS_PER_COIN:
            return {"approved": False, "reason": f"Max orders per {opportunity.symbol} ({MAX_ORDERS_PER_COIN})"}
        
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
    
    def register_position(self, symbol: str):
        """Регистрация открытой позиции"""
        self.open_positions.append(symbol)
        self.orders_per_coin[symbol] = self.orders_per_coin.get(symbol, 0) + 1
    
    def unregister_position(self, symbol: str):
        """Удаление закрытой позиции"""
        if symbol in self.open_positions:
            self.open_positions.remove(symbol)
        if symbol in self.orders_per_coin:
            self.orders_per_coin[symbol] -= 1

