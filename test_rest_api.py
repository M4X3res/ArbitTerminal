"""Проверка REST API с нулевым балансом"""
import asyncio
from env_loader import get_api_keys
from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange
from exchanges.bybit import BybitExchange
from exchanges.asterdex import AsterDEXExchange


async def test_rest_api():
    """Проверка REST API методов"""
    print("="*60)
    print("ПРОВЕРКА REST API (с балансом 0)")
    print("="*60)
    
    # Создаём коннекторы (без API ключей в конструкторе)
    exchanges = {
        "mexc": MEXCExchange(),
        "gate": GateExchange(),
        "bybit": BybitExchange(),
        "asterdex": AsterDEXExchange()
    }
    
    # Загружаем API ключи и устанавливаем их
    print("\n📝 Загрузка API ключей из .env...\n")
    
    for name, exchange in exchanges.items():
        try:
            api_key, api_secret = get_api_keys(name)
            if api_key and api_secret:
                exchange.api_key = api_key
                exchange.api_secret = api_secret
                print(f"✅ {name}: API ключи загружены")
            else:
                print(f"⚠️  {name}: API ключи не найдены в .env")
        except Exception as e:
            print(f"❌ {name}: Ошибка загрузки ключей - {e}")
    
    print("\n1. Проверка подключения к API...\n")
    
    for name, exchange in exchanges.items():
        print(f"--- {name.upper()} ---")
        
        try:
            # Тест 1: Получение баланса
            balance = await exchange.get_balance()
            print(f"✅ get_balance(): {balance} USD")
            
            # Тест 2: Получение инструментов
            try:
                instruments = await exchange.get_instruments()
                print(f"✅ get_instruments(): {len(instruments)} пар")
            except Exception as e:
                print(f"⚠️  get_instruments() error: {e}")
            
            # Тест 3: Попытка создать ордер (будет ошибка, но API работает)
            print(f"🔄 Попытка создать тестовый ордер...")
            try:
                result = await exchange.place_order(
                    symbol="BTCUSDT",
                    side="buy",
                    size=10  # Минимальный размер
                )
                print(f"⚠️  Ордер создан (неожиданно!): {result}")
            except Exception as e:
                error_msg = str(e)
                if "insufficient" in error_msg.lower() or "balance" in error_msg.lower():
                    print(f"✅ API работает! Ошибка: insufficient balance (ожидаемо)")
                elif "invalid" in error_msg.lower() or "signature" in error_msg.lower():
                    print(f"❌ API ключи неверны или подпись неправильная")
                else:
                    print(f"⚠️  Ошибка: {error_msg}")
            
            print()
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}\n")
    
    print("="*60)
    print("ИТОГ:")
    print("✅ Если видите 'get_balance()' и 'get_instruments()' — API работает")
    print("✅ Если видите 'insufficient balance' — всё настроено правильно!")
    print("❌ Если 'invalid signature' — проверьте API ключи в .env")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_rest_api())
