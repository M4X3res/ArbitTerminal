# REST API Trading Methods

## Overview

Все 4 биржи теперь поддерживают торговые операции через REST API с HMAC-SHA256 аутентификацией.

## Реализованные методы

Каждая биржа реализует 3 основных торговых метода:

### 1. `place_order(symbol, side, size, order_type='market')`
Открытие позиции (лонг или шорт)

**Параметры:**
- `symbol` (str): Торговая пара (например, "BTC_USDT", "BTCUSDT")
- `side` (str): Направление - `"buy"` (лонг) или `"sell"` (шорт)
- `size` (float): Размер позиции
- `order_type` (str): Тип ордера - `"market"` или `"limit"` (по умолчанию market)

**Возвращает:** Dict с результатом размещения ордера

### 2. `close_position(symbol, side)`
Закрытие позиции

**Параметры:**
- `symbol` (str): Торговая пара
- `side` (str): Направление позиции для закрытия

**Возвращает:** Dict с результатом закрытия

### 3. `get_balance()`
Получение доступного баланса

**Возвращает:** float - доступный баланс в USDT

## Использование

### Инициализация с API ключами

```python
from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange
from exchanges.bybit import BybitExchange
from exchanges.asterdex import AsterDEXExchange

# MEXC
mexc = MEXCExchange(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Gate.io
gate = GateExchange(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# Bybit
bybit = BybitExchange(
    api_key="your_api_key",
    api_secret="your_api_secret"
)

# AsterDEX
asterdex = AsterDEXExchange(
    api_key="your_api_key",
    api_secret="your_api_secret"
)
```

### Примеры операций

```python
import asyncio

async def trading_example():
    # Получить баланс
    balance = await mexc.get_balance()
    print(f"Balance: {balance} USDT")
    
    # Открыть лонг позицию
    order = await mexc.place_order(
        symbol="BTC_USDT",
        side="buy",
        size=0.001,
        order_type="market"
    )
    print(f"Order: {order}")
    
    # Закрыть позицию
    result = await mexc.close_position(
        symbol="BTC_USDT",
        side="buy"
    )
    print(f"Closed: {result}")

asyncio.run(trading_example())
```

## Особенности по биржам

### MEXC
- **REST API:** `https://contract.mexc.com`
- **Аутентификация:** HMAC-SHA256 с `ApiKey` в headers
- **Форматы:**
  - Side: 1=long, 2=short
  - Type: 5=market, 1=limit

### Gate.io
- **REST API:** `https://fx-api.gateio.ws/api/v4`
- **Аутентификация:** HMAC-SHA512 с специальным форматом подписи
- **Особенности:**
  - Размер позиции: положительный для buy, отрицательный для sell
  - Требует `settle` параметр (usdt)

### Bybit
- **REST API:** `https://api.bybit.com`
- **Аутентификация:** HMAC-SHA256 с headers `X-BAPI-*`
- **Особенности:**
  - Category: "linear" для USDT perpetuals
  - Unified Trading Account API (v5)

### AsterDEX
- **REST API:** `https://fapi.asterdex.com`
- **Аутентификация:** Binance-совместимый HMAC-SHA256
- **Особенности:**
  - Полностью совместим с Binance Futures API
  - Использует `/fapi/v1/` эндпоинты

## Безопасность

⚠️ **ВАЖНО:**

1. **Никогда не коммитьте API ключи в git**
2. Используйте `.env` файл для хранения ключей:
   ```
   MEXC_API_KEY=your_key
   MEXC_API_SECRET=your_secret
   ```
3. Ограничьте права API ключей только необходимыми (торговля, чтение)
4. Используйте IP whitelist где возможно
5. Тестируйте сначала на demo/testnet аккаунтах

## Получение API ключей

- **MEXC:** https://www.mexc.com/user/api-management
- **Gate.io:** https://www.gate.io/myaccount/api_key_manage
- **Bybit:** https://www.bybit.com/app/user/api-management
- **AsterDEX:** https://www.asterdex.com/account/api

## Обработка ошибок

Все методы могут выбросить исключения:

```python
try:
    balance = await exchange.get_balance()
except ValueError as e:
    print(f"Credentials error: {e}")
except Exception as e:
    print(f"API error: {e}")
```

## Интеграция с арбитражной системой

Торговые методы интегрируются с `TradingEngine`:

```python
from trading_engine import TradingEngine

engine = TradingEngine(exchanges)

# Открыть арбитражную пару
await engine.open_position(
    exchange_long="mexc",
    exchange_short="bybit",
    symbol="BTCUSDT",
    quantity=0.001
)
```

## Тестирование

Запустите тест:
```bash
.venv\Scripts\python.exe test_trading_api.py
```

**Внимание:** Замените API ключи на реальные в `test_trading_api.py`

## Лимиты

Каждая биржа имеет свои rate limits:
- **MEXC:** ~10 запросов/сек
- **Gate.io:** ~100 запросов/10 сек
- **Bybit:** ~10 запросов/сек  
- **AsterDEX:** ~20 запросов/сек

Система автоматически обрабатывает ошибки 429 (Too Many Requests).
