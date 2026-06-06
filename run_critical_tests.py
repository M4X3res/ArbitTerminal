"""Простой тест-раннер для критических функций без pytest"""
import sys
sys.path.insert(0, 'C:\\Users\\Maxtr\\PycharmProjects\\ArbitTerminal')

from order_utils import calculate_order_qty, map_order_side
from pnl_calculator import calculate_net_pnl, calculate_pnl_from_spread
from risk_manager import RiskManager


def test_qty_btc():
    """Тест расчёта количества для BTC"""
    qty = calculate_order_qty('BTCUSDT', position_size_usd=100, price=63000, leverage=5)
    assert abs(qty - 0.00793) < 0.0001, f"Expected ~0.00793, got {qty}"
    print("✅ test_qty_btc passed")


def test_qty_not_raw_usd():
    """КРИТИЧЕСКИЙ: qty не должен равняться сырому USD"""
    qty = calculate_order_qty('BTCUSDT', position_size_usd=100, price=63000, leverage=5)
    assert qty != 100, "CRITICAL: qty must not equal raw USD amount"
    print("✅ test_qty_not_raw_usd passed")


def test_bybit_side_mapping():
    """Тест маппинга сторон для Bybit"""
    assert map_order_side('bybit', 'LONG',  is_close=False) == 'Buy'
    assert map_order_side('bybit', 'SHORT', is_close=False) == 'Sell'
    assert map_order_side('bybit', 'LONG',  is_close=True)  == 'Sell'
    assert map_order_side('bybit', 'SHORT', is_close=True)  == 'Buy'
    print("✅ test_bybit_side_mapping passed")


def test_mexc_side_mapping():
    """Тест маппинга сторон для MEXC"""
    assert map_order_side('mexc', 'LONG',  is_close=False) == 1
    assert map_order_side('mexc', 'SHORT', is_close=False) == 3
    assert map_order_side('mexc', 'LONG',  is_close=True)  == 4
    assert map_order_side('mexc', 'SHORT', is_close=True)  == 2
    print("✅ test_mexc_side_mapping passed")


def test_gate_side_mapping():
    """Тест маппинга сторон для Gate"""
    assert map_order_side('gate', 'LONG',  is_close=False) == 1
    assert map_order_side('gate', 'SHORT', is_close=False) == -1
    assert map_order_side('gate', 'LONG',  is_close=True)  == -1
    assert map_order_side('gate', 'SHORT', is_close=True)  == 1
    print("✅ test_gate_side_mapping passed")


def test_calculate_net_pnl_profit():
    """Тест расчёта PnL для прибыльной позиции"""
    result = calculate_net_pnl(
        entry_price_long=100,
        entry_price_short=101,
        current_price_long=101,
        current_price_short=100,
        position_size_usd=100,
        leverage=5,
        fee_rate=0.0005,
    )
    
    assert abs(result['gross_pct'] - 2.0) < 0.01
    assert abs(result['gross_usd'] - 10.0) < 0.1
    assert abs(result['fees_usd'] - 1.0) < 0.01
    assert abs(result['net_usd'] - 9.0) < 0.1
    print("✅ test_calculate_net_pnl_profit passed")


def test_fees_are_subtracted():
    """КРИТИЧЕСКИЙ: комиссии должны вычитаться из прибыли"""
    result = calculate_net_pnl(
        entry_price_long=100,
        entry_price_short=100,
        current_price_long=100,
        current_price_short=100,
        position_size_usd=100,
        leverage=5,
        fee_rate=0.0005,
    )
    
    assert result['gross_usd'] == 0
    assert result['fees_usd'] > 0
    assert result['net_usd'] < 0
    print("✅ test_fees_are_subtracted passed")


def test_no_duplicate_positions():
    """КРИТИЧЕСКИЙ: не должно быть дублирования позиций"""
    rm = RiskManager(initial_balance=1000)
    
    rm.register_position('pair1', 'BTCUSDT', 'mexc', 'gate')
    rm.register_position('pair2', 'BTCUSDT', 'bybit', 'gate')
    
    assert rm.get_open_count() == 2, "Should have 2 positions"
    
    rm.unregister_position('pair1')
    
    assert rm.get_open_count() == 1, "Should have 1 position left"
    assert 'pair2' in rm.open_positions, "pair2 should still exist"
    assert 'pair1' not in rm.open_positions, "pair1 should be removed"
    print("✅ test_no_duplicate_positions passed")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("   UNIT TESTS — КРИТИЧЕСКИЕ ФУНКЦИИ")
    print("="*70 + "\n")
    
    tests = [
        test_qty_btc,
        test_qty_not_raw_usd,
        test_bybit_side_mapping,
        test_mexc_side_mapping,
        test_gate_side_mapping,
        test_calculate_net_pnl_profit,
        test_fees_are_subtracted,
        test_no_duplicate_positions,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("\n" + "="*70)
    print(f"   Результаты: {passed} passed, {failed} failed")
    print("="*70)
    
    sys.exit(0 if failed == 0 else 1)
