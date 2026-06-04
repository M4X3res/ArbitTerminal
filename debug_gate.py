"""Дебаг тест для Gate.io - смотрим что приходит от WebSocket"""
import asyncio
import json
from exchanges.gate import GateExchange


async def debug_gate():
    """Тест с выводом всех сообщений"""
    print("🔧 Gate.io Debug Test...")
    
    exchange = GateExchange()
    await exchange.connect_ws()
    
    # Получение инструментов
    instruments = await exchange.get_instruments()
    print(f"✅ Found {len(instruments)} instruments")
    
    # Подписка на 1 популярный символ
    test_symbol = "BTC_USDT"
    print(f"📊 Subscribing to {test_symbol}...")
    await exchange.subscribe_orderbook([test_symbol])
    
    # Слушаем 20 секунд и выводим уникальные типы сообщений
    print(f"👂 Listening for messages (20 seconds)...\n")
    
    count = 0
    seen_types = {}
    start = asyncio.get_event_loop().time()
    
    while (asyncio.get_event_loop().time() - start) < 20:
        try:
            message = await asyncio.wait_for(exchange.ws.recv(), timeout=2.0)
            data = json.loads(message)
            count += 1
            
            # Определяем тип сообщения
            channel = data.get("channel", "unknown")
            event = data.get("event", "unknown")
            msg_type = f"{channel}:{event}"
            
            # Показываем только первый пример каждого типа
            if msg_type not in seen_types:
                seen_types[msg_type] = data
                print(f"[NEW TYPE #{len(seen_types)}] {msg_type}")
                print(json.dumps(data, indent=2))
                print("-" * 60 + "\n")
            
        except asyncio.TimeoutError:
            print("⏰ No more messages...")
            break
        except Exception as e:
            print(f"❌ Error: {e}")
            break
    
    print(f"\n✅ Summary:")
    print(f"   Total messages: {count}")
    print(f"   Unique types: {len(seen_types)}")
    print(f"   Types found: {list(seen_types.keys())}")


if __name__ == '__main__':
    asyncio.run(debug_gate())
