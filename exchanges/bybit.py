"""Bybit exchange connector"""
import asyncio
import json
from datetime import datetime
from typing import List
import aiohttp
from .base import BaseExchange
from .auth_utils import sign_request_hmac, get_timestamp_ms
from models import MarketData


class BybitExchange(BaseExchange):
    """Bybit exchange implementation"""
    
    def __init__(self):
        super().__init__("Bybit")
        self.ws_url = "wss://stream.bybit.com/v5/public/linear"
        self.rest_url = "https://api.bybit.com"
        self.orderbooks = {}
        self.funding_rates = {}
        
    async def connect_ws(self):
        """Connect to WebSocket"""
        self.ws = await self.session.ws_connect(self.ws_url)
        asyncio.create_task(self._ping_loop())
        
    async def _ping_loop(self):
        """Heartbeat to keep connection alive"""
        while True:
            await asyncio.sleep(20)
            if self.ws:
                await self.ws.send_json({"op": "ping"})
    
    async def get_instruments(self) -> List[str]:
        """Get list of tradeable perpetual contracts"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.rest_url}/v5/market/instruments-info",
                    params={"category": "linear"}
                ) as resp:
                    data = await resp.json()
                    return [
                        item["symbol"]
                        for item in data.get("result", {}).get("list", [])
                        if item.get("status") == "Trading"
                    ]
        except Exception as e:
            print(f"Bybit get_instruments error: {e}")
            return []
    
    async def subscribe_orderbook(self, symbols: List[str]):
        """Subscribe to orderbook updates"""
        for symbol in symbols:
            await self.ws.send_json({
                "op": "subscribe",
                "args": [f"orderbook.50.{symbol}"]
            })
    
    async def subscribe_funding_rate(self, symbols: List[str]):
        """Subscribe to funding rate updates"""
        for symbol in symbols:
            await self.ws.send_json({
                "op": "subscribe",
                "args": [f"tickers.{symbol}"]
            })
    
    async def get_market_data(self, symbol: str) -> MarketData:
        """Get market data from WebSocket stream"""
        while True:
            try:
                msg = await self.ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    
                    # Skip system messages
                    if data.get("op") in ["pong", "subscribe"]:
                        continue
                    
                    topic = data.get("topic", "")
                    
                    # Orderbook data
                    if topic.startswith("orderbook"):
                        result = data.get("data", {})
                        sym = result.get("s")
                        bids = result.get("b", [])
                        asks = result.get("a", [])
                        
                        if sym and bids and asks:
                            self.orderbooks[sym] = {
                                "bid": float(bids[0][0]),
                                "ask": float(asks[0][0])
                            }
                    
                    # Funding rate from tickers
                    elif topic.startswith("tickers"):
                        result = data.get("data", {})
                        sym = result.get("symbol")
                        funding_rate = result.get("fundingRate")
                        
                        if sym and funding_rate is not None:
                            self.funding_rates[sym] = float(funding_rate)
                    
                    # Return data if we have both
                    for sym in list(self.orderbooks.keys()):
                        if sym in self.funding_rates:
                            return MarketData(
                                exchange=self.name,
                                symbol=sym,
                                bid=self.orderbooks[sym]["bid"],
                                ask=self.orderbooks[sym]["ask"],
                                funding_rate=self.funding_rates[sym],
                                timestamp=datetime.now()
                            )
                            
            except Exception as e:
                print(f"Bybit WS error: {e}")
                await asyncio.sleep(1)
    
    async def place_order(self, symbol: str, side: str, size: float, order_type: str = 'market'):
        """Открытие позиции"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        async def _make_request():
            try:
                timestamp = get_timestamp_ms()
                
                # Body для POST запроса (Bybit v5 использует JSON body, не query params)
                body = {
                    "category": "linear",
                    "symbol": symbol,
                    "side": side.capitalize(),  # Buy/Sell
                    "orderType": order_type.capitalize(),  # Market/Limit
                    "qty": str(size)
                }
                
                body_json = json.dumps(body)
                recv_window = "5000"
                
                # Подпись для v5 API
                sign_string = f"{timestamp}{self.api_key}{recv_window}{body_json}"
                signature = sign_request_hmac(self.api_secret, sign_string)
                
                headers = {
                    "X-BAPI-API-KEY": self.api_key,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-TIMESTAMP": str(timestamp),
                    "X-BAPI-RECV-WINDOW": recv_window,
                    "Content-Type": "application/json"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.rest_url}/v5/order/create",
                        data=body_json,
                        headers=headers
                    ) as resp:
                        if resp.status == 429:
                            raise Exception("429 Rate limit exceeded")
                        data = await resp.json()
                        if data.get("retCode") == 0:
                            return data["result"]
                        else:
                            raise Exception(f"Bybit order error: {data.get('retMsg')}")
            except Exception as e:
                print(f"Bybit place_order error: {e}")
                raise
        
        return await self._rate_limited_request(_make_request)
    
    async def close_position(self, symbol: str, side: str):
        """Закрытие позиции"""
        if not self.api_key or not self.api_secret:
            raise ValueError("API credentials required")
        
        async def _make_request():
            timestamp = get_timestamp_ms()
            params = {
                "category": "linear",
                "symbol": symbol,
                "timestamp": timestamp,
                "recv_window": 5000
            }
            
            query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
            signature = sign_request_hmac(self.api_secret, f"{timestamp}{self.api_key}{5000}{query_string}")
            
            headers = {
                "X-BAPI-API-KEY": self.api_key,
                "X-BAPI-SIGN": signature,
                "X-BAPI-TIMESTAMP": str(timestamp),
                "X-BAPI-RECV-WINDOW": "5000"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{self.rest_url}/v5/position/close", json=params, headers=headers) as resp:
                    if resp.status == 429:
                        raise Exception("429 Rate limit exceeded")
                    return await resp.json()
        
        return await self._rate_limited_request(_make_request)
    
    async def get_balance(self) -> float:
        """Получение баланса"""
        if not self.api_key or not self.api_secret:
            return 10000.0  # Demo режим
        
        async def _make_request():
            try:
                timestamp = get_timestamp_ms()
                params = {
                    "accountType": "UNIFIED",
                    "timestamp": timestamp,
                    "recv_window": 5000
                }
                
                query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
                signature = sign_request_hmac(self.api_secret, f"{timestamp}{self.api_key}{5000}{query_string}")
                
                headers = {
                    "X-BAPI-API-KEY": self.api_key,
                    "X-BAPI-SIGN": signature,
                    "X-BAPI-TIMESTAMP": str(timestamp),
                    "X-BAPI-RECV-WINDOW": "5000"
                }
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.rest_url}/v5/account/wallet-balance",
                        params=params,
                        headers=headers
                    ) as resp:
                        if resp.status == 429:
                            raise Exception("429 Rate limit exceeded")
                        data = await resp.json()
                        if data.get("result") and data["result"].get("list"):
                            return float(data["result"]["list"][0].get("totalAvailableBalance", 0))
                        return 0.0
            except Exception as e:
                print(f"Bybit get_balance error: {e}")
                return 10000.0
        
        return await self._rate_limited_request(_make_request)
