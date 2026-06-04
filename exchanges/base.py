"""Базовый класс для интеграции с биржами"""
from abc import ABC, abstractmethod
from typing import List, Dict
import aiohttp
from models import MarketData
from rate_limiter import get_rate_limiter


class BaseExchange(ABC):
    """Базовый интерфейс биржи"""
    
    def __init__(self, name: str, api_key: str = None, api_secret: str = None):
        self.name = name
        self.api_key = api_key
        self.api_secret = api_secret
        self.ws = None
        self.session = None
        self.rate_limiter = get_rate_limiter(name)  # Rate limiter для REST API
    
    async def initialize(self):
        """Инициализация HTTP сессии и WebSocket"""
        self.session = aiohttp.ClientSession()
        await self.connect_ws()
    
    async def close(self):
        """Закрытие соединений"""
        if self.ws:
            await self.ws.close()
        if self.session:
            await self.session.close()
    
    async def _rate_limited_request(self, coro):
        """Выполнить HTTP запрос с rate limiting"""
        return await self.rate_limiter.execute_with_retry(coro)
        
    @abstractmethod
    async def connect_ws(self):
        """Подключение к WebSocket"""
        pass
    
    @abstractmethod
    async def subscribe_orderbook(self, symbols: List[str]):
        """Подписка на orderbook"""
        pass
    
    @abstractmethod
    async def get_market_data(self, symbol: str) -> MarketData:
        """Получение рыночных данных"""
        pass
    
    @abstractmethod
    async def get_instruments(self) -> List[str]:
        """Получение списка инструментов"""
        pass
    
    @abstractmethod
    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'market') -> Dict:
        """Размещение ордера"""
        pass
    
    @abstractmethod
    async def close_position(self, symbol: str, side: str) -> Dict:
        """Закрытие позиции"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> float:
        """Получение баланса"""
        pass
