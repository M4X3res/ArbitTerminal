# 🔍 АУДИТ ПРОЕКТА И РЕКОМЕНДАЦИИ

## ❌ КРИТИЧЕСКИЕ ОШИБКИ

### 1. **Funding Rate — неправильный расчёт стоимости**
**Файл:** `arbitrage_engine.py:26`

```python
# ❌ НЕПРАВИЛЬНО
funding_diff = short_data.funding_rate - long_data.funding_rate
effective = raw_spread - funding_diff * 100
```

**Проблема:**
- Funding rate обычно 0.0001 (0.01%)
- Умножение на 100 даёт 0.01, а это неправильно
- Funding начисляется каждые 8 часов, а не мгновенно

**Решение:**
```python
# ✅ ПРАВИЛЬНО
# Funding rate в час (если удерживаем позицию)
funding_rate_hourly = (short_data.funding_rate - long_data.funding_rate) / 8
# Учитываем только если планируем держать >1 часа
# Для краткосрочной торговли можно игнорировать
effective = raw_spread  # Funding игнорируем для trades <1 hour
```

---

### 2. **PnL расчёт без учёта leverage и комиссий**
**Файл:** `strategies/amplitude_strategy.py:38-44`

```python
# ❌ НЕПРАВИЛЬНО
pnl_long = (long_data.bid - trade.entry_price_long) / trade.entry_price_long * 100
amplitude_usd = amplitude_pct * trade.position_size_usd / 100
```

**Проблема:**
- Не учитывается leverage (10x)
- Не учитываются комиссии (0.02-0.05% × 2 стороны × 2 операции)
- Реальный PnL будет меньше на 0.08-0.2%

**Решение:**
```python
# ✅ ПРАВИЛЬНО
leverage = 10  # Из config
maker_fee = 0.0002  # 0.02%
taker_fee = 0.0005  # 0.05%

# PnL с учётом leverage
pnl_long_pct = (long_data.bid - trade.entry_price_long) / trade.entry_price_long * 100
pnl_short_pct = (trade.entry_price_short - short_data.ask) / trade.entry_price_short * 100

# Комиссии (вход + выход на обе стороны)
total_fees_pct = (maker_fee * 4) * 100  # 0.08% минимум

# Реальный PnL
net_pnl_pct = pnl_long_pct + pnl_short_pct - total_fees_pct
amplitude_usd = net_pnl_pct * trade.position_size_usd / 100
```

---

### 3. **Race condition в Position Manager**
**Файл:** `position_manager.py:32`

```python
# ❌ ПРОБЛЕМА
for pair_id, trade in list(self.positions.items()):
    should_close, reason = self.close_strategy.should_close(trade, market_data)
    if should_close:
        await self.close_position(pair_id, market_data, reason)
        # Позиция удаляется внутри close_position
        # Но если две проверки одновременно - race condition
```

**Решение:**
```python
# ✅ ПРАВИЛЬНО
import asyncio

async def monitor_positions(self, market_data):
    if not self.positions:
        return
    
    # Создаём задачи для всех позиций
    tasks = []
    for pair_id, trade in list(self.positions.items()):
        task = self._check_and_close_position(pair_id, trade, market_data)
        tasks.append(task)
    
    # Выполняем параллельно, но безопасно
    await asyncio.gather(*tasks, return_exceptions=True)

async def _check_and_close_position(self, pair_id, trade, market_data):
    # Проверяем что позиция всё ещё открыта
    if pair_id not in self.positions:
        return
    
    should_close, reason = self.close_strategy.should_close(trade, market_data)
    if should_close:
        await self.close_position(pair_id, market_data, reason)
```

---

## ⚠️ ЛОГИЧЕСКИЕ ПРОБЛЕМЫ

### 4. **Спред может исчезнуть за время открытия**
**Файл:** `main.py:124-135`

Между обнаружением спреда и открытием позиции проходит 50-200ms. За это время:
- Спред может схлопнуться
- Цены могут измениться
- Другой бот может перехватить возможность

**Решение:**
```python
# Проверить спред ещё раз перед открытием
current_spread = self._recalculate_spread(opp, market_data)
if current_spread < OPEN_THRESHOLD * 0.9:  # 10% буфер
    continue  # Пропустить, спред уже не тот
```

---

### 5. **Нет защиты от частичного исполнения**
**Файл:** `trading_engine.py:40-50`

```python
# ❌ ПРОБЛЕМА
success, pair_id = await self.trading_engine.execute_arbitrage(opp, position_size)
# Что если один ордер исполнился частично?
# Получаем несбалансированную позицию
```

**Решение:**
- Использовать `FOK` (Fill-Or-Kill) ордера
- Проверять реальный исполненный объём
- Балансировать позиции если объёмы не совпадают

---

### 6. **Баланс не обновляется после сделок**
**Файл:** `risk_manager.py:16`

```python
# ❌ ПРОБЛЕМА
self.balance = initial_balance  # Никогда не обновляется!
```

**Решение:**
```python
def update_balance(self, pnl: float):
    """Обновление баланса после закрытия позиции"""
    self.balance += pnl

# В position_manager.py после закрытия:
self.risk_manager.update_balance(trade.pnl)
```

---

## 🐛 МЕЛКИЕ БАГИ

### 7. **Неправильная проверка funding rate**
**Файл:** `risk_manager.py:47`

```python
if abs(opportunity.funding_diff) > 0.01:  # 1%
```

**Проблема:** Funding rate обычно 0.0001-0.0003 (0.01-0.03%), это слишком строго.

**Решение:**
```python
if abs(opportunity.funding_diff) > 0.001:  # 0.1% разница
```

---

### 8. **WebSocket может пропустить данные**
**Файл:** `market_data_engine.py:66-75`

Если очередь переполнена, данные просто пропускаются:
```python
try:
    self.data_queue.put_nowait(data)
except asyncio.QueueFull:
    pass  # ❌ Данные теряются!
```

**Решение:**
- Увеличить размер очереди
- Или использовать новые данные вместо старых (LIFO вместо FIFO)

---

### 9. **Нет проверки на минимальный объём ордера**
**Файл:** `risk_manager.py:52`

```python
if position_size < 10:  # Минимум 10 USD
```

**Проблема:** У бирж свои минимальные объёмы (например, Bybit: 10 USDT, Gate: 5 USDT).

**Решение:**
Добавить в config:
```python
MIN_ORDER_SIZE = {
    'mexc': 5,
    'gate': 5,
    'bybit': 10,
    'asterdex': 1
}
```

---

## 💡 УЛУЧШЕНИЯ ПРОИЗВОДИТЕЛЬНОСТИ

### 10. **Параллельный анализ может быть быстрее**
**Файл:** `arbitrage_engine.py:69-83`

Используется ThreadPoolExecutor, но можно ещё быстрее:

```python
# Вместо батчинга по 50 пар
# Использовать numpy для векторизации
import numpy as np

def find_opportunities_vectorized(self, market_data, threshold):
    # Векторизованные операции numpy в 10-100x быстрее
    # Для 200 пар: 10ms → 1ms
    pass
```

---

### 11. **Кэширование расчётов**
Много повторных расчётов spread для одних и тех же данных.

**Решение:**
```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def calculate_spread_cached(self, long_price, short_price, ...):
    # Кэшируем результаты расчётов
    pass
```

---

## 🛡️ БЕЗОПАСНОСТЬ

### 12. **API ключи в .env могут утечь**
**Файл:** `.env`

Если кто-то получит доступ к серверу, ключи доступны в plain text.

**Решение:**
- Шифрование .env файла
- Использовать AWS Secrets Manager / HashiCorp Vault
- Ограничить права на файл: `chmod 600 .env`

---

### 13. **Нет rate limiting для API**
Если система делает слишком много запросов, биржа заблокирует IP.

**Решение:**
```python
from asyncio import Semaphore

class ExchangeWithRateLimit:
    def __init__(self):
        self.semaphore = Semaphore(10)  # Макс 10 запросов одновременно
    
    async def request(self, ...):
        async with self.semaphore:
            await asyncio.sleep(0.1)  # 100ms между запросами
            return await self._do_request()
```

---

### 14. **Нет проверки на негативный баланс**
Система может открыть позицию даже если баланс уйдёт в минус.

**Решение:**
```python
if self.balance - position_size < 0:
    return {"approved": False, "reason": "Would result in negative balance"}
```

---

## 📊 МОНИТОРИНГ

### 15. **Нет логирования в файл**
Все логи только в консоль, при крэше теряются.

**Решение:**
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('arbitrage.log'),
        logging.StreamHandler()
    ]
)
```

---

### 16. **Нет метрик latency**
Невозможно понять насколько быстро система реагирует.

**Решение:**
```python
import time

start = time.time()
opportunities = await analyze()
latency = (time.time() - start) * 1000  # ms

if latency > 50:
    logger.warning(f"High latency: {latency}ms")
```

---

## 🎯 ИТОГОВЫЕ РЕКОМЕНДАЦИИ

### Критично исправить (перед live торговлей):
1. ✅ PnL расчёт с учётом комиссий
2. ✅ Баланс обновление после сделок
3. ✅ Защита от race conditions
4. ✅ Проверка минимальных объёмов бирж
5. ✅ Rate limiting для API

### Важно улучшить:
6. ⚠️ Funding rate расчёт (или убрать)
7. ⚠️ Повторная проверка спреда перед открытием
8. ⚠️ Логирование в файл
9. ⚠️ Мониторинг latency

### Опционально:
10. 💡 Векторизация numpy (5-10x быстрее)
11. 💡 Кэширование расчётов
12. 💡 Шифрование API ключей

---

## 📝 Оценка текущего состояния

| Компонент | Оценка | Замечания |
|-----------|--------|-----------|
| Архитектура | 9/10 | Отличная, async + parallel |
| WebSocket | 8/10 | Работает, но может терять данные |
| Анализ спредов | 7/10 | Быстро, но funding неправильно |
| Risk Management | 6/10 | Базовые проверки есть, но не хватает |
| PnL расчёт | 5/10 | ❌ Нет комиссий и leverage |
| Безопасность | 7/10 | Нужен rate limiting |
| Мониторинг | 6/10 | Нет файлового логирования |
| Документация | 10/10 | ✅ Отличная! |

**Общая оценка: 7.5/10** — хорошая система, но нужны исправления перед live торговлей.
