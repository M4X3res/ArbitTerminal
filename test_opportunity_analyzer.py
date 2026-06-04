"""Unit tests для OpportunityAnalyzer"""
import unittest
from datetime import datetime, timedelta
from models import ArbitragePair, MarketData
from opportunity_analyzer import OpportunityAnalyzer, OpportunityAnalysis


class TestOpportunityAnalyzer(unittest.TestCase):
    """Тесты для Net Edge Strategy"""
    
    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.analyzer = OpportunityAnalyzer()
        
        # Базовая возможность
        self.base_opportunity = ArbitragePair(
            symbol="BTC/USDT",
            exchange_long="mexc",
            exchange_short="gate",
            price_long=50000.0,
            price_short=50300.0,
            spread=0.6,  # 0.6% gross spread
            funding_diff=0.0001,
            data_long=MarketData(
                exchange="mexc",
                symbol="BTC/USDT",
                bid=50000.0,
                ask=50010.0,  # 0.02% bid-ask spread
                funding_rate=0.0001,
                timestamp=datetime.now()
            ),
            data_short=MarketData(
                exchange="gate",
                symbol="BTC/USDT",
                bid=50300.0,
                ask=50310.0,  # 0.02% bid-ask spread
                funding_rate=0.0002,
                timestamp=datetime.now()
            )
        )
    
    def test_approved_good_opportunity(self):
        """Тест: хорошая возможность должна быть одобрена"""
        analysis = self.analyzer.analyze(self.base_opportunity)
        
        self.assertTrue(analysis.approved, f"Should be approved: {analysis.reason}")
        self.assertGreater(analysis.net_edge_pct, self.analyzer.MIN_NET_EDGE)
        self.assertIn("Approved", analysis.reason)
    
    def test_rejected_low_gross_spread(self):
        """Тест: низкий gross spread отклоняется"""
        opp = self.base_opportunity
        opp.spread = 0.2  # Ниже MIN_GROSS_SPREAD (0.35)
        
        analysis = self.analyzer.analyze(opp)
        
        self.assertFalse(analysis.approved)
        self.assertIn("Gross spread too low", analysis.reason)
    
    def test_rejected_high_gross_spread_anomaly(self):
        """Тест: аномально высокий spread отклоняется"""
        opp = self.base_opportunity
        opp.spread = 3.0  # Выше MAX_GROSS_SPREAD (2.5)
        
        analysis = self.analyzer.analyze(opp)
        
        self.assertFalse(analysis.approved)
        self.assertIn("anomaly", analysis.reason)
    
    def test_rejected_wide_bid_ask_long(self):
        """Тест: широкий bid-ask на long leg отклоняется"""
        opp = self.base_opportunity
        # Широкий spread на long exchange
        opp.data_long.bid = 50000.0
        opp.data_long.ask = 50100.0  # 0.2% spread > MAX_BID_ASK_SPREAD_PER_LEG (0.12)
        
        analysis = self.analyzer.analyze(opp)
        
        self.assertFalse(analysis.approved)
        self.assertIn("Bid-ask too wide on long leg", analysis.reason)
    
    def test_rejected_wide_bid_ask_short(self):
        """Тест: широкий bid-ask на short leg отклоняется"""
        opp = self.base_opportunity
        # Широкий spread на short exchange
        opp.data_short.bid = 50300.0
        opp.data_short.ask = 50400.0  # 0.2% spread > MAX_BID_ASK_SPREAD_PER_LEG (0.12)
        
        analysis = self.analyzer.analyze(opp)
        
        self.assertFalse(analysis.approved)
        self.assertIn("Bid-ask too wide on short leg", analysis.reason)
    
    def test_rejected_stale_data(self):
        """Тест: устаревшие данные отклоняются"""
        opp = self.base_opportunity
        # Данные старше MAX_DATA_AGE_MS (1000ms = 1 сек)
        opp.data_long.timestamp = datetime.now() - timedelta(seconds=2)
        
        analysis = self.analyzer.analyze(opp)
        
        self.assertFalse(analysis.approved)
        self.assertIn("Stale data", analysis.reason)
    
    def test_rejected_insufficient_net_edge(self):
        """Тест: недостаточный net edge после издержек отклоняется"""
        opp = self.base_opportunity
        # Маленький gross spread, после издержек net edge будет отрицательным
        opp.spread = 0.40  # Едва выше MIN_GROSS_SPREAD
        
        # Широкие bid-ask spreads (но в пределах лимита)
        opp.data_long.bid = 50000.0
        opp.data_long.ask = 50050.0  # 0.1% spread
        opp.data_short.bid = 50300.0
        opp.data_short.ask = 50350.0  # 0.1% spread
        
        analysis = self.analyzer.analyze(opp)
        
        # После вычета fees (0.2%), slippage (0.08%), bid-ask (0.2%), funding (0.01%)
        # Net edge = 0.40 - 0.2 - 0.08 - 0.2 - 0.01 = -0.09%
        self.assertFalse(analysis.approved)
        self.assertIn("Net edge insufficient", analysis.reason)
        self.assertLess(analysis.net_edge_pct, self.analyzer.MIN_NET_EDGE)
    
    def test_net_edge_calculation(self):
        """Тест: правильность расчёта net edge"""
        analysis = self.analyzer.analyze(self.base_opportunity)
        
        # Проверяем компоненты
        self.assertAlmostEqual(analysis.gross_spread_pct, 0.6, places=2)
        self.assertAlmostEqual(analysis.estimated_fees_pct, 0.2, places=2)  # 0.05 * 4
        self.assertAlmostEqual(analysis.estimated_slippage_pct, 0.08, places=2)  # 0.02 * 4
        
        # Net edge = gross - fees - slippage - bid_ask_long - bid_ask_short - funding
        # = 0.6 - 0.2 - 0.08 - 0.02 - 0.02 - ~0.01 ≈ 0.27%
        self.assertGreater(analysis.net_edge_pct, 0.2)
        self.assertLess(analysis.net_edge_pct, 0.4)
    
    def test_data_age_calculation(self):
        """Тест: расчёт возраста данных"""
        opp = self.base_opportunity
        opp.data_long.timestamp = datetime.now() - timedelta(milliseconds=500)
        opp.data_short.timestamp = datetime.now() - timedelta(milliseconds=800)
        
        analysis = self.analyzer.analyze(opp)
        
        # Должен быть максимум из двух
        self.assertGreater(analysis.data_age_ms, 700)
        self.assertLess(analysis.data_age_ms, 900)
    
    def test_edge_case_no_market_data(self):
        """Тест: обработка отсутствующих рыночных данных"""
        opp = self.base_opportunity
        opp.data_long = None
        opp.data_short = None
        
        analysis = self.analyzer.analyze(opp)
        
        # Должен работать без падения
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.bid_ask_spread_long_pct, 0.0)
        self.assertEqual(analysis.bid_ask_spread_short_pct, 0.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
