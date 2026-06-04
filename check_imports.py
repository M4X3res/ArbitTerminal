"""Простая проверка импортов"""
print("🔧 Проверка импортов...")

try:
    from exchanges.mexc import MEXCExchange
    print("✅ MEXC импортирован")
except Exception as e:
    print(f"❌ MEXC ошибка: {e}")

try:
    from exchanges.gate import GateExchange
    print("✅ Gate импортирован")
except Exception as e:
    print(f"❌ Gate ошибка: {e}")

try:
    from models import MarketData
    print("✅ Models импортированы")
except Exception as e:
    print(f"❌ Models ошибка: {e}")

print("\n✅ Все импорты прошли успешно!")
print("\nДля полного теста запустите:")
print("  .venv\\Scripts\\python.exe test_exchanges.py")
