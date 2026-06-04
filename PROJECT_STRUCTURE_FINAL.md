# ✅ СТРУКТУРА ПРОЕКТА (ФИНАЛЬНАЯ)

```
ArbitTerminal/
│
├── main.py                         # ← ГЛАВНЫЙ ФАЙЛ ЗАПУСКА
│
├── config.py                       # Основная конфигурация
├── performance_config.py           # Настройки производительности
├── .env                            # API ключи (секретно!)
├── .env.example                    # Шаблон .env
├── requirements.txt                # Зависимости
├── .gitignore                      # Git ignore
│
├── models.py                       # Модели данных
├── market_data_engine.py           # Сбор данных с бирж
├── arbitrage_engine.py             # Поиск возможностей
├── trading_engine.py               # Торговля
├── risk_manager.py                 # Риск-менеджмент
├── position_manager.py             # Управление позициями
├── env_loader.py                   # Загрузка .env
│
├── exchanges/                      # Коннекторы бирж
│   ├── __init__.py
│   ├── base.py
│   ├── auth_utils.py
│   ├── mexc.py
│   ├── gate.py
│   ├── bybit.py
│   └── asterdex.py
│
├── strategies/                     # Торговые стратегии
│   ├── __init__.py
│   ├── amplitude_strategy.py
│   └── spread_collapse_strategy.py
│
├── utils/                          # Утилиты
│   ├── __init__.py
│   └── telegram_logger.py
│
├── docs/                           # Документация
│   ├── AMPLITUDE_STRATEGY.md
│   ├── STRATEGY_COMPARISON.md
│   ├── QUICK_START.md
│   ├── TELEGRAM_SETUP.md
│   ├── LIVE_TRADING.md
│   ├── TESTING.md
│   ├── PERFORMANCE.md
│   └── CHECKLIST.md
│
├── test_system.py                  # Тесты системы
│
├── README.md                       # Документация
├── STATUS.md                       # Статус проекта
├── PROJECT_STRUCTURE.md            # Этот файл
└── CLEANUP.md                      # Инструкции по очистке
```

## Команды

```bash
# Запуск
python main.py

# Тесты
python test_system.py

# Установка
pip install -r requirements.txt
```

## Важно!

Папка `core/` НЕ используется - все модули в корне проекта.

Если есть папка `core/` - удалите её:
```bash
rmdir /s core  # Windows
rm -rf core/   # Linux/Mac
```
