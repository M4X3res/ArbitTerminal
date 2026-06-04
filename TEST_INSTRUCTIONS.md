# Инструкция по тестированию коннекторов

## Шаг 1: Активировать виртуальное окружение

### Windows (PowerShell):
```powershell
.venv\Scripts\Activate.ps1
```

### Windows (CMD):
```cmd
.venv\Scripts\activate.bat
```

## Шаг 2: Установить зависимости (если еще не установлены)
```bash
pip install aiohttp websockets
```

## Шаг 3: Проверить импорты
```bash
python check_imports.py
```

Должно вывести:
```
🔧 Проверка импортов...
✅ MEXC импортирован
✅ Gate импортирован
✅ Models импортированы

✅ Все импорты прошли успешно!
```

## Шаг 4: Запустить полное тестирование
```bash
python test_exchanges.py
```

Тест выполнит:
1. Подключение к MEXC WebSocket
2. Получение списка инструментов
3. Подписка на 3 символа
4. Получение market data в течение 10 секунд
5. То же самое для Gate.io

## Ожидаемый результат:

```
============================================================
🧪 Exchange Connectors Test Suite
============================================================

🔧 Testing MEXC Exchange...
✅ MEXC WebSocket connected
✅ Found 150 instruments
   First 5: ['BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT']
✅ MEXC subscribed to 3 symbols
📊 Listening for market data (10 seconds)...
   BTC_USDT: Bid=65000.0, Ask=65001.0, FR=0.0001
   ETH_USDT: Bid=3200.0, Ask=3201.0, FR=0.0001
   ...

🔧 Testing Gate.io Exchange...
✅ Gate.io WebSocket connected
✅ Found 200 instruments
   First 5: ['BTC_USDT', 'ETH_USDT', 'BNB_USDT', 'SOL_USDT', 'XRP_USDT']
✅ Gate.io subscribed to 3 symbols
📊 Listening for market data (10 seconds)...
   BTC_USDT: Bid=65000.0, Ask=65001.0, FR=0.0001
   ...

============================================================
✅ Tests completed
```

## Альтернативный запуск (через batch-файл):
```cmd
run_tests.bat
```

## Возможные ошибки:

### 1. ModuleNotFoundError
```
Решение: pip install aiohttp websockets
```

### 2. Connection timeout
```
Причина: Проблемы с интернетом или блокировка бирж
Решение: Проверить подключение, использовать VPN
```

### 3. WebSocket error
```
Причина: Неверный формат сообщений
Решение: Проверить логи, обновить код коннектора
```

## Быстрая проверка через PyCharm:

1. Открыть `test_exchanges.py`
2. Нажать ПКМ → Run 'test_exchanges'
3. Или нажать Shift+F10

## Для разработки:

Запустить только один коннектор:
```python
import asyncio
from exchanges.mexc import MEXCExchange

async def test():
    exchange = MEXCExchange()
    await exchange.connect_ws()
    instruments = await exchange.get_instruments()
    print(f"Instruments: {len(instruments)}")

asyncio.run(test())
```
