# 📁 Структура проекта

```
ArbitTerminal/
│
├── 📄 main.py                      # Главный файл запуска
├── 📄 config.py                    # Основная конфигурация
├── 📄 performance_config.py        # Настройки производительности
├── 📄 env_loader.py                # Загрузка .env файла
├── 📄 requirements.txt             # Зависимости Python
├── 📄 .env.example                 # Шаблон .env
├── 📄 .env                         # API ключи (не в git!)
├── 📄 .gitignore                   # Git ignore
├── 📄 README.md                    # Документация проекта
├── 📄 STATUS.md                    # Текущий статус
├── 📄 ROADMAP.md                   # Дорожная карта
│
├── 📂 exchanges/                   # Коннекторы бирж
│   ├── base.py                     # Базовый класс
│   ├── auth_utils.py               # Утилиты авторизации
│   ├── mexc.py                     # MEXC
│   ├── gate.py                     # Gate.io
│   ├── bybit.py                    # Bybit
│   ├── asterdex.py                 # AsterDEX
│   ├── bingx.py                    # BingX (опционально)
│   ├── bitget.py                   # Bitget (опционально)
│   └── __init__.py
│
├── 📂 strategies/                  # Торговые стратегии
│   ├── amplitude_strategy.py      # Скальпинг (0.5%+)
│   ├── spread_collapse_strategy.py # Большие спреды (5%+)
│   └── __init__.py
│
├── 📂 utils/                       # Утилиты
│   ├── telegram_logger.py         # Telegram уведомления
│   └── __init__.py
│
├── 📂 docs/                        # Документация
│   ├── AMPLITUDE_STRATEGY.md      # Детали amplitude
│   ├── STRATEGY_COMPARISON.md     # Сравнение стратегий
│   ├── QUICK_START.md             # Быстрый старт
│   ├── TELEGRAM_SETUP.md          # Настройка Telegram
│   ├── LIVE_TRADING.md            # Переход на live
│   ├── TESTING.md                 # Тестирование
│   ├── PERFORMANCE.md             # Оптимизация
│   └── CHECKLIST.md               # Чек-лист проверки
│
├── 📂 core/                        # Основные модули
│   ├── models.py                   # Модели данных
│   ├── market_data_engine.py      # Сбор данных
│   ├── arbitrage_engine.py        # Поиск возможностей
│   ├── trading_engine.py          # Торговля
│   ├── risk_manager.py            # Риск-менеджмент
│   └── position_manager.py        # Управление позициями
│
└── 📂 tests/                       # Тесты
    └── test_system.py              # Проверка системы
```

---

## Основные файлы

### Запуск
- **main.py** — главный файл, запускает систему
- **test_system.py** — проверка всех компонентов

### Конфигурация
- **.env** — API ключи (секретно!)
- **config.py** — торговые параметры
- **performance_config.py** — настройки производительности

### Core модули
- **market_data_engine.py** — WebSocket данные с бирж
- **arbitrage_engine.py** — поиск арбитражных возможностей
- **trading_engine.py** — открытие/закрытие позиций
- **risk_manager.py** — управление рисками
- **position_manager.py** — автоматическое закрытие

### Стратегии
- **amplitude_strategy.py** — скальпинг микроколебаний
- **spread_collapse_strategy.py** — схлопывание больших спредов

### Биржи
4 основных коннектора:
- MEXC
- Gate.io
- Bybit
- AsterDEX

2 опциональных:
- BingX
- Bitget

---

## Команды

### Установка
```bash
pip install -r requirements.txt
```

### Проверка
```bash
python test_system.py
```

### Запуск
```bash
# Demo режим
python main.py

# Live торговля (после настройки)
# Измените USE_LIVE_TRADING = True в main.py
python main.py
```

---

## Размер проекта

- Основной код: ~2500 строк
- Документация: ~4000 строк
- Всего файлов: 30+
- Языки: Python 3.9+
- Зависимости: 4 пакета
