"""Тестирование коннекторов бирж"""
import asyncio
from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange


async def test_mexc():
    """Тест MEXC коннектора"""
    print("\n🔧 Testing MEXC Exchange...")
    
    exchange = MEXCExchange()
    await exchange.connect_ws()
    
    # Получение инструментов
    instruments = await exchange.get_instruments()
    print(f"✅ Found {len(instruments)} instruments")
    print(f"   First 5: {instruments[:5]}")
    
    # Подписка на первые 3 инструмента
    if instruments:
        test_symbols = instruments[:3]
        await exchange.subscribe_orderbook(test_symbols)
        
        # Получение данных в течение 10 секунд
        print(f"📊 Listening for market data (10 seconds)...")
        for _ in range(5):
            data = await exchange.get_market_data(None)
            print(f"   {data.symbol}: Bid={data.bid}, Ask={data.ask}, FR={data.funding_rate}")
            await asyncio.sleep(2)


async def test_gate():
    """Тест Gate.io коннектора"""
    print("\n🔧 Testing Gate.io Exchange...")
    
    exchange = GateExchange()
    await exchange.connect_ws()
    
    # Получение инструментов
    instruments = await exchange.get_instruments()
    print(f"✅ Found {len(instruments)} instruments")
    print(f"   First 5: {instruments[:5]}")
    
    # Подписка на первые 3 инструмента
    if instruments:
        test_symbols = instruments[:3]
        await exchange.subscribe_orderbook(test_symbols)
        
        # Получение данных в течение 10 секунд с таймаутом
        print(f"📊 Listening for market data (10 seconds)...")
        
        timeout_seconds = 10
        start_time = asyncio.get_event_loop().time()
        data_count = 0
        
        while (asyncio.get_event_loop().time() - start_time) < timeout_seconds:
            try:
                data = await asyncio.wait_for(exchange.get_market_data(None), timeout=3.0)
                print(f"   {data.symbol}: Bid={data.bid}, Ask={data.ask}, FR={data.funding_rate}")
                data_count += 1
                await asyncio.sleep(2)
            except asyncio.TimeoutError:
                print("   ⏰ Timeout waiting for data (3s)...")
                break
            except Exception as e:
                print(f"   ❌ Error: {e}")
                break
        
        if data_count == 0:
            print("   ⚠️  No data received - run debug_gate.py to investigate")


async def main():
    """Запуск тестов"""
    print("=" * 60)
    print("🧪 Exchange Connectors Test Suite")
    print("=" * 60)
    
    try:
        await test_mexc()
    except Exception as e:
        print(f"❌ MEXC test failed: {e}")
    
    try:
        await test_gate()
    except Exception as e:
        print(f"❌ Gate.io test failed: {e}")
    
    print("\n" + "=" * 60)
    print("✅ Tests completed")


if __name__ == '__main__':
    asyncio.run(main())
