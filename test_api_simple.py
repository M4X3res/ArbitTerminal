"""Упрощённая проверка API ключей"""
import asyncio
import aiohttp
import time
import hmac
import hashlib
from env_loader import get_api_keys


async def test_mexc():
    """MEXC API тест"""
    print("--- MEXC ---")
    api_key, api_secret = get_api_keys('mexc')
    
    try:
        async with aiohttp.ClientSession() as session:
            # Публичный endpoint - список инструментов
            async with session.get('https://contract.mexc.com/api/v1/contract/detail') as resp:
                data = await resp.json()
                if data.get('success'):
                    print(f"✅ Публичный API: {len(data['data'])} контрактов")
                else:
                    print(f"❌ Ошибка: {data}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    print()


async def test_gate():
    """Gate.io API тест"""
    print("--- GATE.IO ---")
    api_key, api_secret = get_api_keys('gate')
    
    try:
        async with aiohttp.ClientSession() as session:
            # Публичный endpoint - список контрактов
            async with session.get('https://fx-api.gateio.ws/api/v4/futures/usdt/contracts') as resp:
                data = await resp.json()
                print(f"✅ Публичный API: {len(data)} контрактов")
                
            # Приватный endpoint - баланс (требует подпись)
            if api_key and api_secret:
                timestamp = str(int(time.time()))
                method = "GET"
                url_path = "/api/v4/futures/usdt/accounts"
                query = ""
                body = ""
                
                body_hash = hashlib.sha512(body.encode()).hexdigest()
                sign_string = f"{method}\n{url_path}\n{query}\n{body_hash}\n{timestamp}"
                signature = hmac.new(api_secret.encode(), sign_string.encode(), hashlib.sha512).hexdigest()
                
                headers = {
                    'KEY': api_key,
                    'Timestamp': timestamp,
                    'SIGN': signature
                }
                
                async with session.get('https://fx-api.gateio.ws/api/v4/futures/usdt/accounts', headers=headers) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Приватный API: баланс = {data.get('total', 0)} USD")
                    else:
                        text = await resp.text()
                        print(f"❌ Приватный API ошибка ({resp.status}): {text[:100]}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    print()


async def test_bybit():
    """Bybit API тест"""
    print("--- BYBIT ---")
    api_key, api_secret = get_api_keys('bybit')
    
    try:
        async with aiohttp.ClientSession() as session:
            # Публичный endpoint - список инструментов
            async with session.get('https://api.bybit.com/v5/market/instruments-info?category=linear') as resp:
                data = await resp.json()
                contracts = data.get('result', {}).get('list', [])
                print(f"✅ Публичный API: {len(contracts)} контрактов")
                
            # Приватный endpoint - баланс
            if api_key and api_secret:
                timestamp = str(int(time.time() * 1000))
                recv_window = "5000"
                query = f"accountType=UNIFIED&timestamp={timestamp}"
                
                sign_string = f"{timestamp}{api_key}{recv_window}{query}"
                signature = hmac.new(api_secret.encode(), sign_string.encode(), hashlib.sha256).hexdigest()
                
                headers = {
                    'X-BAPI-API-KEY': api_key,
                    'X-BAPI-SIGN': signature,
                    'X-BAPI-TIMESTAMP': timestamp,
                    'X-BAPI-RECV-WINDOW': recv_window
                }
                
                async with session.get(
                    f'https://api.bybit.com/v5/account/wallet-balance?{query}',
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        if data.get('retCode') == 0:
                            balance = data['result']['list'][0].get('totalAvailableBalance', 0)
                            print(f"✅ Приватный API: баланс = {balance} USD")
                        else:
                            print(f"❌ API ошибка: {data.get('retMsg')}")
                    else:
                        text = await resp.text()
                        print(f"❌ HTTP ошибка ({resp.status}): {text[:100]}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    print()


async def main():
    print("="*60)
    print("ПРОВЕРКА API (упрощённая)")
    print("="*60)
    print()
    
    await test_mexc()
    await test_gate()
    await test_bybit()
    
    print("="*60)
    print("ИТОГ:")
    print("✅ Если видите 'Публичный API' — биржа доступна")
    print("✅ Если видите 'Приватный API: баланс' — API ключи работают!")
    print("❌ Если ошибка подписи — проверьте .env")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
