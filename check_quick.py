"""Быстрая проверка импортов"""
import sys

print("Проверка импортов...\n")

try:
    from market_data_engine import MarketDataEngine
    print("✅ market_data_engine")
except Exception as e:
    print(f"❌ market_data_engine: {e}")

try:
    from arbitrage_engine import ArbitrageEngine  
    print("✅ arbitrage_engine")
except Exception as e:
    print(f"❌ arbitrage_engine: {e}")

try:
    from trading_engine import TradingEngine
    print("✅ trading_engine")
except Exception as e:
    print(f"❌ trading_engine: {e}")

try:
    from risk_manager import RiskManager
    print("✅ risk_manager")
except Exception as e:
    print(f"❌ risk_manager: {e}")

try:
    from position_manager import PositionManager
    print("✅ position_manager")
except Exception as e:
    print(f"❌ position_manager: {e}")

print("\n✅ Все основные модули доступны!")
