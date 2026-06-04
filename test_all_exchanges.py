"""Test all 6 exchange connectors"""
import asyncio
from exchanges.bybit import BybitExchange
from exchanges.bitget import BitgetExchange
from exchanges.bingx import BingXExchange
from exchanges.asterdex import AsterDEXExchange


async def test_exchange(exchange_class, timeout=20):
    """Test a single exchange connector"""
    print(f"\n{'='*50}")
    print(f"Testing {exchange_class.__name__}")
    print(f"{'='*50}")
    
    exchange = None
    try:
        exchange = exchange_class()
        await exchange.initialize()
        
        # Get instruments
        print("\nFetching instruments...")
        instruments = await exchange.get_instruments()
        print(f"[OK] Found {len(instruments)} instruments")
        if instruments:
            print(f"  First 5: {instruments[:5]}")
        
        if not instruments:
            print("[FAIL] No instruments found")
            return
        
        # Subscribe to first 3
        test_symbols = instruments[:3]
        print(f"\n[OK] Subscribing to: {test_symbols}")
        
        await exchange.subscribe_orderbook(test_symbols)
        await exchange.subscribe_funding_rate(test_symbols)
        
        # Collect some data
        print("\n[OK] Collecting market data...")
        collected = 0
        start_time = asyncio.get_event_loop().time()
        
        while collected < 5:
            if asyncio.get_event_loop().time() - start_time > timeout:
                print(f"\n[WARN] Timeout after {timeout}s")
                break
                
            try:
                data = await asyncio.wait_for(
                    exchange.get_market_data(test_symbols[0]),
                    timeout=5.0
                )
                collected += 1
                print(f"  [{collected}] {data.symbol}: bid={data.bid:.4f}, ask={data.ask:.4f}, funding={data.funding_rate:.6f}")
            except asyncio.TimeoutError:
                print("  No data within 5s...")
                break
            except Exception as e:
                print(f"  Error getting data: {e}")
                break
        
        if collected > 0:
            print(f"\n[PASS] {exchange.name} test completed: {collected} messages received")
        else:
            print(f"\n[WARN] {exchange.name} test incomplete: no data received")
        
    except Exception as e:
        print(f"\n[FAIL] Error testing {exchange_class.__name__}: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if exchange:
            try:
                await exchange.close()
            except:
                pass


async def main():
    """Test new exchanges (Bybit, Bitget, BingX, AsterDEX)"""
    exchanges = [
        BybitExchange,
        BitgetExchange,
        BingXExchange,
        AsterDEXExchange,
    ]
    
    for exchange_class in exchanges:
        await test_exchange(exchange_class, timeout=30)
        await asyncio.sleep(2)
    
    print(f"\n{'='*50}")
    print("All tests completed")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
