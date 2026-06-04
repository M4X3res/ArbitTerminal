"""Smoke test wrapper для проверки demo режима (30 секунд)"""
import asyncio
import sys
from datetime import datetime

# Импорт основных компонентов
from main import ArbitrageSystem

async def smoke_test():
    """Быстрый smoke test на 30 секунд"""
    print("\n" + "="*70)
    print("   🧪 SMOKE TEST - DEMO MODE (30 секунд)")
    print("   ⚠️  NO LIVE TRADING - NO REAL ORDERS")
    print("="*70)
    
    start_time = datetime.now()
    
    # Создаём систему в DEMO режиме
    system = ArbitrageSystem(
        use_api_keys=False,  # БЕЗ API ключей
        initial_balance=1000,
        strategy='dynamic',
        demo_mode=True  # DEMO режим
    )
    
    try:
        # Инициализируем
        print("\n📋 Инициализация компонентов...")
        await system.initialize()
        
        # Запускаем на 30 секунд
        print("\n🚀 Запуск мониторинга на 30 секунд...\n")
        await system.run(duration_seconds=30)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ Ошибка во время теста: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Остановка системы
        if hasattr(system, 'running'):
            system.running = False
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "="*70)
        print(f"   ✅ Smoke test завершён за {duration:.1f} секунд")
        print("   📊 Статус: DEMO режим, реальные ордера НЕ размещались")
        print("="*70)
        
        # Показываем краткую статистику
        if hasattr(system, 'market_data_engine') and system.market_data_engine:
            print("\n📈 Полученные данные:")
            market_data = system.market_data_engine.market_data
            for exchange, symbols in market_data.items():
                if symbols:
                    sample_symbol = list(symbols.keys())[0]
                    sample_data = symbols[sample_symbol]
                    print(f"   {exchange}: {len(symbols)} symbols, "
                          f"funding={sample_data.funding_rate:.6f} "
                          f"(sample: {sample_symbol})")
        
        if hasattr(system, 'position_manager') and system.position_manager:
            open_count = len(system.position_manager.positions)
            closed_count = len(system.position_manager.closed_positions)
            print(f"\n💼 Позиции (DEMO):")
            print(f"   Открыто: {open_count}")
            print(f"   Закрыто: {closed_count}")

if __name__ == "__main__":
    asyncio.run(smoke_test())
