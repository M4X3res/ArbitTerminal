"""Тест задержек REST API"""
import asyncio
import time
from exchanges.mexc_connector import MEXCConnector
from exchanges.bybit_connector import BybitConnector
from exchanges.gate_connector import GateConnector


async def test_rest_latency():
    """Замер задержек REST запросов"""
    
    exchanges = {
        'mexc': MEXCConnector(),
        'bybit': BybitConnector(),
        'gate': GateConnector()
    }
    
    print("🚀 Тестирование REST API latency...\n")
    
    for name, exchange in exchanges.items():
        print(f"📊 {name.upper()}:")
        
        # 5 последовательных запросов
        latencies = []
        for i in range(5):
            start = time.perf_counter()
            try:
                await exchange.get_ticker("BTC/USDT")
                latency = (time.perf_counter() - start) * 1000
                latencies.append(latency)
                print(f"  Запрос {i+1}: {latency:.1f}ms")
            except Exception as e:
                print(f"  Запрос {i+1}: ОШИБКА - {e}")
            
            await asyncio.sleep(0.2)  # Избегаем rate limit
        
        if latencies:
            avg = sum(latencies) / len(latencies)
            print(f"  ➡️ Средняя: {avg:.1f}ms, Макс: {max(latencies):.1f}ms\n")
    
    # Симуляция параллельного открытия позиции
    print("⚡ Симуляция открытия арбитражной позиции (2 ордера параллельно):")
    
    start = time.perf_counter()
    try:
        results = await asyncio.gather(
            exchanges['mexc'].get_ticker("BTC/USDT"),
            exchanges['bybit'].get_ticker("BTC/USDT"),
            return_exceptions=True
        )
        total_time = (time.perf_counter() - start) * 1000
        print(f"  ✅ Время открытия: {total_time:.1f}ms")
        print(f"  📌 Это минимальное окно для исполнения арбитража\n")
    except Exception as e:
        print(f"  ❌ Ошибка: {e}\n")
    
    # Закрываем соединения
    for exchange in exchanges.values():
        await exchange.close()


if __name__ == "__main__":
    asyncio.run(test_rest_latency())
