"""Проверка работоспособности системы"""
import asyncio
import sys

async def test_imports():
    """Тест 1: Проверка импортов"""
    print("="*60)
    print("ТЕСТ 1: Проверка импортов")
    print("="*60)
    
    try:
        from env_loader import get_api_keys
        print("✅ env_loader")
        
        from exchanges.mexc import MEXCExchange
        from exchanges.gate import GateExchange
        from exchanges.bybit import BybitExchange
        from exchanges.asterdex import AsterDEXExchange
        print("✅ exchanges")
        
        from market_data_engine import MarketDataEngine
        print("✅ market_data_engine")
        
        from arbitrage_engine import ArbitrageEngine
        print("✅ arbitrage_engine")
        
        from trading_engine import TradingEngine
        print("✅ trading_engine")
        
        from risk_manager import RiskManager
        print("✅ risk_manager")
        
        from position_manager import PositionManager
        print("✅ position_manager")
        
        from strategies import AmplitudeStrategy, SpreadCollapseStrategy
        print("✅ strategies")
        
        from utils import TelegramLogger
        print("✅ telegram_logger")
        
        from config import STRATEGY, OPEN_THRESHOLD
        print(f"✅ config (STRATEGY={STRATEGY}, THRESHOLD={OPEN_THRESHOLD}%)")
        
        try:
            from performance_config import MAX_WORKERS
            print(f"✅ performance_config (MAX_WORKERS={MAX_WORKERS})")
        except ImportError:
            print("⚠️  performance_config не найден (используются дефолты)")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        return False

async def test_initialization():
    """Тест 2: Инициализация компонентов"""
    print("\n" + "="*60)
    print("ТЕСТ 2: Инициализация компонентов")
    print("="*60)
    
    try:
        from exchanges.mexc import MEXCExchange
        from exchanges.gate import GateExchange
        from exchanges.bybit import BybitExchange
        from exchanges.asterdex import AsterDEXExchange
        from market_data_engine import MarketDataEngine
        from arbitrage_engine import ArbitrageEngine
        from trading_engine import TradingEngine
        from risk_manager import RiskManager
        from position_manager import PositionManager
        from strategies import SpreadCollapseStrategy
        from utils import TelegramLogger
        
        # Создание бирж
        exchanges = {
            "mexc": MEXCExchange(),
            "gate": GateExchange(),
            "bybit": BybitExchange(),
            "asterdex": AsterDEXExchange()
        }
        print("✅ Биржи созданы")
        
        # Движки
        market_data_engine = MarketDataEngine(exchanges)
        print("✅ MarketDataEngine")
        
        arbitrage_engine = ArbitrageEngine(max_workers=4)
        print("✅ ArbitrageEngine")
        
        trading_engine = TradingEngine(exchanges, demo_mode=True)
        print("✅ TradingEngine")
        
        risk_manager = RiskManager(initial_balance=1000)
        print("✅ RiskManager")
        
        close_strategy = SpreadCollapseStrategy()
        print("✅ SpreadCollapseStrategy")
        
        telegram = TelegramLogger(None, None)
        print("✅ TelegramLogger")
        
        position_manager = PositionManager(trading_engine, close_strategy, telegram)
        print("✅ PositionManager")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_websocket_connection():
    """Тест 3: WebSocket подключение"""
    print("\n" + "="*60)
    print("ТЕСТ 3: WebSocket подключение (5 секунд)")
    print("="*60)
    
    try:
        from exchanges.mexc import MEXCExchange
        from exchanges.gate import GateExchange
        
        exchanges = {
            "mexc": MEXCExchange(),
            "gate": GateExchange()
        }
        
        for name, exchange in exchanges.items():
            print(f"   Подключение к {name}...")
            await exchange.initialize()
            print(f"   ✅ {name} подключен")
        
        print("\n   Ожидание данных 5 секунд...")
        await asyncio.sleep(5)
        
        # Закрытие
        for name, exchange in exchanges.items():
            await exchange.close()
            print(f"   ✓ {name} закрыт")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_arbitrage_engine():
    """Тест 4: ArbitrageEngine с тестовыми данными"""
    print("\n" + "="*60)
    print("ТЕСТ 4: ArbitrageEngine (тестовые данные)")
    print("="*60)
    
    try:
        from arbitrage_engine import ArbitrageEngine
        from models import MarketData
        from datetime import datetime
        
        engine = ArbitrageEngine(max_workers=4)
        
        # Создаём тестовые данные
        market_data = {
            "bybit": {
                "BTCUSDT": MarketData(
                    exchange="bybit",
                    symbol="BTCUSDT",
                    bid=65000,
                    ask=65010,
                    funding_rate=0.0001,
                    timestamp=datetime.now()
                )
            },
            "gate": {
                "BTCUSDT": MarketData(
                    exchange="gate",
                    symbol="BTCUSDT",
                    bid=65100,
                    ask=65110,
                    funding_rate=0.0002,
                    timestamp=datetime.now()
                )
            }
        }
        
        # Тест последовательного анализа
        print("   Тест find_opportunities()...")
        opportunities = engine.find_opportunities(market_data, threshold=0.1)
        print(f"   ✅ Найдено {len(opportunities)} возможностей")
        
        # Тест параллельного анализа
        print("   Тест find_opportunities_parallel()...")
        opportunities_parallel = engine.find_opportunities_parallel(market_data, threshold=0.1, batch_size=50)
        print(f"   ✅ Найдено {len(opportunities_parallel)} возможностей (параллельно)")
        
        if opportunities:
            opp = opportunities[0]
            print(f"   Пример: {opp.symbol} спред {opp.spread:.3f}%")
        
        return True
    except Exception as e:
        print(f"❌ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Запуск всех тестов"""
    print("\n" + "="*60)
    print("  ПРОВЕРКА СИСТЕМЫ АРБИТРАЖА")
    print("="*60 + "\n")
    
    results = []
    
    # Тест 1
    result = await test_imports()
    results.append(("Импорты", result))
    
    if not result:
        print("\n❌ Тесты остановлены из-за ошибки импорта")
        sys.exit(1)
    
    # Тест 2
    result = await test_initialization()
    results.append(("Инициализация", result))
    
    # Тест 3 (опционально - требует интернет)
    print("\n⚠️  Тест 3 (WebSocket) пропущен (требует подключение к биржам)")
    print("   Запустите main.py для полного теста")
    
    # Тест 4
    result = await test_arbitrage_engine()
    results.append(("ArbitrageEngine", result))
    
    # Итоги
    print("\n" + "="*60)
    print("ИТОГИ ПРОВЕРКИ")
    print("="*60)
    
    for name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"   {name}: {status}")
    
    all_passed = all(r for _, r in results)
    
    if all_passed:
        print("\n🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ! Система готова к запуску.")
        print("\nЗапустите: python main.py")
    else:
        print("\n❌ НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОШЛИ. Проверьте ошибки выше.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
