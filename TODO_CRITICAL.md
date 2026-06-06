# КРИТИЧЕСКИЕ ЗАДАЧИ ПЕРЕД LIVE-TRADING

## Статус: 🔴 БЛОКИРУЕТ LIVE-TRADING

На основе анализа `prompt/AGENT_PROMPT.md` выявлены критические баги, которые могут привести к потере средств.

---

## ПРИОРИТЕТ 1 — БЛОКЕРЫ (может привести к ликвидации)

### ✅ ИСПРАВЛЕНО
- [x] БАГ: `trade.timestamp` → `trade.open_time` в `rest_optimized_strategy.py`
- [x] Обработка ошибок в `monitor_positions()`
- [x] Аварийное закрытие позиций при остановке

### 🔴 КРИТИЧНО — ТРЕБУЕТ ИСПРАВЛЕНИЯ

#### БАГ #1 — Position Sizing
**Файлы:** `exchanges/mexc.py`, `gate.py`, `bybit.py`, `trading_engine.py`
**Риск:** При передаче `size=100` USD биржа может открыть 100 контрактов = $6,300,000 для BTC

**Действие:**
1. Создать `order_utils.py` с функцией `calculate_order_qty()`
2. Обновить все `place_order()` в exchange-адаптерах
3. Добавить unit-тест

#### БАГ #2 — Order Side Mapping
**Файлы:** `exchanges/bybit.py`, `mexc.py`, `gate.py`
**Риск:** `'LONG'.capitalize()` = `'Long'` — невалидно для Bybit (ждёт `'Buy'`)

**Действие:**
1. Добавить `SIDE_MAP` в `order_utils.py`
2. Функция `map_order_side(exchange, side, is_close)`
3. Обновить все `place_order()` и `close_position()`

#### БАГ #3 — Risk Manager дублирование
**Файл:** `risk_manager.py`
**Риск:** Счётчик позиций ломается при закрытии → может открыть больше MAX_OPEN_POSITIONS

**Действие:**
1. Заменить `self.open_positions = []` на `dict` с ключом `pair_id`
2. Обновить `register_position()` и `unregister_position()`
3. Обновить все вызовы в `main.py` и `position_manager.py`

#### БАГ #4 — PnL несогласованность
**Файлы:** `position_manager.py`, все стратегии
**Риск:** Закрытие по неверному порогу → преждевременное/запоздалое закрытие

**Действие:**
1. Создать `pnl_calculator.py` с `calculate_net_pnl()`
2. Учесть leverage, комиссии (4 операции), slippage
3. Заменить все расчёты PnL на единую функцию

#### БАГ #5 — Symbol Normalization
**Файлы:** `market_data_engine.py`, `arbitrage_engine.py`, все exchanges
**Риск:** `common_symbols` пустой из-за несовпадения форматов → нет сделок

**Действие:**
1. Использовать существующий `symbol_utils.py`
2. Добавить `to_canonical()` и `to_local()` в `BaseExchange`
3. Нормализовать везде к единому формату `BTCUSDT`

---

## ПРИОРИТЕТ 2 — ВАЖНО (логические ошибки)

### ОШИБКА #1 — MarketDataEngine двойной polling
**Файл:** `market_data_engine.py`
**Проблема:** `_listen_exchange()` вызывает `get_market_data()` в цикле, но WebSocket уже обновляет `orderbooks`

**Действие:** Убрать `exchange.get_market_data(symbol)` из цикла, читать `exchange.orderbooks` напрямую

### ОШИБКА #2 — Несогласованные пороги
**Файлы:** `config.py` (OPEN_THRESHOLD=1.0), `opportunity_config.py` (MIN_GROSS_SPREAD=0.35)

**Действие:** Синхронизировать значения, один источник правды

### ОШИБКА #3 — RestOptimizedStrategy импорт
**Файл:** `strategy_selector.py`
**Проблема:** Импорт несуществующего файла

**Действие:** ✅ УЖЕ СОЗДАН файл `rest_optimized_strategy.py`

---

## ПРИОРИТЕТ 3 — УЛУЧШЕНИЯ (перед масштабированием)

- [ ] Единый `settings.py` вместо 3 конфиг-файлов
- [ ] Structured logging вместо `print()`
- [ ] Health check endpoint `/health`
- [ ] Backtesting модуль
- [ ] Unit-тесты для критических функций

---

## ПОРЯДОК ВЫПОЛНЕНИЯ

### Этап 0 (10 мин) — Безопасность
- [ ] Проверить `.env` не в git
- [ ] Telegram token актуальный

### Этап 1 (3-4 часа) — Критические баги
1. [x] Создать `order_utils.py` (БАГ #1 + #2)
2. [x] Создать `pnl_calculator.py` (БАГ #4)
3. [x] Исправить `risk_manager.py` (БАГ #3)
4. [x] Подключить `symbol_utils.py` везде (БАГ #5)
5. [x] Написать unit-тесты для #1-4
6. [ ] Запустить тесты — все зелёные

**ЭТАП 1 ЗАВЕРШЁН — критические баги исправлены!**

---

### Этап 2 (1-2 часа) — Логические ошибки
1. [ ] Исправить `market_data_engine.py` (ОШИБКА #1)
2. [ ] Синхронизировать пороги (ОШИБКА #2)
3. [ ] Добавить `executor.shutdown()` в `arbitrage_engine.py`

### Этап 3 (2-3 часа) — Улучшения
1. [ ] Объединить конфиги в `settings.py`
2. [ ] Заменить `print()` на `logger.*`
3. [ ] Health check endpoint
4. [ ] Базовый backtester

### Этап 4 — Тестирование
1. [ ] `python test_system.py` — полный pass
2. [ ] Demo 30+ минут без ошибок
3. [ ] Только после этого → live с $100 max

---

## КРИТЕРИИ ГОТОВНОСТИ К LIVE

- [ ] `pytest tests/` — 100% pass
- [ ] `calculate_order_qty('BTCUSDT', 100, 63000, 5)` → 0.00793, НЕ 100
- [ ] `map_order_side('bybit', 'LONG', False)` → `'Buy'`
- [ ] Demo работает 30+ минут без ошибок
- [ ] IP whitelist на биржах
- [ ] Вывод средств отключён в API
- [ ] Начальный капитал ≤ $100

---

## ⚠️ ВАЖНО

**НЕ ВКЛЮЧАТЬ `USE_LIVE_TRADING = True` ДО ЗАВЕРШЕНИЯ ЭТАПА 1**

Текущие баги могут привести к:
- Открытию гигантских позиций (БАГ #1)
- Отклонению всех ордеров (БАГ #2)
- Нарушению лимитов позиций (БАГ #3)
- Неверным сигналам закрытия (БАГ #4)
- Отсутствию сделок из-за пустых `common_symbols` (БАГ #5)
