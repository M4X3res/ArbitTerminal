"""Конфигурация арбитражной системы"""

# Биржи (3 working exchanges)
EXCHANGES = ['mexc', 'gate', 'bybit']

# === СТРАТЕГИЯ ОТКРЫТИЯ ===
# Стратегия выбирается АВТОМАТИЧЕСКИ по размеру спреда:
# - 0.7-2%: amplitude (быстрый скальпинг)
# - 2-5%: balanced (средняя)
# - 5%+: collapse (схлопывание)

OPEN_THRESHOLD = 0.7  # Минимальный спред для открытия
MAX_SPREAD_OPEN = 15.0  # Максимальный спред

# === СТРАТЕГИЯ ЗАКРЫТИЯ ===
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
POSITION_SIZE_FRACTION = 0.1
MAX_OPEN_POSITIONS = 3  # Максимум 3 позиции одновременно (на всех биржах)
MAX_POSITIONS_PER_EXCHANGE = 3  # Максимум 3 позиции на одной бирже
MAX_LEVERAGE = 10
MIN_LIQUIDITY_MULTIPLIER = 1.5

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
