# ПРОМПТ ДЛЯ ИИ-АГЕНТА: ДОРАБОТКА CRYPTO ARBITRAGE SYSTEM

## КОНТЕКСТ ПРОЕКТА

Ты работаешь над автоматизированной системой межбиржевого криптоарбитража на Python (asyncio). Система торгует на биржах MEXC, Gate.io, Bybit через WebSocket (данные) и REST API (ордера). Текущее состояние: demo-режим работает, live-trading заблокирован критическими багами.

---

## ЧАСТЬ 1: КРИТИЧЕСКИЕ БАГИ (ИСПРАВИТЬ НЕМЕДЛЕННО — до включения live-trading)

### БАГ #1 — Position Sizing: неправильный расчёт объёма ордера

**Файлы:** `exchanges/mexc.py`, `exchanges/gate.py`, `exchanges/bybit.py`  
**Риск:** МГНОВЕННАЯ ЛИКВИДАЦИЯ на live-trading

**Проблема:** `trading_engine.py` передаёт `position_size=100` (USD) в `place_order()`, а биржи интерпретируют это как 100 контрактов. При BTC=$63,000 это открывает позицию на $6,300,000 вместо $100.

**Исправление:** Создать файл `order_utils.py`:

```python
def calculate_order_qty(symbol: str, position_size_usd: float, price: float, leverage: int = 1) -> float:
    """
    Конвертирует USD в количество контрактов.
    position_size_usd=100, price=63000, leverage=5 → notional=500, qty=0.00793 BTC
    """
    notional = position_size_usd * leverage
    qty = notional / price
    # Округление до точности инструмента (минимум 3 знака для BTC, больше для альтов)
    if price > 10000:
        return round(qty, 3)
    elif price > 100:
        return round(qty, 2)
    else:
        return round(qty, 1)
```

Затем в каждом exchange-адаптере заменить:
```python
# БЫЛО:
"qty": str(size)  # size=100 USD → 100 контрактов ❌

# СТАЛО:
qty = calculate_order_qty(symbol, size, current_price, leverage=5)
"qty": str(qty)  # qty=0.00793 → правильно ✅
```

Для получения `current_price` использовать `self.orderbooks[symbol]["ask"]` перед отправкой ордера.

---

### БАГ #2 — Order Side Mapping: неправильный маппинг направления ордера

**Файлы:** `exchanges/bybit.py` (критично), `exchanges/mexc.py`, `exchanges/gate.py`

**Проблема:** `trading_engine.py` передаёт `side='LONG'` или `side='SHORT'`, но:
- Bybit ждёт `'Buy'` / `'Sell'`
- `'SHORT'.capitalize()` = `'Short'` — невалидный параметр, ордер отклоняется

**Исправление:** Добавить в `order_utils.py`:

```python
SIDE_MAP = {
    # exchange: {internal_side: {is_open: api_side}}
    'bybit': {
        'LONG':  {True: 'Buy',  False: 'Sell'},
        'SHORT': {True: 'Sell', False: 'Buy'},
    },
    'mexc': {
        'LONG':  {True: 1, False: 4},   # 1=open long, 4=close long
        'SHORT': {True: 3, False: 2},   # 3=open short, 2=close short
    },
    'gate': {
        'LONG':  {True: 1, False: -1},  # positive=buy, negative=sell
        'SHORT': {True: -1, False: 1},
    },
}

def map_order_side(exchange: str, side: str, is_close: bool = False):
    return SIDE_MAP[exchange][side][not is_close]
```

---

### БАГ #3 — Risk Manager: дублирование позиций по символу

**Файл:** `risk_manager.py`  
**Проблема:** `open_positions` — это `list` символов. При открытии двух позиций BTC на разных биржах список содержит `['BTCUSDT', 'BTCUSDT']`. При закрытии первой `list.remove('BTCUSDT')` удаляет оба вхождения → счётчик позиций ломается.

**Исправление:** Заменить list на dict с ключом `pair_id`:

```python
# БЫЛО:
self.open_positions = []  # list

# СТАЛО:
self.open_positions: Dict[str, dict] = {}  # {pair_id: {symbol, long_ex, short_ex}}

def register_position(self, pair_id: str, symbol: str, exchange_long: str, exchange_short: str):
    self.open_positions[pair_id] = {
        'symbol': symbol,
        'exchange_long': exchange_long,
        'exchange_short': exchange_short,
    }
    self.positions_per_exchange[exchange_long] = self.positions_per_exchange.get(exchange_long, 0) + 1
    self.positions_per_exchange[exchange_short] = self.positions_per_exchange.get(exchange_short, 0) + 1

def unregister_position(self, pair_id: str):
    if pair_id not in self.open_positions:
        return
    pos = self.open_positions.pop(pair_id)
    for ex in [pos['exchange_long'], pos['exchange_short']]:
        self.positions_per_exchange[ex] = max(0, self.positions_per_exchange.get(ex, 1) - 1)

def get_open_count(self) -> int:
    return len(self.open_positions)
```

Обновить все вызовы `register_position` и `unregister_position` в `main.py` и `position_manager.py`, передавая `pair_id`.

---

### БАГ #4 — PnL: расчёт без leverage и без комиссий в position_manager

**Файл:** `position_manager.py`, строки 58-65

**Проблема:** PnL считается без учёта leverage и комиссий, а в `amplitude_strategy.py` с ними. Закрытие происходит по неверному порогу.

**Исправление:** Создать `pnl_calculator.py` и использовать везде:

```python
def calculate_net_pnl(
    entry_price_long: float,
    entry_price_short: float,
    current_price_long: float,
    current_price_short: float,
    position_size_usd: float,
    leverage: int = 5,
    fee_rate: float = 0.0005,
) -> dict:
    pnl_long_pct  = (current_price_long  - entry_price_long)  / entry_price_long  * 100
    pnl_short_pct = (entry_price_short   - current_price_short) / entry_price_short * 100
    gross_pct = pnl_long_pct + pnl_short_pct

    notional  = position_size_usd * leverage
    gross_usd = gross_pct * notional / 100
    fees_usd  = notional * fee_rate * 4   # 4 операции: open/close × 2 биржи
    net_usd   = gross_usd - fees_usd

    return {
        "gross_pct": gross_pct,
        "gross_usd": gross_usd,
        "fees_usd":  fees_usd,
        "net_usd":   net_usd,
    }
```

Заменить расчёт в `position_manager.py`, `amplitude_strategy.py`, `balanced_strategy.py`, `spread_collapse_strategy.py` на вызов этой функции.

---

### БАГ #5 — Symbol Normalization: несовместимые форматы символов

**Файлы:** `market_data_engine.py`, `arbitrage_engine.py`, все exchange-адаптеры

**Проблема:** MEXC возвращает `BTC_USDT`, Bybit — `BTCUSDT`, внутри системы гуляют `BTC/USDT`. `arbitrage_engine` ищет пересечение через `set & set`, и из-за несовпадения форматов `common_symbols` может быть пустым, хотя пары есть на обеих биржах.

**Исправление:** `symbol_utils.py` уже существует — подключить его. Внести в BaseExchange:

```python
# exchanges/base.py
from symbol_utils import normalize_symbol, to_exchange_symbol

class BaseExchange:
    def to_canonical(self, exchange_symbol: str) -> str:
        return normalize_symbol(exchange_symbol)  # всегда BTCUSDT

    def to_local(self, canonical: str) -> str:
        return to_exchange_symbol(canonical, self.name)  # BTC_USDT для mexc/gate
```

В каждом адаптере:
- `get_market_data()` → хранить в `self.orderbooks` по canonical-ключу
- `get_instruments()` → возвращать canonical-символы
- `place_order()` → конвертировать canonical → local перед отправкой

---

### БАГ #6 — WebSocket Race Condition: дублирование `_is_listening`

**Файлы:** `exchanges/mexc.py`, `exchanges/gate.py`, `exchanges/bybit.py`

**Проблема:** Флаг `_is_listening` устанавливается внутри `start_websocket_listener()`, но `market_data_engine.py` может вызвать этот метод дважды (два `asyncio.create_task()`). Первая проверка `if hasattr(self, '_is_listening')` не атомарна.

**Исправление:** Использовать `asyncio.Lock()`:

```python
def __init__(self, ...):
    self._ws_lock = asyncio.Lock()
    self._is_listening = False

async def start_websocket_listener(self, symbols):
    async with self._ws_lock:
        if self._is_listening:
            return
        self._is_listening = True
    # ... остальной код
```

---

## ЧАСТЬ 2: ЛОГИЧЕСКИЕ ОШИБКИ

### ОШИБКА #1 — MarketDataEngine: двойной запуск WebSocket

**Файл:** `market_data_engine.py`, метод `_subscribe_exchange()`

**Проблема:** Метод создаёт `asyncio.create_task(exchange.start_websocket_listener(...))` И затем `asyncio.create_task(self._listen_exchange(...))`. `_listen_exchange` тоже вызывает `exchange.get_market_data()`, который читает из `self.orderbooks`, которые уже заполняются в `start_websocket_listener`. Это создаёт дублирование poll-цикла и лишнюю нагрузку.

**Исправление:** `_listen_exchange` должен только агрегировать данные, которые адаптер уже обновил сам. Убрать из `_listen_exchange` вызов `exchange.get_market_data(symbol)` в цикле по всем символам — вместо этого читать `exchange.orderbooks` напрямую:

```python
async def _listen_exchange(self, name: str, exchange):
    while True:
        try:
            await asyncio.sleep(0.1)
            for symbol, ob in list(exchange.orderbooks.items()):
                canonical = symbol  # уже canonical после БАГ #5
                if canonical in exchange.funding_rates:
                    from models import MarketData
                    from datetime import datetime
                    data = MarketData(
                        exchange=name,
                        symbol=canonical,
                        bid=ob["bid"],
                        ask=ob["ask"],
                        funding_rate=exchange.funding_rates[canonical],
                        timestamp=datetime.now(),
                    )
                    self.market_data[name][canonical] = data
        except Exception as e:
            await asyncio.sleep(1)
```

---

### ОШИБКА #2 — OpportunityAnalyzer: пороги не соответствуют стратегии

**Файлы:** `opportunity_config.py`, `config.py`

**Проблема:** `OPEN_THRESHOLD = 1.0%` в `config.py`, но `MIN_GROSS_SPREAD = 0.35%` в `opportunity_config.py`. Возможности с gross 0.35-1.0% проходят `OpportunityAnalyzer.approve()`, но затем блокируются в `find_opportunities_parallel()` по `threshold=OPEN_THRESHOLD`. Логика противоречива.

**Исправление:** Синхронизировать:
```python
# opportunity_config.py
MIN_GROSS_SPREAD = OPEN_THRESHOLD  # импортировать из config.py, один источник правды
```

---

### ОШИБКА #3 — StrategySelector: импорт несуществующего модуля

**Файл:** `strategy_selector.py`, строка 2

**Проблема:**
```python
from strategies.rest_optimized_strategy import RestOptimizedStrategy
```
Файл `strategies/rest_optimized_strategy.py` не существует (не входит в `strategies/__init__.py`). При запуске `main.py` падает с `ImportError`.

**Исправление:** Создать `strategies/rest_optimized_strategy.py` с классом `RestOptimizedStrategy`, либо убрать импорт и заменить на `BalancedStrategy` как fallback, пока класс не реализован.

---

### ОШИБКА #4 — ArbitrageEngine: ThreadPoolExecutor не закрывается

**Файл:** `arbitrage_engine.py`

**Проблема:** `self.executor = ThreadPoolExecutor(max_workers=max_workers)` создаётся в `__init__`, но нигде не вызывается `executor.shutdown()`. При каждом перезапуске или тесте накапливаются зависшие потоки.

**Исправление:**
```python
def __del__(self):
    self.executor.shutdown(wait=False)

# Также в main.py::cleanup():
if hasattr(self, 'arbitrage_engine'):
    self.arbitrage_engine.executor.shutdown(wait=True)
```

---

### ОШИБКА #5 — config.py: STRATEGY_TYPE по умолчанию ссылается на отсутствующую стратегию

**Файл:** `config.py`, строка 22; `strategy_selector.py`, строка 8

**Проблема:** `STRATEGY_TYPE = 'rest_optimized'` — это значение используется в `StrategySelector.select_strategy()`. Если `RestOptimizedStrategy` не существует, выбирается она по умолчанию для всех спредов.

**Исправление:** Временно установить `STRATEGY_TYPE = 'balanced'` до реализации `rest_optimized_strategy.py`.

---

### ОШИБКА #6 — Telegram token утечка (исторически)

**Файл:** `P0_COMPLETE.md`, `P0_VERIFICATION_REPORT.md`

**Проблема:** В документации явно написан старый токен `7768319583:AAEV2q1mwmnkA9MHDDocKeWqirFNBYx3qdc`. Если репозиторий публичный или был когда-либо расшарен — токен скомпрометирован.

**Действие:** Немедленно зайти в @BotFather → `/revoke` → создать новый токен → добавить в `.env`.

---

## ЧАСТЬ 3: УЛУЧШЕНИЯ АРХИТЕКТУРЫ

### УЛУЧШЕНИЕ #1 — Единый конфиг-файл (устранить дублирование)

**Проблема:** Параметры дублируются в `config.py`, `performance_config.py`, `opportunity_config.py`. Одно изменение требует правки 3 файлов.

**Решение:** Объединить в `settings.py` с секциями:

```python
class Settings:
    # Trading
    OPEN_THRESHOLD: float = 1.0
    MAX_OPEN_POSITIONS: int = 3
    MAX_LEVERAGE: int = 5
    POSITION_SIZE_FRACTION: float = 0.1

    # Performance
    MAX_WORKERS: int = 8
    SYMBOLS_PER_EXCHANGE: int = 50
    ANALYSIS_INTERVAL: float = 0.1

    # Net Edge
    MIN_NET_EDGE: float = 0.30
    MIN_GROSS_SPREAD: float = 1.0  # = OPEN_THRESHOLD
    MAX_GROSS_SPREAD: float = 3.0
    TAKER_FEE_PCT: float = 0.05
    SLIPPAGE_PCT: float = 0.05

settings = Settings()
```

---

### УЛУЧШЕНИЕ #2 — Добавить backtesting-модуль для оптимизации параметров

**Файл:** создать `backtester.py`

Система не имеет возможности проверить стратегию на истории до запуска. Это критично перед live-trading.

**Минимальная реализация:**

```python
class Backtester:
    def __init__(self, strategy, fee_rate=0.0005, leverage=5):
        self.strategy = strategy
        self.fee_rate = fee_rate
        self.leverage = leverage

    def run(self, spread_history: list[dict]) -> dict:
        """
        spread_history: [{timestamp, symbol, exchange_long, exchange_short,
                          spread, price_long, price_short}, ...]
        """
        trades = []
        open_trade = None

        for tick in spread_history:
            if open_trade is None and tick['spread'] >= self.strategy.OPEN_THRESHOLD:
                open_trade = tick.copy()
                open_trade['open_time'] = tick['timestamp']
            elif open_trade:
                should_close, reason = self.strategy.should_close_by_spread(
                    open_trade['spread'], tick['spread'],
                    (tick['timestamp'] - open_trade['open_time']).total_seconds()
                )
                if should_close:
                    pnl = calculate_net_pnl(...)
                    trades.append({**open_trade, 'pnl': pnl, 'reason': reason})
                    open_trade = None

        win_rate = len([t for t in trades if t['pnl']['net_usd'] > 0]) / max(len(trades), 1)
        total_pnl = sum(t['pnl']['net_usd'] for t in trades)
        return {'trades': len(trades), 'win_rate': win_rate, 'total_pnl': total_pnl}
```

---

### УЛУЧШЕНИЕ #3 — Structured Logging вместо print()

**Проблема:** 371 вызов `print()` в 24 файлах. При падении в production невозможно отследить цепочку событий.

**Решение:** Добавить в начало каждого модуля:

```python
import logging
logger = logging.getLogger(__name__)
```

И заменить по правилу:
- `print(f"✅ ...")` → `logger.info(...)`
- `print(f"❌ ...")` → `logger.error(...)`
- `print(f"⚠️ ...")` → `logger.warning(...)`
- `print(f"🔍 RAW MESSAGE: ...")` → `logger.debug(...)` (по умолчанию OFF)

В `main.py` уже есть `RotatingFileHandler` — расширить его на все модули через `logging.config.dictConfig`.

---

### УЛУЧШЕНИЕ #4 — Health Check endpoint

**Зачем:** При запуске на VPS нет способа понять, работает ли система, не подключаясь к консоли.

**Решение:** Добавить минимальный HTTP-сервер (FastAPI или aiohttp):

```python
# health_server.py
from aiohttp import web

async def health_handler(request):
    return web.json_response({
        "status": "ok",
        "open_positions": len(position_manager.positions),
        "total_pnl": position_manager.total_pnl,
        "uptime_sec": int(time.time() - start_time),
        "exchanges_connected": {
            name: bool(ex.ws and not ex.ws.closed)
            for name, ex in exchanges.items()
        }
    })

app = web.Application()
app.router.add_get('/health', health_handler)
```

Запускать как фоновую задачу рядом с основным event loop.

---

### УЛУЧШЕНИЕ #5 — Автоматические unit-тесты для критических функций

**Создать:** `tests/test_order_utils.py`, `tests/test_pnl_calculator.py`, `tests/test_risk_manager.py`

**Минимальный пример:**

```python
# tests/test_order_utils.py
import pytest
from order_utils import calculate_order_qty, map_order_side

def test_qty_btc():
    qty = calculate_order_qty('BTCUSDT', position_size_usd=100, price=63000, leverage=5)
    assert abs(qty - 0.00793) < 0.0001, f"Expected ~0.00793, got {qty}"

def test_qty_not_raw_usd():
    qty = calculate_order_qty('BTCUSDT', position_size_usd=100, price=63000, leverage=5)
    assert qty != 100, "CRITICAL: qty must not equal raw USD amount"

def test_bybit_side_mapping():
    assert map_order_side('bybit', 'LONG',  is_close=False) == 'Buy'
    assert map_order_side('bybit', 'SHORT', is_close=False) == 'Sell'
    assert map_order_side('bybit', 'LONG',  is_close=True)  == 'Sell'
    assert map_order_side('bybit', 'SHORT', is_close=True)  == 'Buy'

def test_mexc_side_mapping():
    assert map_order_side('mexc', 'LONG',  is_close=False) == 1  # open long
    assert map_order_side('mexc', 'SHORT', is_close=True)  == 2  # close short
```

---

## ЧАСТЬ 4: ПОРЯДОК ВЫПОЛНЕНИЯ

**Выполняй строго по этапам. После каждого этапа убеждайся, что `python -m py_compile` проходит без ошибок.**

### Этап 0 (безопасность, 10 мин)
1. Отозвать старый Telegram token через @BotFather
2. Добавить новый в `.env`

### Этап 1 (критические баги, 3-4 часа)
1. Создать `order_utils.py` (БАГ #1 + БАГ #2)
2. Создать `pnl_calculator.py` (БАГ #4)
3. Обновить `risk_manager.py` (БАГ #3)
4. Подключить `symbol_utils.py` в базовый класс и адаптеры (БАГ #5)
5. Исправить `asyncio.Lock()` в адаптерах (БАГ #6)
6. Написать unit-тесты для #1-4 (Улучшение #5)
7. Запустить `pytest tests/` — все тесты должны пройти

### Этап 2 (логические ошибки, 1-2 часа)
1. Создать `strategies/rest_optimized_strategy.py` (ОШИБКА #3)
2. Исправить двойной polling в `market_data_engine.py` (ОШИБКА #1)
3. Синхронизировать `OPEN_THRESHOLD` и `MIN_GROSS_SPREAD` (ОШИБКА #2)
4. Добавить `executor.shutdown()` в `arbitrage_engine.py` (ОШИБКА #4)
5. Установить `STRATEGY_TYPE = 'balanced'` временно (ОШИБКА #5)

### Этап 3 (улучшения, 2-3 часа)
1. Объединить конфиги в `settings.py` (Улучшение #1)
2. Заменить `print()` на `logger.*` в core-модулях (Улучшение #3)
3. Добавить `/health` endpoint (Улучшение #4)
4. Реализовать базовый `backtester.py` (Улучшение #2)

### Этап 4 (тестирование)
1. `python test_system.py` — должно пройти полностью
2. `python smoke_test.py` — 30 сек demo, убедиться что позиции открываются/закрываются
3. Только после успешного прохождения — можно устанавливать `USE_LIVE_TRADING = True` с капиталом не более $100

---

## ЧЕГО НЕ ДЕЛАТЬ

- **Не включать** `USE_LIVE_TRADING = True` до завершения Этапа 1
- **Не изменять** логику WebSocket-подписок без проверки через `test_full_logging.py`
- **Не удалять** demo-режим как fallback
- **Не коммитить** `.env` в git
- **Не запускать** `test_trading_api.py` с реальными API-ключами — он делает реальные запросы баланса

---

## КРИТЕРИИ ГОТОВНОСТИ К LIVE-TRADING

- [ ] `pytest tests/` — 100% pass
- [ ] `test_system.py` — все биржи подключены, funding rate ≠ 0
- [ ] `calculate_order_qty(BTCUSDT, 100, 63000, 5)` возвращает ~0.00793, а не 100
- [ ] `map_order_side('bybit', 'LONG', False)` возвращает `'Buy'`
- [ ] Demo работает 30+ минут без ошибок
- [ ] `/health` endpoint возвращает статус всех бирж
- [ ] Telegram bot-token обновлён
- [ ] IP whitelist на всех биржах
- [ ] Вывод средств отключён в API-настройках бирж
- [ ] Начальный капитал ≤ $100 на первый запуск
