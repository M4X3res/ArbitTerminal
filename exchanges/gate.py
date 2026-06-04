"""Gate.io Exchange Connector"""
import json
import asyncio
import websockets
import time
import aiohttp
import hmac
import hashlib
from typing import List, Dict
from datetime import datetime
from exchanges.base import BaseExchange
from exchanges.auth_utils import get_timestamp_ms
from models import MarketData


class GateExchange(BaseExchange):
    """Коннектор для биржи Gate.io Futures"""
    
    WS_URL = "wss://fx-ws.gateio.ws/v4/ws/usdt"
    REST_URL = "https://fx-api.gateio.ws/api/v4"
    
    def __init__(self, api_key: str = None, api_secret: str = None):
        super().__init__("gate", api_key, api_secret)
        self.orderbooks = {}
        self.funding_rates = {}
        self.instruments = []
        self._ping_task = None
    
    async def connect_ws(self):
        """Подключение к WebSocket"""
        self.ws = await websockets.connect(self.WS_URL)
        self._ping_task = asyncio.create_task(self._ping_loop())
        print(f"✅ Gate.io WebSocket connected")
    
    async def _ping_loop(self):
        """Отправка ping каждые 30 секунд"""
        while True:
            try:
                await asyncio.sleep(30)
                if self.ws:
                    await self.ws.ping()
            except Exception as e:
                print(f"Gate.io ping error: {e}")
                break
    
    async def subscribe_orderbook(self, symbols: List[str]):
        """Подписка на orderbook для списка символов"""
        for symbol in symbols:
            # Подписка на order_book
            await self.ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "futures.order_book",
                "event": "subscribe",
                "payload": [symbol, "20", "0"]
            }))
            
            # Подписка на tickers (funding rate)
            await self.ws.send(json.dumps({
                "time": int(time.time()),
                "channel": "futures.tickers",
                "event": "subscribe",
                "payload": [symbol]
            }))
        
        print(f"✅ Gate.io subscribed to {len(symbols)} symbols")
    
    async def subscribe_funding_rate(self, symbols: List[str]):
        """Подписка на funding rate (уже включена в subscribe_orderbook)"""
        pass  # Funding rate подписка происходит через futures.tickers в subscribe_orderbook
    
    async def get_market_data(self, symbol: str) -> MarketData:
        """Получение рыночных данных из WebSocket потока"""
        while True:
            try:
                message = await self.ws.recv()
                data = json.loads(message)
                
                channel = data.get("channel")
                event = data.get("event")
                
                # Пропускаем служебные сообщения
                if event in ["subscribe", "pong"]:
                    continue
                
                # Обработка order_book (событие "all" или "update")
                if channel == "futures.order_book" and event in ["all", "update"]:
                    result = data.get("result", {})
                    contract = result.get("contract")
                    asks = result.get("asks", [])
                    bids = result.get("bids", [])
                    
                    if contract and asks and bids:
                        self.orderbooks[contract] = {
                            "bid": float(bids[0]["p"]),
                            "ask": float(asks[0]["p"])
                        }
                
                # Обработка tickers
                elif channel == "futures.tickers" and event == "update":
                    for ticker in data.get("result", []):
                        contract = ticker.get("contract")
                        funding_rate = ticker.get("funding_rate")
                        
                        if contract and funding_rate is not None:
                            self.funding_rates[contract] = float(funding_rate)
                
                # Возврат данных если доступны
                for contract in list(self.orderbooks.keys()):
                    if contract in self.funding_rates:
                        return MarketData(
                            exchange=self.name,
                            symbol=contract,
                            bid=self.orderbooks[contract]["bid"],
                            ask=self.orderbooks[contract]["ask"],
                            funding_rate=self.funding_rates[contract],
                            timestamp=datetime.now()
                        )
                    
            except Exception as e:
                print(f"Gate.io WS error: {e}")
                await asyncio.sleep(1)
    
    async def get_instruments(self) -> List[str]:
        """Получение списка торговых инструментов"""
        import aiohttp
        
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.REST_URL}/futures/usdt/contracts") as resp:
                data = await resp.json()
                
                if isinstance(data, list):
                    self.instruments = [item["name"] for item in data if not item.get("in_delisting")]
                    return self.instruments
                
                return []
    
    def _sign_gate(self, method: str, url: str, query: str = "", body: str = "") -> Dict[str, str]:
        """Gate.io подпись"""
        timestamp = str(int(time.time()))
        hashed_payload = hashlib.sha512(body.encode()).hexdigest()
        sign_string = f"{method}\n{url}\n{query}\n{hashed_payload}\n{timestamp}"
        signature = hmac.new(self.api_secret.encode(), sign_string.encode(), hashlib.sha512).hexdigest()
        
        return {
            "KEY": self.api_key,
            "Timestamp": timestamp,
            "SIGN": signature
        }
    
    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'market') -> Dict:
        """Размещение ордера"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        settle = "usdt"
        url = f"/api/v4/futures/{settle}/orders"
        body = json.dumps({
            "contract": symbol,
            "size": int(size) if side.lower() == "buy" else -int(size),
            "price": "0",
            "tif": "ioc"
        })
        
        headers = self._sign_gate("POST", url, "", body)
        headers["Content-Type"] = "application/json"
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.REST_URL}{url}", data=body, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    return await resp.json()
        
        return await self._rate_limited_request(_make_request)
    
    async def close_position(self, symbol: str, side: str) -> Dict:
        """Закрытие позиции"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        settle = "usdt"
        url = f"/api/v4/futures/{settle}/positions/{symbol}/close"
        body = json.dumps({})
        
        headers = self._sign_gate("POST", url, "", body)
        headers["Content-Type"] = "application/json"
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.REST_URL}{url}", data=body, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    return await resp.json()
        
        return await self._rate_limited_request(_make_request)
    
    async def get_balance(self) -> float:
        """Получение баланса"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        settle = "usdt"
        url = f"/api/v4/futures/{settle}/accounts"
        
        headers = self._sign_gate("GET", url)
        
        async def _make_request():
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.REST_URL}{url}", headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    data = await resp.json()
                    return float(data.get("available", 0))
        
        return await self._rate_limited_request(_make_request)
