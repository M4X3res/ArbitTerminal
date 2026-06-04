# 🔧 ПЛАН ГЛУБОКОЙ ДОРАБОТКИ ARBITRAGE TERMINAL

## ✅ P0: КРИТИЧНЫЕ ИСПРАВЛЕНИЯ (SECURITY & RUNTIME)

### P0.1: Security — Telegram Credentials ✅ DONE
- [x] Удалить hardcoded токены из config.py
- [x] Добавить get_telegram_config() в env_loader.py
- [x] main.py загружает из .env
- [ ] **ACTION REQUIRED**: Отозвать старый токен и создать новый

### P0.2: MEXC Missing Imports ✅ DONE
- [x] Добавить импорты auth_utils в mexc.py

### P0.3: Bybit Naming ✅ DONE
- [x] Исправить "Bybit" → "bybit" (lowercase)

### P0.4: WebSocket Reconnect ✅ DONE
- [x] Объявить reconnect_delay variables

### P0.5: test_system.py timestamp_ms ✅ DONE
- [x] Исправить timestamp.timestamp() * 1000

### P0.6: WebSocket Lifecycle 🔄 IN PROGRESS
**ПРОБЛЕМА**: Exchange adapters имеют `start_websocket_listener()`, но он не вызывается!
- MarketDataEngine вызывает только `subscribe_orderbook/subscribe_funding_rate`
- Потом poll'ит локальные данные через `_listen_exchange()`
- Но WebSocket messages никто не читает в фоне!

**РЕШЕНИЕ**:
1. В `_subscribe_exchange()` вызвать `exchange.start_websocket_listener(symbols)` один раз
2. Удалить или упростить `_listen_exchange()` — просто poll'ить готовые данные
3. Каждый adapter сам читает свой WebSocket и заполняет orderbooks/funding_rates

---

## 🔧 P1: АРХИТЕКТУРНЫЕ ИСПРАВЛЕНИЯ

### P1.1: Symbol Normalization
**ПРОБЛЕМА**: Символы в разных форматах: BTCUSDT, BTC/USDT, BTC_USDT

**РЕШЕНИЕ**:
1. Выбрать canonical format: **BTCUSDT** (без разделителей, uppercase)
2. Добавить в BaseExchange:
   - `normalize_symbol(exchange_symbol) -> canonical`
   - `to_exchange_symbol(canonical) -> биржевой формат`
3. MarketData/Trade всегда хранят canonical
4. Exchange adapters конвертируют перед API вызовами

### P1.2: Order Side Mapping
**ПРОБЛЕМА**: trading_engine передает 'LONG'/'SHORT', но биржи ждут buy/sell/reduce_only

**РЕШЕНИЕ**:
1. Добавить в каждый exchange adapter:
   ```python
   def _map_order_params(self, side: str, is_close: bool):
       if side == 'LONG':
           return {'side': 'sell' if is_close else 'buy', 'reduceOnly': is_close}
       else:  # SHORT
           return {'side': 'buy' if is_close else 'sell', 'reduceOnly': is_close}
   ```
2. place_order/close_position используют этот mapping

### P1.3: Position Sizing
**ПРОБЛЕМА**: position_size_usd отправляется как qty напрямую

**РЕШЕНИЕ**:
1. Добавить helper:
   ```python
   def calculate_order_qty(symbol, position_size_usd, price, leverage):
       notional = position_size_usd * leverage
       qty = notional / price
       return round_to_precision(qty, symbol)
   ```
2. place_order использует это перед отправкой

### P1.4: Unified PnL Calculation
**ПРОБЛЕМА**: PnL считается по-разному в разных местах

**РЕШЕНИЕ**:
1. Создать `pnl_calculator.py`:
   ```python
   def calculate_pnl(trade, current_long_price, current_short_price, fees_pct, leverage):
       # Unified calculation
       pnl_long_pct = ...
       pnl_short_pct = ...
       gross_pnl = ...
       fees = position_size * fees_pct * 2  # open + close
       net_pnl = gross_pnl - fees
       return net_pnl
   ```
2. Все стратегии и PositionManager используют это

### P1.5: Risk Manager — Tracking by pair_id
**ПРОБЛЕМА**: open_positions хранит только символы, возможны дубли

**РЕШЕНИЕ**:
1. Изменить структуру:
   ```python
   self.open_positions = {}  # pair_id -> {'symbol', 'long_exchange', 'short_exchange'}
   ```
2. register_position(pair_id, symbol, exchanges)
3. unregister_position(pair_id)
4. Корректный подсчет по биржам и символам

---

## 📝 P2: КАЧЕСТВО КОДА

### P2.1: Logging Cleanup
- Заменить print на logging в core modules
- RAW MESSAGE → logger.debug()
- Не логировать секреты
- CLI output в main.py остается print

### P2.2: Pytest Suite
Добавить тесты:
- `test_symbol_normalization.py`
- `test_order_mapping.py`
- `test_position_sizing.py`
- `test_pnl_calculation.py`
- `test_risk_manager.py`
- `test_market_data_engine.py`

Мок network calls, без реальных ордеров.

### P2.3: Documentation
- README.md — честное описание (demo ready, live pending)
- ARCHITECTURE.md — объяснение WebSocket lifecycle
- SAFETY.md — чек-лист перед live trading

### P2.4: Cleanup
- Удалить неиспользуемый ThreadPoolExecutor в main.py или использовать
- ArbitrageEngine executor shutdown
- Вынести test_*.py → tests/ директория
- Добавить .gitignore для .env

---

## 🎯 ПРИОРИТЕТ ВЫПОЛНЕНИЯ

1. **P0.6** — WebSocket lifecycle (критично для работы!)
2. **P1.1** — Symbol normalization (перед тестами)
3. **P1.2** — Order side mapping (перед live)
4. **P1.3** — Position sizing (перед live)
5. **P1.4** — Unified PnL
6. **P1.5** — Risk manager pair_id
7. **P2.1-P2.4** — Качество и тесты

---

## ⚠️ ОГРАНИЧЕНИЯ

- НЕ включать USE_LIVE_TRADING=True
- НЕ делать реальные ордера в тестах
- Все изменения — маленькими шагами
- После каждого шага — проверка работоспособности

---

## 📊 ТЕКУЩИЙ СТАТУС

✅ P0.1-P0.5: Завершено
🔄 P0.6: В процессе
⏳ P1.1-P1.5: Ожидает
⏳ P2.1-P2.4: Ожидает
