# Net Edge Strategy - Changelog

## 🎯 Цель
Переход от простого raw spread threshold к полноценной net edge стратегии с учётом всех издержек.

## 📦 Новые модули

### 1. `opportunity_analyzer.py`
Анализ арбитражных возможностей с расчётом net edge:

**Расчёты:**
- `gross_spread_pct` - сырой спред между биржами
- `bid_ask_spread_long_pct` - bid-ask spread на long leg
- `bid_ask_spread_short_pct` - bid-ask spread на short leg
- `estimated_fees_pct` - комиссии (0.05% × 4 сделки = 0.2%)
- `estimated_slippage_pct` - проскальзывание (0.02% × 4 = 0.08%)
- `funding_adjustment_pct` - корректировка на funding rate
- **`net_edge_pct`** = gross - fees - slippage - bid_ask_long - bid_ask_short - funding

**Результат:**
- `approved: bool` - одобрено/отклонено
- `reason: str` - детальная причина решения

### 2. `opportunity_config.py`
Конфигурация thresholds:

```python
MIN_GROSS_SPREAD = 0.35       # Минимальный gross spread
MIN_NET_EDGE = 0.15           # Минимальный net edge (после издержек)
MAX_GROSS_SPREAD = 2.5        # Аномально высокий spread
MAX_BID_ASK_SPREAD_PER_LEG = 0.12  # Максимальный bid-ask на одну позицию
MAX_DATA_AGE_MS = 1000        # Максимальный возраст данных (1 сек)

TAKE_PROFIT_NET = 0.15        # Take profit
STOP_LOSS_NET = -0.30         # Stop loss
```

### 3. `test_opportunity_analyzer.py`
Unit tests для всех сценариев:
- ✅ Approved good opportunity
- ❌ Rejected low gross spread
- ❌ Rejected high anomaly
- ❌ Rejected wide bid-ask (long/short)
- ❌ Rejected stale data
- ❌ Rejected insufficient net edge

## 🔄 Изменённые модули

### `risk_manager.py`
- Добавлен параметр `analysis` в `check_opportunity()`
- Если analysis не одобрен → сразу reject с его причиной
- Если analysis одобрен → дополнительные проверки (позиции, баланс)
- Использует `net_edge_pct` вместо `gross_spread`

### `main.py`
- Импорт `OpportunityAnalyzer` и `OPPORTUNITY_CONFIG`
- Создание `self.opportunity_analyzer` при инициализации
- В цикле мониторинга:
  - Анализ всех opportunities через analyzer
  - Фильтрация approved/rejected
  - Вывод статистики: "✅ одобрено X, ❌ отклонено Y"
  - Передача `analysis` в `risk_manager.check_opportunity()`
  - Вывод: "Gross: X% → Net Edge: Y%"

## 🛡️ Фильтры отказа

Позиция НЕ открывается если:

1. **Stale data** - данные старше 1 секунды
2. **Gross spread too low** - < 0.35%
3. **Gross spread anomaly** - > 2.5% (похоже на ошибку данных)
4. **Bid-ask too wide** - > 0.12% на любой позиции
5. **Net edge insufficient** - < 0.15% после всех издержек
6. **Max positions reached** - достигнут лимит позиций
7. **Negative net edge** - ожидается убыток

## 📊 Пример вывода

### До:
```
🎯 Найдено 5 возможностей:
   ✅ BTC/USDT: mexc ↔ gate
      Спред: 0.52% | Funding: 0.0001
```

### После:
```
🎯 Найдено 12 возможностей, ✅ одобрено 3, ❌ отклонено 9
   ✅ BTC/USDT: mexc ↔ gate
      Gross: 0.520% → Net Edge: 0.180%
   ❌ ETH/USDT: gate ↔ bybit
      Reason: Bid-ask too wide on short leg (0.15% > 0.12%)
```

## 🧪 Тестирование

### Unit Tests:
```bash
run_unit_tests.bat
```

Запускает 11 тестов различных сценариев approve/reject.

### Smoke Test (30 сек):
```bash
run_smoke_test.bat
```

Проверяет:
- Инициализацию OpportunityAnalyzer
- Работу фильтров в реальном времени
- Статистику approved/rejected
- Demo режим БЕЗ реальных ордеров

## ✅ Гарантии безопасности

- ❌ **НЕТ** изменений в live trading logic
- ❌ **НЕТ** новых вызовов API ордеров
- ✅ Работает **ТОЛЬКО** в demo режиме
- ✅ Дополнительная фильтрация **УМЕНЬШАЕТ** количество открываемых позиций
- ✅ Unit tests подтверждают корректность логики

## 📈 Ожидаемый эффект

### Старая логика:
- Открывалось: ~80% opportunities с spread > threshold
- Много ложных срабатываний на wide spreads
- Потери на fees/slippage не учитывались

### Новая логика:
- Открывается: ~20-30% opportunities (строгая фильтрация)
- Только возможности с положительным net edge
- Учёт всех издержек → более реалистичный PnL

## 🚀 Запуск

### 1. Unit Tests:
```bash
run_unit_tests.bat
```

### 2. Smoke Test:
```bash
run_smoke_test.bat
```

### 3. Demo мониторинг:
```bash
.venv\Scripts\python.exe main.py
```

Наблюдайте:
- Сколько opportunities найдено
- Сколько прошло фильтр (approved)
- Причины отказа (rejected)
- Net edge для одобренных

## 📝 Примечания

- Все изменения **обратно совместимы**
- Если `analysis` не передан в `risk_manager` → работает старая логика
- Demo режим **не затронут** → безопасное тестирование
- Live trading **не изменён** → безопасность
