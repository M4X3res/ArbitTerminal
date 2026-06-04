# 🔧 TODO: Оставшиеся исправления

## ⚠️ Критично (требует немедленного внимания)

### 1. Повторная проверка спреда перед открытием ордера
**Где:** `main.py`, функция `run_arbitrage_monitoring`

**Проблема:** Между обнаружением возможности и реальным открытием ордера проходит время — спред может схлопнуться.

**Решение:**
```python
# В main.py перед execute_arbitrage:
# Повторная проверка спреда
long_data = market_data.get(opportunity.exchange_long, {}).get(opportunity.symbol)
short_data = market_data.get(opportunity.exchange_short, {}).get(opportunity.symbol)

if long_data and short_data:
    current_spread = (short_data.bid - long_data.ask) / long_data.ask * 100
    if current_spread < opportunity.spread * 0.9:  # Спред упал более чем на 10%
        print(f"⚠️ Спред схлопнулся: {opportunity.spread:.2f}% → {current_spread:.2f}%")
        continue
```

### 2. API ключи в .env должны быть удалены
**Где:** `.env` файл

**ВНИМАНИЕ:** Если файл `.env` был расшарен в Git или где-то ещё, **немедленно поменяйте API ключи на всех биржах!**

**Действия:**
1. Удалить `.env` из Git: `git rm --cached .env`
2. Добавить `.env` в `.gitignore`
3. Создать `.env.example` с шаблоном без ключей
4. Использовать secrets manager для продакшна

### 3. Исправить get_market_data() — архитектурная проблема
**Где:** `exchanges/gate.py`, `exchanges/mexc.py`

**Проблема:** Метод `get_market_data()` возвращает данные только когда есть и orderbook, и funding rate. Funding rate приходит значительно реже — метод «зависает» и возвращает данные только для одного символа.

**Решение:** Перейти на push-модель через очередь:
```python
# Вместо return в WebSocket listener
await self.data_queue.put(MarketData(...))

# В market_data_engine.py
async def get_next_update(self):
    return await self.data_queue.get()
```

---

## 🟡 Важно (повысит стабильность)

### 4. Rate-limit защита для REST API
**Где:** Все файлы в `exchanges/`

**Решение:**
```python
# В base.py или отдельный RateLimiter
self.rate_limiter = asyncio.Semaphore(10)  # 10 запросов одновременно

async def _request(self, ...):
    async with self.rate_limiter:
        # HTTP запрос
        if resp.status == 429:  # Too Many Requests
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
```

### 5. Логирование в файл
**Где:** `main.py`, добавить в начало

**Решение:**
```python
import logging
from logging.handlers import RotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        RotatingFileHandler('arbitrage.log', maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
```

### 6. Проверка минимального объёма ордера по биржам
**Где:** `risk_manager.py`, метод `check_opportunity`

**Решение:**
```python
EXCHANGE_MIN_ORDER = {
    'mexc': 5,
    'gate': 5,
    'bybit': 10,
    'asterdex': 10
}

# В check_opportunity:
min_long = EXCHANGE_MIN_ORDER.get(opportunity.exchange_long, 10)
min_short = EXCHANGE_MIN_ORDER.get(opportunity.exchange_short, 10)

if position_size < max(min_long, min_short):
    return {"approved": False, "reason": f"Position size below exchange minimum"}
```

---

## 🔵 Опционально (улучшения)

### 7. Унифицировать ThreadPoolExecutor
**Где:** `main.py`, `arbitrage_engine.py`

**Проблема:** Создаются три разных пула потоков.

**Решение:** Создать один `ThreadPoolExecutor` в `main.py` и передавать его во все компоненты.

### 8. Исправить тесты — PositionManager + StrategySelector
**Где:** `test_system.py`

**Проблема:** В тестах `PositionManager` создаётся с объектом стратегии, а не `StrategySelector`.

**Решение:** В `test_system.py`:
```python
from strategy_selector import StrategySelector
strategy_selector = StrategySelector()
position_manager = PositionManager(trading_engine, strategy_selector, telegram)
```

---

## 📊 Приоритет исправлений

| Пункт | Приоритет | Влияние | Сложность |
|-------|-----------|---------|-----------|
| 1. Повторная проверка спреда | 🔴 Критично | Предотвращает убыточные сделки | Низкая |
| 2. API ключи | 🔴 Критично | Безопасность | Низкая |
| 3. get_market_data() | 🔴 Критично | Исправляет зависание | Высокая |
| 4. Rate-limit | 🟡 Важно | Предотвращает баны | Средняя |
| 5. Логирование | 🟡 Важно | Отладка проблем | Низкая |
| 6. Минимальный объём | 🟡 Важно | Предотвращает отклонение ордеров | Низкая |
| 7. Унификация executor | 🔵 Опционально | Чистота кода | Средняя |
| 8. Тесты | 🔵 Опционально | Качество тестов | Низкая |

---

## ✅ Быстрые исправления (5 минут)

Можно исправить **прямо сейчас:**

1. **Повторная проверка спреда** — добавить 5 строк в `main.py`
2. **API ключи** — `git rm --cached .env` + добавить в `.gitignore`
3. **Логирование** — добавить 10 строк в начало `main.py`
4. **Минимальный объём** — добавить словарь и проверку в `risk_manager.py`

---

## 🚀 Готово к продакшну после:

- [x] Исправление 5 критических багов ✅
- [ ] Исправление 3 критичных TODO
- [ ] Добавление rate-limit защиты
- [ ] Настройка логирования
