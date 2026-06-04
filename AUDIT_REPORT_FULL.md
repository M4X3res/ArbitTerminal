# 🔍 ТЕХНИЧЕСКИЙ АУДИТ ПРОЕКТА ARBITRAGE TERMINAL

**Дата аудита:** 2026-06-05  
**Цель:** Глубокий анализ перед системными исправлениями  
**Режим:** Demo/Paper только (Live trading disabled)

---

## 📊 КАРТА ПРОЕКТА

### Структура проекта (41 Python файлов)

```
ArbitTerminal/
├── main.py                 # 🚪 Entry point (demo_mode=True)
├── config.py               # ⚙️ Конфигурация (Telegram token УЖЕ ВЫНЕСЕН в .env)
├── env_loader.py           # 🔐 Загрузка .env
├── models.py               # 📦 Data models (MarketData, Trade, Position, ArbitragePair)
│
├── Core Trading Engine
│   ├── market_data_engine.py    # 📡 WebSocket aggregator (ИСПРАВЛЕН)
│   ├── arbitrage_engine.py      # 🔍 Spread calculator + parallel search
│   ├── trading_engine.py        # 💼 Order execution (demo + live)
│   ├── risk_manager.py          # 🛡️ Risk checks (balance, positions, limits)
│   ├── position_manager.py      # 📊 Position lifecycle
│   └── strategy_selector.py     # 🎯 Dynamic strategy selection
│
├── exchanges/               # 🏦 Exchange adapters (6 total)
│   ├── base.py             # Base class
│   ├── mexc.py             # ✅ Working (imports FIXED)
│   ├── gate.py             # ✅ Working (ping timeout FIXED)
│   ├── bybit.py            # ✅ Working (name FIXED)
│   ├── asterdex.py         # 🚧 Incomplete
│   ├── bitget.py           # 🚧 Incomplete
│   └── bingx.py            # 🚧 Incomplete
│
├── strategies/              # 📈 Closing strategies
│   ├── amplitude_strategy.py       # Fast scalping (0.7-2% spreads)
│   ├── balanced_strategy.py        # Hybrid (2-5%)
│   ├── spread_collapse_strategy.py # Large spreads (5%+)
│   └── momentum_reversal_strategy.py # Unused
│
├── utils/
│   └── telegram_logger.py  # 📱 Notifications
│
├── Tests (9 files, scattered)
│   ├── test_system.py         # ✅ Integration test (FIXED timestamp_ms)
│   ├── test_full_logging.py   # ✅ WebSocket test
│   ├── test_rest_api.py       # REST API check
│   ├── test_trading_api.py    # ⚠️ Makes REAL API calls
│   ├── test_exchanges.py      # Basic exchange test
│   └── test_*.py (others)     # Various tests
│
└── Docs (15+ markdown files)
    ├── README.md, STATUS.md, ROADMAP.md
    ├── P0_COMPLETE.md         # ✅ P0 fixes done
    ├── REFACTORING_PLAN.md    # 📋 Master plan
    └── Various hotfix docs
```

---

## 🎯 КЛЮЧЕВЫЕ КОМПОНЕНТЫ

### 1. Main Entry Point (`main.py`)
- **Архитектура:** AsyncIO + ThreadPoolExecutor (8 workers)
- **Режим:** `demo_mode=True` (симуляция торговли)
- **Lifecycle:**
  1. Initialize exchanges (WebSocket connect)
  2. Create engines (market_data, arbitrage, trading, risk, position)
  3. Subscribe to symbols (запускает start_websocket_listener на каждой бирже)
  4. Run monitoring loop (100ms intervals)
  5. Auto open/close positions

**✅ СТАТУС:** Работает корректно после P0 fixes

---

### 2. Market Data Pipeline

```
Exchange Adapter (start_websocket_listener)
   ↓ Reads WebSocket messages
   ↓ Updates self.orderbooks / self.funding_rates
   
MarketDataEngine (_listen_exchange)
   ↓ Polls orderbooks every 100ms
   ↓ Normalizes symbols
   ↓ Aggregates to self.market_data
   
ArbitrageEngine (find_opportunities_parallel)
   ↓ Calculates spreads (parallel, batched)
   ↓ Filters by threshold
   
RiskManager (check_opportunity)
   ↓ Validates position limits, balance, spreads
   
TradingEngine (execute_arbitrage)
   ↓ Opens LONG + SHORT positions
   
PositionManager (monitor_positions)
   ↓ Checks close conditions via StrategySelector
   ↓ Closes when conditions met
```

**✅ ИСПРАВЛЕНО (P0.6):** WebSocket lifecycle теперь корректный

---

### 3. Trading Logic

**Demo Mode (default):**
- Симулирует открытие/закрытие без реальных ордеров
- Трекает виртуальные позиции
- Считает PnL на основе market data

**Live Mode (DISABLED):**
- Требует API keys в .env
- Использует REST API для place_order/close_position
- ⚠️ НЕ ГОТОВ для продакшна (см. проблемы ниже)

---

## 🚨 КРИТИЧЕСКИЕ ПРОБЛЕМЫ

### P0: SECURITY & RUNTIME (✅ ИСПРАВЛЕНО)

#### ✅ P0.1: Telegram Token (FIXED)
- **Было:** Hardcoded в config.py
- **Стало:** Загружается из .env
- ⚠️ **ACTION REQUIRED:** Отозвать старый токен `7768319583:AAE...`

#### ✅ P0.2: MEXC Imports (FIXED)
- **Было:** `get_timestamp_ms`, `build_query_string`, `sign_request_hmac` не импортированы
- **Стало:** Добавлен import из `auth_utils`

#### ✅ P0.3: Bybit Naming (FIXED)
- **Было:** `super().__init__("Bybit")` (uppercase)
- **Стало:** `super().__init__("bybit")` (lowercase)

#### ✅ P0.4: WebSocket Reconnect (FIXED)
- **Было:** `reconnect_delay` не объявлен
- **Стало:** Exponential backoff 1s → 60s

#### ✅ P0.5: test_system.py (FIXED)
- **Было:** `market_data.timestamp_ms` (не существует)
- **Стало:** `market_data.timestamp.timestamp() * 1000`

#### ✅ P0.6: WebSocket Lifecycle (FIXED)
- **Было:** `start_websocket_listener()` не вызывался
- **Стало:** MarketDataEngine запускает listener на каждой бирже

---

### P1: АРХИТЕКТУРНЫЕ ПРОБЛЕМЫ (🔴 НЕ ИСПРАВЛЕНО)

#### 🔴 P1.1: Symbol Normalization
**ПРОБЛЕМА:** Символы в разных форматах по всей кодовой базе

**Форматы:**
- MEXC: `BTC_USDT` (underscore)
- Gate.io: `BTC_USDT` (underscore)
- Bybit: `BTCUSDT` (no separator)
- Internal: Mix of all (inconsistent)

**Где ломается:**
```python
# market_data_engine.py:136
normalized = data.symbol.replace("-", "").replace("_", "").replace("/", "").upper()

# Но exchanges возвращают разные форматы!
# MEXC: "BTC_USDT" → normalized "BTCUSDT" ✅
# Gate: "BTC_USDT" → normalized "BTCUSDT" ✅
# Bybit: "BTCUSDT" → normalized "BTCUSDT" ✅
# Но MarketData.symbol хранит оригинальный формат биржи!
```

**Последствия:**
- Arbitrage engine может не найти common symbols
- Position manager может дублировать позиции
- Логирование confusion

**РЕШЕНИЕ:**
1. Выбрать canonical: **BTCUSDT** (no separators, uppercase)
2. MarketData/Trade всегда хранят canonical
3. Exchange adapters конвертируют перед API вызовами
4. Создать `symbol_utils.py` (уже начато)

---

#### 🔴 P1.2: Order Side Mapping
**ПРОБЛЕМА:** TradingEngine передает `side='LONG'/'SHORT'`, но биржи ждут другие параметры

**Текущий код:**
```python
# trading_engine.py:43-46
await self.exchanges[opportunity.exchange_short].place_order(
    opportunity.symbol, 'SHORT', position_size
)
```

**Что делают exchanges:**
```python
# MEXC (mexc.py:179)
"side": 1 if side.lower() == "buy" else 2  # ❌ 'SHORT'.lower() != 'buy' → side=2 ✅
# Но это side для OPEN, не для CLOSE!

# Gate.io (gate.py:216)
"size": int(size) if side.lower() == "buy" else -int(size)
# ❌ 'SHORT' → negative size (correct for futures)

# Bybit (bybit.py:228)
"side": side.capitalize()  # ❌ 'SHORT'.capitalize() = 'Short' (неверный формат!)
# Bybit ждет: 'Buy' или 'Sell'
```

**КРИТИЧНО для LIVE:**
- MEXC: Может работать случайно (side=2 для short)
- Gate.io: Может работать (negative size = short)
- Bybit: **НЕ РАБОТАЕТ** ('Short' не валидный side)

**РЕШЕНИЕ:**
```python
# В каждом exchange adapter добавить:
def _map_order_params(self, side: str, is_close: bool):
    """
    LONG open = buy
    SHORT open = sell
    LONG close = sell + reduceOnly
    SHORT close = buy + reduceOnly
    """
    if side == 'LONG':
        return {
            'side': 'sell' if is_close else 'buy',
            'reduceOnly': is_close
        }
    else:  # SHORT
        return {
            'side': 'buy' if is_close else 'sell',
            'reduceOnly': is_close
        }
```

---

#### 🔴 P1.3: Position Sizing
**ПРОБЛЕМА:** `position_size` трактуется как USD, но биржи ждут qty/contracts

**Текущий код:**
```python
# trading_engine.py:44
await self.exchanges[...].place_order(symbol, 'SHORT', position_size)

# position_size = 100 USD
```

**Что получают exchanges:**
```python
# MEXC (mexc.py:182)
"vol": str(size)  # ❌ "100" как qty (не USD!)

# Gate.io (gate.py:216)
"size": int(size)  # ❌ 100 контрактов (не USD!)

# Bybit (bybit.py:232)
"qty": str(size)  # ❌ "100" qty (не USD!)
```

**Последствия LIVE:**
- Вместо $100 позиции открывается 100 контрактов
- При BTC $63,000 это $6,300,000 позиция! 💥
- Instant liquidation

**РЕШЕНИЕ:**
```python
def calculate_order_qty(symbol, position_size_usd, price, leverage=1):
    """
    Example:
    - position_size_usd = 100 USD
    - price = 63000 (BTC)
    - leverage = 10
    
    notional = 100 * 10 = 1000 USD
    qty = 1000 / 63000 = 0.0158 BTC
    """
    notional = position_size_usd * leverage
    qty = notional / price
    return round_to_precision(qty, symbol)
```

---

#### 🔴 P1.4: Unified PnL Calculation
**ПРОБЛЕМА:** PnL считается по-разному в 3 местах

**Места расчета:**
1. `position_manager.py:58-60` (простой)
2. `strategies/amplitude_strategy.py:51-58` (с leverage и fees)
3. `strategies/balanced_strategy.py:61-69` (без fees)
4. `strategies/spread_collapse_strategy.py:31-38` (простой)

**Различия:**
```python
# position_manager.py
pnl_long = (long_data.bid - trade.entry_price_long) / trade.entry_price_long * 100
pnl_short = (trade.entry_price_short - short_data.ask) / trade.entry_price_short * 100
pnl_pct = pnl_long + pnl_short
pnl_usd = pnl_pct * trade.position_size_usd / 100  # ❌ Нет leverage, нет fees!

# amplitude_strategy.py
leverage = getattr(trade, 'leverage', 10)
amplitude_usd = amplitude_pct * trade.position_size_usd * leverage / 100
fee_rate = 0.0005
total_fees = trade.position_size_usd * leverage * fee_rate * 4
amplitude_usd -= total_fees  # ✅ Есть leverage и fees
```

**Последствия:**
- Неточная статистика PnL
- Стратегии принимают решения на разных данных
- Position manager может закрывать слишком рано/поздно

**РЕШЕНИЕ:**
Создать `pnl_calculator.py`:
```python
def calculate_pnl(
    entry_long, entry_short,
    current_long, current_short,
    position_size_usd,
    leverage=1,
    fee_rate=0.0005
):
    # Gross PnL
    pnl_long_pct = (current_long - entry_long) / entry_long * 100
    pnl_short_pct = (entry_short - current_short) / entry_short * 100
    gross_pnl_pct = pnl_long_pct + pnl_short_pct
    
    # USD
    notional = position_size_usd * leverage
    gross_pnl_usd = gross_pnl_pct * notional / 100
    
    # Fees (4 operations: open long, open short, close long, close short)
    fees_usd = notional * fee_rate * 4
    
    # Net
    net_pnl_usd = gross_pnl_usd - fees_usd
    
    return {
        'pnl_long_pct': pnl_long_pct,
        'pnl_short_pct': pnl_short_pct,
        'gross_pnl_pct': gross_pnl_pct,
        'gross_pnl_usd': gross_pnl_usd,
        'fees_usd': fees_usd,
        'net_pnl_usd': net_pnl_usd
    }
```

---

#### 🔴 P1.5: Risk Manager — Position Tracking
**ПРОБЛЕМА:** `open_positions` — список символов, возможны дубли

**Текущая структура:**
```python
# risk_manager.py:26
self.open_positions = []  # List of symbols

# Регистрация (line 93):
self.open_positions.append(symbol)  # ❌ Может быть 2x "BTCUSDT"!

# Удаление (line 100):
if symbol in self.open_positions:
    self.open_positions.remove(symbol)  # ❌ Удаляет только первый!
```

**Сценарий дублирования:**
```
1. Open BTCUSDT: mexc↔gate (pair_id=abc)
2. Open BTCUSDT: mexc↔bybit (pair_id=def)
3. open_positions = ['BTCUSDT', 'BTCUSDT']
4. Close pair_id=abc
5. open_positions.remove('BTCUSDT') → ['BTCUSDT'] (удалил только 1!)
6. Check new BTCUSDT opportunity:
   len(open_positions) = 1 < MAX_OPEN_POSITIONS (3) → approved ✅
7. Но фактически уже 2 позиции BTCUSDT open!
```

**Последствия:**
- Неправильный подсчет позиций
- Violation MAX_OPEN_POSITIONS
- Violation MAX_POSITIONS_PER_EXCHANGE

**РЕШЕНИЕ:**
```python
# Изменить структуру:
self.open_positions = {}  # pair_id -> {'symbol', 'long_exchange', 'short_exchange'}

def register_position(self, pair_id, symbol, long_ex, short_ex):
    self.open_positions[pair_id] = {
        'symbol': symbol,
        'long_exchange': long_ex,
        'short_exchange': short_ex
    }
    # Update counters
    self.positions_per_exchange[long_ex] = ...
    self.positions_per_exchange[short_ex] = ...

def unregister_position(self, pair_id):
    if pair_id not in self.open_positions:
        return
    
    pos = self.open_positions[pair_id]
    del self.open_positions[pair_id]
    # Update counters
    ...

def get_position_count(self):
    return len(self.open_positions)  # По pair_id!

def get_symbol_positions(self, symbol):
    return [pid for pid, pos in self.open_positions.items() if pos['symbol'] == symbol]
```

---

### P2: КАЧЕСТВО КОДА (🟡 МОЖНО УЛУЧШИТЬ)

#### 🟡 P2.1: Logging
**ПРОБЛЕМА:** Смешаны print и logging, RAW MESSAGE в production

**Статистика:**
- `print()`: 371 вызовов в 24 файлах
- `logger.*`: Только в main.py и test_system.py
- RAW MESSAGE: В exchanges/*.py (строки 81-103)

**Текущее состояние:**
```python
# exchanges/gate.py:81
print(f"🔍 GATE RAW MESSAGE: {data}")  # ❌ В production!

# main.py:44
print(f"   📊 Баланс: {self.initial_balance} USD")  # ✅ CLI output OK

# trading_engine.py:77
print(f"   ❌ Ошибка открытия: {e}")  # ❌ Должен быть logger.error()
```

**РЕШЕНИЕ:**
1. Core modules (engines, managers) → `logging.getLogger(__name__)`
2. RAW MESSAGE → `logger.debug()` (по умолчанию OFF)
3. CLI output (main.py) → оставить `print()`
4. Не логировать секреты (API keys, signatures)

---

#### 🟡 P2.2: Tests
**ПРОБЛЕМА:** Тесты scattered, некоторые устарели, нет pytest

**Файлы:**
```
test_system.py          ✅ Integration test (working)
test_full_logging.py    ✅ WebSocket test (working)
test_rest_api.py        ⚠️ Делает HTTP запросы
test_trading_api.py     ⚠️ Делает REAL API calls (balance check)
test_exchanges.py       ✅ Basic check
test_all_exchanges.py   ✅ Loop test
test_api_simple.py      ✅ Simple check
check_imports.py        ✅ Import check
check_quick.py          ✅ Quick import check
```

**Проблемы:**
- Нет pytest structure (tests/ directory)
- Нет unit tests для core logic:
  - Symbol normalization
  - Order side mapping
  - Position sizing calculation
  - PnL calculation
  - Risk manager register/unregister
- test_trading_api.py может случайно сделать real trade (если API keys есть)
- Нет mocking для network calls

**РЕШЕНИЕ:**
```
tests/
├── unit/
│   ├── test_symbol_utils.py
│   ├── test_pnl_calculator.py
│   ├── test_risk_manager.py
│   └── test_order_mapping.py
├── integration/
│   ├── test_market_data_engine.py
│   ├── test_arbitrage_engine.py
│   └── test_trading_flow.py
└── conftest.py (pytest fixtures)

# Все network calls → mock
# Никаких real API calls в unit tests
```

---

#### 🟡 P2.3: ThreadPoolExecutor Cleanup
**ПРОБЛЕМА:** Executor создается но не shutdown'ится

**Код:**
```python
# main.py:74
self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)

# arbitrage_engine.py:16
self.executor = ThreadPoolExecutor(max_workers=max_workers)

# Нигде нет:
self.executor.shutdown(wait=True)
```

**Последствия:**
- Memory leak при множественных запусках
- Threads не cleanup'ятся
- Может вызвать "too many threads" error

**РЕШЕНИЕ:**
```python
# main.py
async def stop(self):
    """Graceful shutdown"""
    self.running = False
    await self.market_data_engine.stop()
    self.executor.shutdown(wait=True)  # ✅ Cleanup

# arbitrage_engine.py
def __del__(self):
    self.executor.shutdown(wait=False)  # ✅ Best effort cleanup
```

---

#### 🟡 P2.4: Duplicate Files
**ПРОБЛЕМА:** Дублирование models.py

**Файлы:**
```
models.py           ← Main (используется везде)
core/models.py      ← Дубликат (не используется)
```

**РЕШЕНИЕ:** Удалить `core/models.py` (или вынести общие части)

---

## 📋 ПРИОРИТИЗАЦИЯ ПРОБЛЕМ

### P0: КРИТИЧНО — SECURITY & RUNTIME ✅ ЗАВЕРШЕНО
- [x] P0.1: Telegram token → .env
- [x] P0.2: MEXC imports
- [x] P0.3: Bybit naming
- [x] P0.4: WebSocket reconnect
- [x] P0.5: test_system timestamp_ms
- [x] P0.6: WebSocket lifecycle

**Статус:** ✅ Все исправлено, система работает в demo режиме

---

### P1: БЛОКЕРЫ LIVE TRADING 🔴 ТРЕБУЕТ ИСПРАВЛЕНИЯ
- [ ] P1.1: Symbol normalization (средний приоритет)
- [ ] **P1.2: Order side mapping** 🚨 КРИТИЧНО для live
- [ ] **P1.3: Position sizing** 🚨 КРИТИЧНО для live (риск огромных позиций!)
- [ ] P1.4: Unified PnL (средний)
- [ ] P1.5: Risk manager pair_id (высокий)

**Блокируют:** Включение live trading  
**Риск:** 🔴 Финансовые потери, liquidation

---

### P2: КАЧЕСТВО КОДА 🟡 ЖЕЛАТЕЛЬНО
- [ ] P2.1: Logging cleanup
- [ ] P2.2: Pytest suite
- [ ] P2.3: ThreadPoolExecutor cleanup
- [ ] P2.4: Duplicate files

**Блокируют:** Maintainability, debugging  
**Риск:** 🟡 Технический долг

---

## 📝 ПЛАН ИСПРАВЛЕНИЙ

### ЭТАП 1: P1.2 + P1.3 (Order Side Mapping + Position Sizing) 🚨
**Приоритет:** КРИТИЧНО  
**Время:** 2-3 часа

**Шаги:**
1. Создать `order_utils.py`:
   - `map_order_side(side, is_close, exchange)` → биржевые параметры
   - `calculate_order_qty(symbol, position_size_usd, price, leverage)` → qty
2. Обновить exchanges/mexc.py, gate.py, bybit.py:
   - Использовать `map_order_side()`
   - Использовать `calculate_order_qty()`
3. Написать unit tests:
   - test_order_mapping.py
   - test_position_sizing.py
4. Ручной тест с demo_mode=False (без real orders!)

**Критерий завершения:** ✅ Все unit tests pass + manual verification

---

### ЭТАП 2: P1.1 (Symbol Normalization)
**Приоритет:** ВЫСОКИЙ  
**Время:** 1-2 часа

**Шаги:**
1. Завершить `symbol_utils.py` (уже начато)
2. Обновить BaseExchange:
   - `normalize_symbol(exchange_symbol)`
   - `to_exchange_symbol(canonical)`
3. Обновить MarketData/Trade:
   - Всегда хранить canonical symbol
4. Обновить все exchanges:
   - Конвертация перед API calls
5. Unit tests: test_symbol_normalization.py

**Критерий завершения:** ✅ Все symbols в canonical формате

---

### ЭТАП 3: P1.5 + P1.4 (Risk Manager + PnL)
**Приоритет:** ВЫСОКИЙ  
**Время:** 2 часа

**Шаги:**
1. Создать `pnl_calculator.py`:
   - `calculate_pnl()` с leverage и fees
2. Обновить position_manager.py, strategies/*:
   - Использовать единый PnL calculator
3. Обновить risk_manager.py:
   - `open_positions = {}` (dict, не list)
   - `register_position(pair_id, ...)`
   - `unregister_position(pair_id)`
4. Unit tests

**Критерий завершения:** ✅ No position duplicates + correct PnL

---

### ЭТАП 4: P2.1 (Logging Cleanup)
**Приоритет:** СРЕДНИЙ  
**Время:** 1 час

**Шаги:**
1. Заменить print → logging в core modules
2. RAW MESSAGE → logger.debug()
3. CLI output (main.py) → оставить print
4. Добавить log levels: INFO, WARNING, ERROR

---

### ЭТАП 5: P2.2 + P2.3 + P2.4 (Tests + Cleanup)
**Приоритет:** НИЗКИЙ  
**Время:** 2-3 часа

**Шаги:**
1. Создать pytest structure (tests/ directory)
2. Написать unit tests для всех core functions
3. Mock network calls
4. ThreadPoolExecutor shutdown
5. Удалить core/models.py

---

## 🎯 ГОТОВНОСТЬ К LIVE TRADING

### Текущий статус: 🔴 НЕ ГОТОВ

**Блокеры:**
1. 🚨 P1.2: Order side mapping (критично!)
2. 🚨 P1.3: Position sizing (критично!)
3. 🔴 P1.5: Risk manager duplicates

**После исправления P1.2 + P1.3:**
- ✅ Demo режим: Полностью готов
- 🟡 Live режим: Готов с ограничениями (малый капитал, manual supervision)

**Для полного produc

tion:**
- Завершить все P1
- Добавить comprehensive tests
- Testnet testing (если доступен)
- Phased rollout: $100 → $500 → $1000

---

## 📊 РЕЗЮМЕ

**Код база:** 41 Python файл, ~5000 строк  
**Архитектура:** AsyncIO + ThreadPool, modular design  
**Режим:** Demo ✅ | Live 🔴 (blocked by P1.2, P1.3)

**Сильные стороны:**
- ✅ Clean architecture (engines, strategies, adapters)
- ✅ Dynamic strategy selection
- ✅ Parallel arbitrage search (fast)
- ✅ Demo mode работает стабильно
- ✅ WebSocket pipeline исправлен

**Слабые стороны:**
- 🔴 Order side mapping broken (live risk!)
- 🔴 Position sizing broken (liquidation risk!)
- 🔴 Risk manager position duplicates
- 🟡 Symbol normalization inconsistent
- 🟡 PnL calculation varies
- 🟡 Heavy use of print() instead of logging
- 🟡 No comprehensive unit tests

**Рекомендация:**
1. ✅ Demo mode: Готов к использованию
2. 🔴 Live mode: Исправить P1.2 + P1.3 перед любыми real trades!
3. 📝 Следовать плану исправлений (5 этапов)
4. ✅ Постепенный rollout после тестов

---

**Аудитор:** AI Assistant  
**Дата:** 2026-06-05  
**Версия:** v1.0
