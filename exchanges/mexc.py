"""MEXC Exchange Connector"""
import json
import asyncio
import websockets
import hmac
import hashlib
import time
from typing import List, Dict
from datetime import datetime
import aiohttp
from exchanges.base import BaseExchange
from models import MarketData


class MEXCExchange(BaseExchange):
    """Коннектор для биржи MEXC"""
    
    WS_URL = "wss://contract.mexc.com/edge"
    REST_URL = "https://contract.mexc.com"
    
    def __init__(self, api_key: str = "", api_secret: str = ""):
        super().__init__("mexc", api_key, api_secret)
        self.orderbooks = {}
        self.funding_rates = {}
        self.instruments = []
        self.ws_running = False
    
    async def start_websocket_listener(self, symbols: List[str]):
        """Запуск WebSocket слушателя с автоматическим реконнектом"""
        # 🔒 Жесткая блокировка повторного запуска
        if hasattr(self, '_is_listening') and self._is_listening:
            return
        self._is_listening = True
        
        self.ws_running = True
        
        while self.ws_running:
            try:
                # 🔧 FIX: Закрываем старое соединение перед реконнектом
                if hasattr(self, 'ws') and self.ws:
                    try:
                        await self.ws.close()
                    except Exception:
                        pass
                    self.ws = None
                
                await self.connect_ws()
                await self.subscribe_orderbook(symbols)
                
                # 🔧 FIX: Явный recv() вместо async for для предотвращения race condition
                while self.ws_running and self.ws:
                    try:
                        message = await self.ws.recv()
                        data = json.loads(message)
                        await self._handle_message(data)
                    except websockets.exceptions.ConnectionClosed:
                        print("⚠️ MEXC WS connection closed, reconnecting...")
                        break
                    
            except Exception as e:
                print(f"❌ MEXC WebSocket error: {e}, reconnecting...")
                await asyncio.sleep(2)
    
    async def stop_websocket(self):
        """Остановка WebSocket"""
        self.ws_running = False
        if self.ws:
            await self.ws.close()
    
    def _normalize_symbol(self, symbol: str) -> str:
        """Нормализация символа к виду BTC/USDT"""
        return symbol.replace("_", "/")
    
    def _exchange_format_symbol(self, symbol: str) -> str:
        """Конвертация BTC/USDT в формат биржи BTC_USDT"""
        return symbol.replace("/", "_")
    
    async def _handle_message(self, data: dict):
        """Обработка входящего сообщения"""
        print(f"🔍 MEXC RAW MESSAGE: {data}")  # Отладка входящих сообщений
        try:
            # Обработка depth
            if data.get("channel") == "push.depth":
                symbol = self._normalize_symbol(data["symbol"])
                asks = data["data"]["asks"]
                bids = data["data"]["bids"]
                
                if asks and bids:
                    self.orderbooks[symbol] = {
                        "bid": float(bids[0][0]),
                        "ask": float(asks[0][0])
                    }
                    print(f"✅ MEXC orderbook saved: {symbol}")
            
            # Обработка funding rate
            elif data.get("channel") == "push.funding.rate":
                symbol = self._normalize_symbol(data["symbol"])
                self.funding_rates[symbol] = float(data["data"]["rate"])
                print(f"✅ MEXC funding rate saved: {symbol}")
        except Exception as e:
            print(f"⚠️ MEXC message parse error: {e}")
    
    async def connect_ws(self):
        """Подключение к WebSocket"""
        self.ws = await websockets.connect(self.WS_URL)
        print(f"✅ MEXC WebSocket connected")
    
    async def subscribe_orderbook(self, symbols: List[str]):
        """Подписка на orderbook для списка символов"""
        for symbol in symbols:
            exchange_symbol = self._exchange_format_symbol(symbol)
            # Подписка на depth
            await self.ws.send(json.dumps({
                "method": "sub.depth",
                "param": {"symbol": exchange_symbol}
            }))
            
            # Подписка на funding rate
            await self.ws.send(json.dumps({
                "method": "sub.funding.rate",
                "param": {"symbol": exchange_symbol}
            }))
        
        print(f"✅ MEXC subscribed to {len(symbols)} symbols")
    
    async def subscribe_funding_rate(self, symbols: List[str]):
        """Подписка на funding rate (уже включена в subscribe_orderbook)"""
        pass  # Funding rate подписка происходит в subscribe_orderbook
    
    async def get_market_data(self, symbol: str = None) -> MarketData:
        """Получение рыночных данных из локального хранилища"""
        # Если symbol не указан, возвращаем любые доступные данные
        if symbol is None:
            for sym in self.orderbooks.keys():
                return MarketData(
                    exchange=self.name,
                    symbol=sym,
                    bid=self.orderbooks[sym]["bid"],
                    ask=self.orderbooks[sym]["ask"],
                    funding_rate=self.funding_rates.get(sym, 0.0),
                    timestamp=datetime.now()
                )
            return None
        
        # Просто читаем готовые данные для конкретного символа
        if symbol in self.orderbooks:
            return MarketData(
                exchange=self.name,
                symbol=symbol,
                bid=self.orderbooks[symbol]["bid"],
                ask=self.orderbooks[symbol]["ask"],
                funding_rate=self.funding_rates.get(symbol, 0.0),
                timestamp=datetime.now()
            )
        return None
    
    async def get_instruments(self) -> List[str]:
        """Получение списка торговых инструментов"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.REST_URL}/api/v1/contract/detail") as resp:
                data = await resp.json()
                
                if data.get("success"):
                    self.instruments = [item["symbol"] for item in data.get("data", [])]
                    return self.instruments
                
                return []
    
    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'market') -> Dict:
        """Открытие позиции"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required for trading")
        
        params = {
            "symbol": symbol,
            "side": 1 if side.lower() == "buy" else 2,  # 1=long, 2=short
            "type": 5 if order_type == "market" else 1,  # 5=market, 1=limit
            "vol": str(size),
            "timestamp": get_timestamp_ms()
        }
        
        query_string = build_query_string(params)
        signature = sign_request_hmac(self.api_secret, query_string)
        params["sign"] = signature
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                headers = {"ApiKey": self.api_key, "Request-Time": str(params["timestamp"])}
                async with session.post(f"{self.REST_URL}/api/v1/private/order/submit", json=params, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    return await resp.json()
        
        return await self._rate_limited_request(_make_request)
    
    async def close_position(self, symbol: str, side: str) -> Dict:
        """Закрытие позиции"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required for trading")
        
        params = {
            "symbol": symbol,
            "timestamp": get_timestamp_ms()
        }
        
        query_string = build_query_string(params)
        signature = sign_request_hmac(self.api_secret, query_string)
        params["sign"] = signature
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                headers = {"ApiKey": self.api_key}
                async with session.post(f"{self.REST_URL}/api/v1/private/position/close_all", json=params, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    return await resp.json()
        
        return await self._rate_limited_request(_make_request)
    
    async def get_balance(self) -> float:
        """Получение баланса"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        params = {"timestamp": get_timestamp_ms()}
        query_string = build_query_string(params)
        signature = sign_request_hmac(self.api_secret, query_string)
        params["sign"] = signature
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                headers = {"ApiKey": self.api_key}
                async with session.get(f"{self.REST_URL}/api/v1/private/account/assets", params=params, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    data = await resp.json()
                    if data.get("success") and data.get("data"):
                        return float(data["data"][0].get("availableBalance", 0))
                    return 0.0
        
        return await self._rate_limited_request(_make_request)


