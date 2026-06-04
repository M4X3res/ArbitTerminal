"""Проверка импортов и синтаксиса новых модулей"""
import sys

print("=" * 70)
print("   Проверка Net Edge Strategy модулей")
print("=" * 70)

# 1. Проверка opportunity_config
try:
    from opportunity_config import OPPORTUNITY_CONFIG
    print("\n✅ opportunity_config.py импортирован")
    print(f"   MIN_NET_EDGE: {OPPORTUNITY_CONFIG['MIN_NET_EDGE']}%")
    print(f"   MIN_GROSS_SPREAD: {OPPORTUNITY_CONFIG['MIN_GROSS_SPREAD']}%")
    print(f"   MAX_GROSS_SPREAD: {OPPORTUNITY_CONFIG['MAX_GROSS_SPREAD']}%")
except Exception as e:
    print(f"\n❌ Ошибка импорта opportunity_config: {e}")
    sys.exit(1)

# 2. Проверка opportunity_analyzer
try:
    from opportunity_analyzer import OpportunityAnalyzer, OpportunityAnalysis
    print("\n✅ opportunity_analyzer.py импортирован")
    
    analyzer = OpportunityAnalyzer(config=OPPORTUNITY_CONFIG)
    print(f"   Analyzer создан: {analyzer.__class__.__name__}")
    print(f"   MIN_NET_EDGE: {analyzer.MIN_NET_EDGE}%")
except Exception as e:
    print(f"\n❌ Ошибка импорта opportunity_analyzer: {e}")
    sys.exit(1)

# 3. Проверка обновлённого risk_manager
try:
    from risk_manager import RiskManager
    print("\n✅ risk_manager.py импортирован")
    
    rm = RiskManager(initial_balance=1000)
    print(f"   RiskManager создан, баланс: ${rm.balance}")
    
    # Проверяем что check_opportunity принимает analysis
    import inspect
    sig = inspect.signature(rm.check_opportunity)
    params = list(sig.parameters.keys())
    if 'analysis' in params:
        print(f"   ✅ Параметр 'analysis' добавлен в check_opportunity")
    else:
        print(f"   ⚠️  Параметр 'analysis' НЕ найден в check_opportunity")
except Exception as e:
    print(f"\n❌ Ошибка импорта risk_manager: {e}")
    sys.exit(1)

# 4. Проверка обновлённого main.py
try:
    # Проверяем что main.py компилируется
    import py_compile
    py_compile.compile('main.py', doraise=True)
    print("\n✅ main.py синтаксис корректен")
    
    # Проверяем импорты в main.py
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if 'from opportunity_analyzer import' in content:
            print("   ✅ OpportunityAnalyzer импортирован в main.py")
        if 'from opportunity_config import' in content:
            print("   ✅ OPPORTUNITY_CONFIG импортирован в main.py")
        if 'self.opportunity_analyzer' in content:
            print("   ✅ opportunity_analyzer создан в ArbitrageSystem")
except Exception as e:
    print(f"\n❌ Ошибка проверки main.py: {e}")
    sys.exit(1)

# 5. Проверка test_opportunity_analyzer
try:
    from test_opportunity_analyzer import TestOpportunityAnalyzer
    print("\n✅ test_opportunity_analyzer.py импортирован")
    
    import unittest
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestOpportunityAnalyzer)
    test_count = suite.countTestCases()
    print(f"   Найдено {test_count} тестов")
except Exception as e:
    print(f"\n❌ Ошибка импорта test_opportunity_analyzer: {e}")
    sys.exit(1)

print("\n" + "=" * 70)
print("   ✅ ВСЕ МОДУЛИ ПРОВЕРЕНЫ УСПЕШНО")
print("=" * 70)
print("\n🚀 Готово к запуску:")
print("   1. run_unit_tests.bat - запуск тестов")
print("   2. run_smoke_test.bat - 30 сек demo")
print("   3. main.py - полный мониторинг")
print()
