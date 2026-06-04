"""Главный модуль арбитражной системы"""
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        RotatingFileHandler('arbitrage.log', maxBytes=10*1024*1024, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from env_loader import get_api_keys, get_telegram_config
from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange
from exchanges.bybit import BybitExchange

from market_data_engine import MarketDataEngine
from arbitrage_engine import ArbitrageEngine
from trading_engine import TradingEngine
from risk_manager import RiskManager
from position_manager import PositionManager
from strategy_selector import StrategySelector
from utils import TelegramLogger

from config import (
    OPEN_THRESHOLD, MAX_OPEN_POSITIONS
)

# Стратегия выбирается динамически
STRATEGY = 'dynamic'  # используется только для отображения

# Импорт производительной конфигурации (если есть)
try:
    from performance_config import (
        MAX_WORKERS, SYMBOLS_PER_EXCHANGE, ANALYSIS_INTERVAL,
        STATS_INTERVAL, OPPORTUNITY_DISPLAY_INTERVAL, TOP_OPPORTUNITIES
    )
except ImportError:
    # Дефолтные значения
    MAX_WORKERS = 4
    SYMBOLS_PER_EXCHANGE = 10
    ANALYSIS_INTERVAL = 0.3
    STATS_INTERVAL = 30
    OPPORTUNITY_DISPLAY_INTERVAL = 3
    TOP_OPPORTUNITIES = 5


class ArbitrageSystem:
    """Основная система арбитража"""
    
    def __init__(self, use_api_keys=False, initial_balance=1000, strategy='amplitude', demo_mode=True):
        self.use_api_keys = use_api_keys
        self.initial_balance = initial_balance
        self.strategy_name = strategy
        self.demo_mode = demo_mode
        self.exchanges = {}
        self.market_data_engine = None
        self.arbitrage_engine = None
        self.trading_engine = None
        self.risk_manager = None
        self.strategy_selector = None
        self.position_manager = None
        self.telegram = None
        self.running = False
        self.pairwise_symbols = {}  # Попарные пересечения символов
        self.executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)  # Пул потоков для анализа
    
    async def initialize(self):
        """Инициализация всех компонентов"""
        print("\n=== Инициализация ArbitrageSystem ===")
        
        # Создаём коннекторы бирж
        print("\n1. Создание коннекторов бирж...")
        
        if self.use_api_keys:
            print("   📝 Загрузка API ключей из .env...")
            mexc_key, mexc_secret = get_api_keys('mexc')
            gate_key, gate_secret = get_api_keys('gate')
            bybit_key, bybit_secret = get_api_keys('bybit')
            
            self.exchanges = {
                "mexc": MEXCExchange(),
                "gate": GateExchange(),
                "bybit": BybitExchange()
            }
            
            # Устанавливаем API ключи
            self.exchanges["mexc"].api_key = mexc_key
            self.exchanges["mexc"].api_secret = mexc_secret
            self.exchanges["gate"].api_key = gate_key
            self.exchanges["gate"].api_secret = gate_secret
            self.exchanges["bybit"].api_key = bybit_key
            self.exchanges["bybit"].api_secret = bybit_secret
        else:
            self.exchanges = {
                "mexc": MEXCExchange(),
                "gate": GateExchange(),
                "bybit": BybitExchange()
            }
        
        # Инициализируем каждую биржу
        for name, exchange in self.exchanges.items():
            print(f"   - Инициализация {name}...")
            await exchange.initialize()
        
        print("   ✓ Все биржи инициализированы")
        
        # Создаём движки
        print("\n2. Создание движков...")
        self.market_data_engine = MarketDataEngine(self.exchanges)
        self.arbitrage_engine = ArbitrageEngine(max_workers=MAX_WORKERS)  # Параллельный движок
        self.trading_engine = TradingEngine(self.exchanges, demo_mode=self.demo_mode)
        self.risk_manager = RiskManager(initial_balance=self.initial_balance)
        
        # Динамический селектор стратегий
        self.strategy_selector = StrategySelector()
        
        # Telegram logger (загрузка из .env)
        telegram_bot_token, telegram_chat_id = get_telegram_config()
        self.telegram = TelegramLogger(telegram_bot_token, telegram_chat_id)
        
        # Position Manager
        self.position_manager = PositionManager(
            self.trading_engine,
            self.strategy_selector,
            self.telegram,
            self.risk_manager  # Передаём risk_manager для обновления баланса
        )
        
        mode_text = "DEMO" if self.demo_mode else "LIVE"
        print(f"   ✓ Все движки созданы ({mode_text} режим)")
        print(f"   📊 Стратегия: DYNAMIC (выбирается по спреду)")
        print(f"   📊 Баланс: {self.initial_balance} USD")
        print(f"   📊 Размер позиции: {self.risk_manager.calculate_position_size()} USD (1/10 баланса)")
        print(f"   📊 Макс позиций: {MAX_OPEN_POSITIONS}")
        print(f"   📊 Минимальный спред: {OPEN_THRESHOLD}%")
        
        # Уведомление в Telegram
        await self.telegram.log_system_start(
            balance=self.initial_balance,
            strategy=self.strategy_name.upper(),
            exchanges=list(self.exchanges.keys())
        )
        
        print("\n=== Система готова ===\n")
    
    async def run_market_data_collection(self):
        """Запуск сбора рыночных данных"""
        print("📊 Запуск сбора рыночных данных...")
        
        # Получаем попарные пересечения
        pairwise_symbols = await self.market_data_engine.get_common_symbols(limit=None)
        
        # Используем объединение всех пар (уникальные символы)
        all_symbols = set()
        for pair_key, symbols in pairwise_symbols.items():
            if pair_key != 'all':
                all_symbols.update(symbols)
        
        common_symbols = list(all_symbols)
        print(f"   📈 Торговых пар для мониторинга: {len(common_symbols)}")
        
        if len(common_symbols) > 0:
            print(f"   📋 Примеры: {', '.join(list(common_symbols)[:5])}")
        
        # Сохраняем информацию о парах для арбитража
        self.pairwise_symbols = pairwise_symbols
        
        # Подписываемся на данные (запускает фоновые задачи)
        await self.market_data_engine.subscribe_all(common_symbols)
        print("   ✓ Данные поступают в реальном времени")
    
    async def run_arbitrage_monitoring(self):
        """Непрерывный мониторинг арбитража с автоматическим открытием/закрытием"""
        print(f"\n🔍 Запуск высокопроизводительного мониторинга...")
        print(f"   Потоков: {MAX_WORKERS} | Интервал: {ANALYSIS_INTERVAL*1000:.0f}ms\n")
        
        iteration = 0
        last_stats_time = asyncio.get_event_loop().time()
        last_opportunity_time = 0
        
        while self.running:
            iteration += 1
            current_time = asyncio.get_event_loop().time()
            
            # Получаем данные без блокировки (из кэша)
            market_data = self.market_data_engine.get_latest_data()
            
            if not market_data or not any(market_data.values()):
                await asyncio.sleep(0.05)
                continue
            
            # Мониторинг открытых позиций (параллельно)
            monitor_task = asyncio.create_task(
                self.position_manager.monitor_positions(market_data)
            )
            
            # Параллельный анализ возможностей (батчинг в отдельных потоках)
            opportunities = await asyncio.get_event_loop().run_in_executor(
                None,  # Используем дефолтный executor
                self.arbitrage_engine.find_opportunities_parallel,  # Параллельная версия
                market_data,
                OPEN_THRESHOLD,
                50  # batch_size
            )
            
            # Ждём завершения мониторинга позиций
            await monitor_task
            
            # Показываем возможности
            if opportunities and (current_time - last_opportunity_time) >= OPPORTUNITY_DISPLAY_INTERVAL:
                last_opportunity_time = current_time
                
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 🎯 Найдено {len(opportunities)} возможностей:")
                
                # Обрабатываем топ возможности
                for opp in opportunities[:TOP_OPPORTUNITIES]:
                    risk_check = self.risk_manager.check_opportunity(opp, market_data)
                    
                    status = "✅" if risk_check["approved"] else "❌"
                    print(f"   {status} {opp.symbol}: {opp.exchange_long} ↔ {opp.exchange_short}")
                    print(f"      Спред: {opp.spread:.3f}% | Funding: {opp.funding_diff:.4f}")
                    
                    if risk_check["approved"]:
                        # Повторная проверка спреда перед открытием (защита от схлопывания)
                        long_data = market_data.get(opp.exchange_long, {}).get(opp.symbol)
                        short_data = market_data.get(opp.exchange_short, {}).get(opp.symbol)
                        
                        if long_data and short_data:
                            current_spread = (short_data.bid - long_data.ask) / long_data.ask * 100
                            
                            # Если спред упал более чем на 10%, пропускаем
                            if current_spread < opp.spread * 0.9:
                                print(f"      ⚠️ Спред схлопнулся: {opp.spread:.2f}% → {current_spread:.2f}%, пропускаем")
                                continue
                        
                        # Динамический выбор стратегии по спреду
                        strategy, strategy_name = self.strategy_selector.select_strategy(opp.spread)
                        
                        # Автоматическое открытие позиции
                        position_size = risk_check["position_size"]
                        success, pair_id = await self.trading_engine.execute_arbitrage(
                            opp, position_size, strategy_name
                        )
                        
                        if success:
                            trade = self.trading_engine.get_position(pair_id)
                            self.position_manager.register_position(trade)
                            self.risk_manager.register_position(opp.symbol, opp.exchange_long, opp.exchange_short)
                            
                            print(f"      ✅ Позиция открыта: {pair_id[:8]}... (стратегия: {strategy_name})")
                            
                            await self.telegram.log_position_opened(
                                symbol=opp.symbol,
                                exchange_long=opp.exchange_long,
                                exchange_short=opp.exchange_short,
                                spread=opp.spread,
                                position_size=position_size
                            )
                    else:
                        print(f"      Причина: {risk_check['reason']}")
                
                print()
            
            # Статистика
            if current_time - last_stats_time >= STATS_INTERVAL:
                stats = self.arbitrage_engine.get_statistics()
                pos_stats = self.position_manager.get_statistics()
                
                print(f"📈 Статистика (итерация {iteration}):")
                print(f"   Возможностей найдено: {stats['total_opportunities']}")
                if stats['total_opportunities'] > 0:
                    print(f"   Средний спред: {stats['avg_spread']:.3f}%")
                    print(f"   Макс спред: {stats['max_spread']:.3f}%")
                
                print(f"   Открытых позиций: {len(self.position_manager.positions)}")
                if pos_stats['total_trades'] > 0:
                    print(f"   Закрытых сделок: {pos_stats['total_trades']}")
                    print(f"   Win rate: {pos_stats['win_rate']:.1f}%")
                    print(f"   Общий PnL: {pos_stats['total_pnl']:+.2f} USD")
                print()
                last_stats_time = current_time
            
            await asyncio.sleep(ANALYSIS_INTERVAL)
    
    async def run(self, duration_seconds=None):
        """Запуск системы на определенное время (или бесконечно)"""
        self.running = True
        
        try:
            # Запускаем сбор данных
            await self.run_market_data_collection()
            
            # Даём время на накопление данных
            print("⏳ Ожидание первых данных (10 сек)...\n")
            await asyncio.sleep(10)
            
            # Запускаем мониторинг
            if duration_seconds:
                print(f"▶️  Запуск мониторинга на {duration_seconds} секунд...\n")
                try:
                    await asyncio.wait_for(
                        self.run_arbitrage_monitoring(),
                        timeout=duration_seconds
                    )
                except asyncio.TimeoutError:
                    print(f"\n⏱️  Время вышло ({duration_seconds}s)")
            else:
                print(f"▶️  Запуск бесконечного мониторинга (Ctrl+C для остановки)...\n")
                await self.run_arbitrage_monitoring()
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Остановка по запросу пользователя...")
        finally:
            self.running = False
            await self.cleanup()
    
    async def cleanup(self):
        """Очистка ресурсов"""
        print("\n🧹 Завершение работы...")
        
        # Останавливаем слушателей
        if self.market_data_engine:
            await self.market_data_engine.stop()
        
        # Закрываем ThreadPoolExecutor
        if hasattr(self, 'executor'):
            self.executor.shutdown(wait=False)
        
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
                print(f"   ✓ {name} закрыт")
            except:
                pass
        
        print("✅ Система остановлена\n")


async def main():
    """Основная функция"""
    print("="*70)
    print("   CRYPTO ARBITRAGE SYSTEM — PRODUCTION READY")
    print(f"   Strategy: {STRATEGY.upper()} | Min Spread: {OPEN_THRESHOLD}%")
    print(f"   Auto trading | Position management | Risk control")
    print("="*70)
    
    # Выбор режима
    USE_LIVE_TRADING = False  # ← Измените на True для реальной торговли
    
    # Создаём систему
    system = ArbitrageSystem(
        use_api_keys=USE_LIVE_TRADING,  # API ключи для live режима
        initial_balance=1000,
        strategy=STRATEGY,
        demo_mode=not USE_LIVE_TRADING  # demo если не live
    )
    
    # Инициализируем
    await system.initialize()
    
    # Запускаем
    duration = None  # 2 мин для demo, бесконечно для live
    await system.run(duration_seconds=duration)
    
    print("\n" + "="*70)
    if USE_LIVE_TRADING:
        print("   Live торговля остановлена")
    else:
        print("   Demo тестирование завершено")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
