"""Главная конфигурация арбитражной системы"""

# Биржи (3 working exchanges)
EXCHANGES = ['mexc', 'gate', 'bybit']

# === ЧЕРНЫЙ СПИСОК СИМВОЛОВ ===
# Тикеры с аномальными данными (рыночные коллизии, делистинги, сплиты)
# Полностью исключаются из обработки на уровне WebSocket-агрегатора
BLACKLISTED_SYMBOLS = [
    "EDGEUSDT",  # Аномалия: Gate=0.06532, Bybit=0.4655 (7.13x разница)
]

# === СТРАТЕГИЯ ОТКРЫТИЯ (REST-оптимизировано) ===
# Для REST торговли требуются более высокие спреды
# из-за задержек исполнения (100-300ms на 2 ордера)

OPEN_THRESHOLD = 1.0  # Минимальный спред для открытия
MAX_SPREAD_OPEN = 3.0  # Максимальный спред (выше — вероятно ловушка)
MIN_NET_EDGE = 0.3     # Минимальная чистая прибыль после всех издержек

# Aggressive mode (использовать с осторожностью!)
AGGRESSIVE_MODE = False
AGGRESSIVE_MAX_SPREAD = 5.0  # Если True, макс спред 5% вместо 3%

# === СТРАТЕГИЯ ЗАКРЫТИЯ (REST-оптимизировано) ===
STRATEGY_TYPE = 'rest_optimized'  # 'amplitude', 'collapse', или 'rest_optimized'

# REST Optimized Strategy (рекомендуется для REST торговли)
REST_TAKE_PROFIT_PCT = 0.4    # Фиксированный TP: 0.4% (с 5x = 2% ROI)
REST_STOP_LOSS_PCT = 0.5      # Фиксированный SL: 0.5% (с 5x = 2.5% убыток от margin)
REST_MAX_HOLD_TIME = 180      # 3 минуты максимум
REST_TRAILING_ACTIVATION = 0.5  # Трейлинг после 0.5% прибыли
# Amplitude Strategy
AMPLITUDE_WINDOW = 50
AMPLITUDE_THRESHOLD = 0.7
MIN_AMPLITUDE_USD = 5.0
STOP_LOSS_MULTIPLIER = 2.0
MAX_HOLD_TIME_SEC = 300  # 5 минут

# Collapse Strategy
COLLAPSE_THRESHOLD = 0.1     # Спред схлопнулся до 0.1%
MIN_PROFIT_PCT = 0.05        # Минимальная прибыль 0.05%
MAX_HOLD_TIME_COLLAPSE = 3600  # 1 час

# === РИСК-МЕНЕДЖМЕНТ ===
POSITION_SIZE_FRACTION = 0.1    # 10% от баланса на позицию
MAX_OPEN_POSITIONS = 3          # Максимум 3 позиции одновременно
MAX_POSITIONS_PER_EXCHANGE = 3  # Максимум 3 позиции на одной бирже
MAX_LEVERAGE = 5                # Плечо 5x (было 10x - снижено для безопасности)
                                # При 10x: риск ликвидации -10%, прибыль выше в 2 раза

# БАГ ОШИБКА #4 FIX: Защита от двойных позиций по одному символу
ALLOW_MULTIPLE_POSITIONS_PER_SYMBOL = False  # Запрещаем несколько позиций по одному символу

# УЛУЧШЕНИЕ #2: Cooldown после убыточной сделки
COOLDOWN_AFTER_LOSS_SEC = 300  # 5 минут
                                # При 5x: риск ликвидации -20%, баланс риск/прибыль ✅
MIN_LIQUIDITY_MULTIPLIER = 1.5

# === HIGH-SPREAD STRATEGY ===
HIGH_SPREAD_MODE        = True   # Включить / выключить
HIGH_SPREAD_MIN_PCT     = 4.0    # Минимальный спред для этой стратегии
HIGH_SPREAD_MAX_HOLD    = 90     # Минут (жёсткий лимит)
HIGH_SPREAD_LEVERAGE    = 3      # Меньше плеча — рынки тонкие
HIGH_SPREAD_POS_FRAC    = 0.06   # 6% от баланса на позицию
HIGH_SPREAD_MAX_POS     = 3      # Максимум позиций одновременно

# === TELEGRAM УВЕДОМЛЕНИЯ ===
# ⚠️ ВАЖНО: Токен и chat_id должны быть в .env файле!
# Получите ваш chat_id через @userinfobot в Telegram
# Пример .env:
#   TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
#   TELEGRAM_CHAT_ID=123456789
TELEGRAM_BOT_TOKEN = None  # Читается из .env
TELEGRAM_CHAT_ID = None    # Читается из .env

# Устаревшие (для совместимости)
MAX_POSITION_SIZE = 1000
PROFIT_THRESHOLD_K = 0.8
CLOSE_THRESHOLD = 50

# Мониторинг
SPREAD_HISTORY_LENGTH = 100
LATENCY_WARNING_MS = 500

# WebSocket
WS_RECONNECT_DELAY = 5
WS_PING_INTERVAL = 30
