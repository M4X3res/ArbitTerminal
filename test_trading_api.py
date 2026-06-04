"""Пример использования торговых методов"""
import asyncio
from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange
from exchanges.bybit import BybitExchange
from exchanges.asterdex import AsterDEXExchange


async def test_trading_api():
    """Тестирование торговых методов (только с валидными API ключами)"""
    
    # Пример с MEXC
    mexc = MEXCExchange(
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    try:
        # Получить баланс
        balance = await mexc.get_balance()
        print(f"MEXC Balance: {balance} USDT")
        
        # Открыть позицию (ОСТОРОЖНО: реальная торговля!)
        # order = await mexc.place_order(
        #     symbol="BTC_USDT",
        #     side="buy",  # "buy" для лонг, "sell" для шорт
        #     size=0.001,
        #     order_type="market"
        # )
        # print(f"Order placed: {order}")
        
        # Закрыть позицию
        # close_result = await mexc.close_position(
        #     symbol="BTC_USDT",
        #     side="buy"
        # )
        # print(f"Position closed: {close_result}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    # Пример с Gate.io
    gate = GateExchange(
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    try:
        balance = await gate.get_balance()
        print(f"Gate.io Balance: {balance} USDT")
    except Exception as e:
        print(f"Error: {e}")
    
    # Пример с Bybit
    bybit = BybitExchange(
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    try:
        balance = await bybit.get_balance()
        print(f"Bybit Balance: {balance} USDT")
    except Exception as e:
        print(f"Error: {e}")
    
    # Пример с AsterDEX
    asterdex = AsterDEXExchange(
        api_key="your_api_key",
        api_secret="your_api_secret"
    )
    
    try:
        balance = await asterdex.get_balance()
        print(f"AsterDEX Balance: {balance} USDT")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    print("="*50)
    print("Trading API Examples")
    print("="*50)
    print("\nВНИМАНИЕ: Замените API ключи на реальные!")
    print("Раскомментируйте строки для реальной торговли\n")
    
    asyncio.run(test_trading_api())
