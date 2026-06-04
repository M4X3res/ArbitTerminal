# 🔧 Исправления Exchange API

На основе официальной документации бирж.

---

## 📚 BYBIT

**Документация:** https://bybit-exchange.github.io/docs/v5/order/create-order

### Authentication (v5)
```python
timestamp = str(int(time.time() * 1000))  # Миллисекунды!
recv_window = "5000"
query_string = "accountType=UNIFIED&timestamp={timestamp}"

# Строка для подписи
sign_string = f"{timestamp}{api_key}{recv_window}{query_string}"
signature = hmac.new(api_secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()

headers = {
    'X-BAPI-API-KEY': api_key,
    'X-BAPI-SIGN': signature,
    'X-BAPI-TIMESTAMP': timestamp,
    'X-BAPI-RECV-WINDOW': recv_window,
    'Content-Type': 'application/json'
}
```

### Place Order
```python
POST /v5/order/create
{
    "category": "linear",      # ОБЯЗАТЕЛЬНО для futures!
    "symbol": "BTCUSDT",
    "side": "Buy",             # Buy или Sell (с заглавной)
    "orderType": "Market",     # Market или Limit
    "qty": "0.001"             # Строка!
}
```

### Get Balance
```python
GET /v5/account/wallet-balance?accountType=UNIFIED&timestamp={ts}

Response:
{
    "retCode": 0,
    "result": {
        "list": [{
            "totalAvailableBalance": "10000.50"
        }]
    }
}
```

---

## 📚 MEXC

**Документация:** https://www.mexc.com/api-docs/futures/account-and-trading-endpoints/place-order

### Authentication
```python
# MEXC использует query string + signature в параметрах
timestamp = int(time.time() * 1000)
params = {
    "symbol": "BTCUSDT",
    "price": "50000",
    "vol": "1",
    "side": 1,  # 1=open long, 2=close short, 3=open short, 4=close long
    "type": 5,  # 5=market, 1=limit
    "openType": 2,  # 2=cross margin
    "timestamp": timestamp,
    "recvWindow": 5000
}

# Сортировка + создание query string
query_string = '&'.join([f"{k}={v}" for k, v in sorted(params.items())])
signature = hmac.new(api_secret.encode(), query_string.encode(), hashlib.sha256).hexdigest()

params["signature"] = signature

headers = {
    'X-MEXC-APIKEY': api_key,
    'Content-Type': 'application/json'
}
```

### Place Order
```python
POST /api/v1/private/order/create
{
    "symbol": "BTC_USDT",
    "price": "50000",
    "vol": "0.001",
    "side": 1,           # 1=open long, 2=close short, 3=open short, 4=close long
    "type": 5,           # 5=market
    "openType": 2,       # 2=cross margin
    "leverage": 10,
    "timestamp": 1234567890,
    "signature": "abc123..."
}
```

---

## 📚 GATE.IO

**Документация:** https://www.gate.io/docs/developers/futures (403 - нужен VPN)

### Authentication
```python
timestamp = str(int(time.time()))  # Секунды (не миллисекунды!)
method = "GET"
url_path = "/api/v4/futures/usdt/accounts"
query_string = ""  # Пустая строка если нет query params
body = ""          # Пустая строка для GET

# Hash body
body_hash = hashlib.sha512(body.encode()).hexdigest()

# Строка для подписи
sign_string = f"{method}\n{url_path}\n{query_string}\n{body_hash}\n{timestamp}"
signature = hmac.new(api_secret.encode(), sign_string.encode(), hashlib.sha512).hexdigest()

headers = {
    'KEY': api_key,
    'Timestamp': timestamp,
    'SIGN': signature
}
```

### Get Balance
```python
GET https://fx-api.gateio.ws/api/v4/futures/usdt/accounts

Response:
{
    "total": "10000.50",
    "unrealised_pnl": "0",
    "available": "10000.50"
}
```

### Place Order
```python
POST /api/v4/futures/usdt/orders
{
    "contract": "BTC_USDT",
    "size": 1,           # Положительный для long, отрицательный для short
    "price": "50000",    # 0 для market
    "tif": "ioc"         # ioc для market
}
```

---

## ✅ КЛЮЧЕВЫЕ ОТЛИЧИЯ

| Биржа | Timestamp | Hash | Header API Key | Signature Location |
|-------|-----------|------|----------------|-------------------|
| **Bybit** | Миллисекунды | SHA256 | X-BAPI-API-KEY | X-BAPI-SIGN |
| **MEXC** | Миллисекунды | SHA256 | X-MEXC-APIKEY | В params |
| **Gate.io** | Секунды | SHA512 | KEY | SIGN |

---

## 🎯 ПРОБЛЕМЫ В ТЕКУЩЕМ КОДЕ

### 1. Gate.io
❌ **URL path дублирование** - REST_URL уже содержит `/api/v4`  
❌ **Неправильная подпись** - нужен body hash  
✅ **Исправление:** Использовать полный URL без REST_URL константы

### 2. Bybit
❌ **self.session не создан** - `None.get()` ошибка  
❌ **Проверка response structure** - нужно проверять `retCode`  
✅ **Исправление:** Создавать `aiohttp.ClientSession()` в каждом методе

### 3. MEXC
❌ **Mock методы** - всегда возвращают demo данные  
✅ **Исправление:** Реализовать реальные REST запросы

---

## 🚀 РЕКОМЕНДАЦИИ

1. **Используйте официальные SDK** (если есть) вместо ручной реализации
2. **Тестируйте на testnet** перед live торговлей
3. **Логируйте все запросы** для отладки подписи
4. **Проверяйте timestamp** - серверное время может отличаться
