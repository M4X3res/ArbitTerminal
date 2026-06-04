"""
Полный тест с детальным логированием всех процессов
"""
import asyncio
import time
from datetime import datetime


async def test_full_system():
    """Тест системы с полным логированием"""
    
    print("="*80)
    print("🔬 ПОЛНЫЙ ТЕСТ СИСТЕМЫ С ДЕТАЛЬНЫМ ЛОГИРОВАНИЕМ")
    print("="*80)
    print(f"⏰ Время старта: {datetime.now().strftime('%H:%M:%S')}")
    print()
    
    # ========== ЭТАП 1: Загрузка бирж ==========
    print("📦 ЭТАП 1: Загрузка коннекторов бирж")
    print("-"*80)
    
    try:
        from exchanges.mexc import MEXCExchange
        from exchanges.gate import GateExchange
        from exchanges.bybit import BybitExchange
        print("✅ Импорт коннекторов успешен")
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        return
    
    # Инициализация бирж
    print("\n🔧 Инициализация бирж...")
    exchanges = {
        'mexc': MEXCExchange(api_key="", api_secret=""),
        'gate': GateExchange(api_key="", api_secret=""),
        'bybit': BybitExchange(api_key="", api_secret="")
    }
    print(f"✅ Инициализировано {len(exchanges)} бирж")
    
    # ========== ЭТАП 2: Тестовые символы ==========
    print("\n📊 ЭТАП 2: Подготовка тестовых символов")
    print("-"*80)
    
    test_symbols = ['BTC/USDT', 'ETH/USDT']
    print(f"🎯 Тестовые пары: {test_symbols}")
    
    # ========== ЭТАП 3: Запуск WebSocket слушателей ==========
    print("\n🚀 ЭТАП 3: Запуск WebSocket слушателей")
    print("-"*80)
    
    ws_tasks = []
    for name, exchange in exchanges.items():
        print(f"▶️  Запуск слушателя {name.upper()}...")
        task = asyncio.create_task(
            exchange.start_websocket_listener(test_symbols),
            name=f"ws_{name}"
        )
        ws_tasks.append(task)
    
    print("⏳ Ожидание подключений (5 сек)...")
    await asyncio.sleep(5)
    print("✅ Подключения установлены")
    
    # ========== ЭТАП 4: Мониторинг данных ==========
    print("\n📡 ЭТАП 4: Мониторинг входящих данных")
    print("-"*80)
    
    test_duration = 15  # секунд
    start_time = time.time()
    iteration = 0
    
    # Счетчики
    data_received = {name: {sym: False for sym in test_symbols} for name in exchanges.keys()}
    
    while time.time() - start_time < test_duration:
        iteration += 1
        elapsed = int(time.time() - start_time)
        
        print(f"\n{'='*80}")
        print(f"📊 СНИМОК #{iteration} (T+{elapsed}s / {test_duration}s)")
        print(f"{'='*80}")
        
        for name, exchange in exchanges.items():
            print(f"\n🏦 {name.upper()}:")
            print(f"   📦 Orderbooks: {len(exchange.orderbooks)} пар")
            print(f"   💰 Funding rates: {len(exchange.funding_rates)} пар")
            
            # Проверяем каждый символ
            for symbol in test_symbols:
                market_data = await exchange.get_market_data(symbol)
                
                if market_data:
                    data_received[name][symbol] = True
                    spread = market_data.ask - market_data.bid
                    spread_pct = (spread / market_data.bid) * 100
                    
                    print(f"   ✅ {symbol}:")
                    print(f"      Bid: {market_data.bid:.2f}")
                    print(f"      Ask: {market_data.ask:.2f}")
                    print(f"      Spread: {spread:.2f} ({spread_pct:.3f}%)")
                    print(f"      Funding: {market_data.funding_rate*100:.4f}%")
                else:
                    print(f"   ⏳ {symbol}: Ожидание данных...")
            
            # Показываем сырые данные
            if exchange.orderbooks:
                print(f"   📋 Доступные пары в orderbooks: {list(exchange.orderbooks.keys())[:5]}")
            if exchange.funding_rates:
                print(f"   📋 Доступные пары в funding_rates: {list(exchange.funding_rates.keys())[:5]}")
        
        # Пауза между снимками
        await asyncio.sleep(5)
    
    # ========== ЭТАП 5: Статистика ==========
    print("\n📈 ЭТАП 5: Итоговая статистика")
    print("-"*80)
    
    total_expected = len(exchanges) * len(test_symbols)
    total_received = sum(sum(symbols.values()) for symbols in data_received.values())
    success_rate = (total_received / total_expected) * 100
    
    print(f"\n📊 Результаты теста:")
    print(f"   Длительность: {test_duration}s")
    print(f"   Снимков сделано: {iteration}")
    print(f"   Ожидалось данных: {total_expected}")
    print(f"   Получено данных: {total_received}")
    print(f"   Успешность: {success_rate:.1f}%")
    
    print(f"\n📋 Детализация по биржам:")
    for name, symbols in data_received.items():
        received = sum(symbols.values())
        expected = len(test_symbols)
        print(f"   {name.upper()}: {received}/{expected} ({received/expected*100:.0f}%)")
        for sym, status in symbols.items():
            status_icon = "✅" if status else "❌"
            print(f"      {status_icon} {sym}")
    
    # ========== ЭТАП 6: Остановка ==========
    print("\n🛑 ЭТАП 6: Остановка WebSocket соединений")
    print("-"*80)
    
    for name, exchange in exchanges.items():
        print(f"   Останавливаем {name.upper()}...")
        await exchange.stop_websocket()
    
    for task in ws_tasks:
        task.cancel()
    
    await asyncio.gather(*ws_tasks, return_exceptions=True)
    print("✅ Все соединения закрыты")
    
    # ========== ИТОГ ==========
    print("\n" + "="*80)
    if success_rate >= 80:
        print("🎉 ТЕСТ УСПЕШЕН!")
    elif success_rate >= 50:
        print("⚠️  ТЕСТ ЧАСТИЧНО УСПЕШЕН (требуется доработка)")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН (система не работает)")
    print("="*80)
    print(f"⏰ Время завершения: {datetime.now().strftime('%H:%M:%S')}")


if __name__ == "__main__":
    try:
        asyncio.run(test_full_system())
    except KeyboardInterrupt:
        print("\n\n⚠️  Тест прерван пользователем")
    except Exception as e:
        print(f"\n\n❌ КРИТИЧЕСКАЯ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
