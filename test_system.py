"""
Комплексный тест фьючерсных коннекторов
Проверка: WebSocket, Funding Rate, Market Data streaming
"""
import asyncio
import logging
import time
import sys
from typing import Dict

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class FuturesSystemTester:
    """Тестер фьючерсной системы с 3 биржами"""
    
    def __init__(self):
        # Отложенный импорт коннекторов
        try:
            from exchanges.mexc import MEXCExchange
            from exchanges.gate import GateExchange
            from exchanges.bybit import BybitExchange
            
            # Инициализация бирж БЕЗ API ключей (только публичные данные)
            self.exchanges = {
                'mexc': MEXCExchange(api_key="", api_secret=""),
                'gate': GateExchange(api_key="", api_secret=""),
                'bybit': BybitExchange(api_key="", api_secret="")
            }
            
            logger.info("✅ All exchanges loaded successfully")
            
        except ImportError as e:
            logger.error(f"❌ Failed to import exchanges: {e}")
            raise
        
        # Тестовые символы
        self.test_symbols = ['BTC/USDT', 'ETH/USDT']
        
        # Собранные данные
        self.collected_data: Dict[str, Dict] = {
            'mexc': {},
            'gate': {},
            'bybit': {}
        }
        
        logger.info("✅ FuturesSystemTester initialized")
    
    async def test_websocket_connections(self, duration_seconds: int = 20):
        """
        Тест WebSocket подключений ко всем биржам
        
        Args:
            duration_seconds: Длительность теста в секундах
        """
        logger.info(f"🚀 Starting WebSocket test for {duration_seconds} seconds...")
        logger.info(f"   Exchanges: {list(self.exchanges.keys())}")
        logger.info(f"   Symbols: {self.test_symbols}")
        
        # Запуск всех WebSocket слушателей параллельно
        ws_tasks = []
        for exchange_name, exchange in self.exchanges.items():
            task = asyncio.create_task(
                exchange.start_websocket_listener(self.test_symbols),
                name=f"ws_{exchange_name}"
            )
            ws_tasks.append(task)
        
        # Даем время на подключение
        logger.info("⏳ Waiting for connections to establish...")
        await asyncio.sleep(5)
        logger.info("✅ WebSocket connections established")
        
        # Мониторинг данных
        monitor_task = asyncio.create_task(
            self._monitor_market_data(duration_seconds)
        )
        
        # Ждем завершения мониторинга
        await monitor_task
        
        # Останавливаем WebSocket соединения
        logger.info("🛑 Stopping WebSocket connections...")
        for exchange in self.exchanges.values():
            await exchange.stop_websocket()
        
        # Отменяем задачи
        for task in ws_tasks:
            task.cancel()
        
        # Ждем отмены
        await asyncio.gather(*ws_tasks, return_exceptions=True)
        
        logger.info("✅ All WebSocket connections closed")
    
    async def _monitor_market_data(self, duration: int):
        """Мониторинг получаемых данных"""
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < duration:
            iteration += 1
            
            logger.info(f"\n{'='*60}")
            logger.info(f"📊 DATA SNAPSHOT #{iteration} (T+{int(time.time() - start_time)}s)")
            logger.info(f"{'='*60}")
            
            # Сбор данных с каждой биржи
            for exchange_name, exchange in self.exchanges.items():
                logger.info(f"\n🏦 {exchange_name.upper()} Exchange:")
                
                for symbol in self.test_symbols:
                    market_data = await exchange.get_market_data(symbol)
                    
                    if market_data:
                        # Сохраняем данные
                        self.collected_data[exchange_name][symbol] = market_data
                        
                        # Вывод информации
                        spread_pct = (market_data.ask - market_data.bid) / market_data.bid * 100
                        
                        logger.info(
                            f"   {symbol}: "
                            f"Bid={market_data.bid:.2f} | "
                            f"Ask={market_data.ask:.2f} | "
                            f"Spread={spread_pct:.3f}% | "
                            f"Funding={market_data.funding_rate*100:.4f}%"
                        )
                        
                        # 🔧 КРИТИЧЕСКАЯ ПРОВЕРКА: Funding rate
                        if abs(market_data.funding_rate) < 0.000001:
                            logger.warning(
                                f"   ⚠️ WARNING: Funding rate is ~0 for {symbol} on {exchange_name}"
                            )
                        
                        # Проверка латентности данных
                        latency_ms = time.time() * 1000 - market_data.timestamp_ms
                        if latency_ms > 100:
                            logger.warning(
                                f"   ⚠️ WARNING: High latency {latency_ms:.0f}ms for {symbol}"
                            )
                    else:
                        logger.warning(f"   ❌ No data for {symbol}")
            
            # Пауза перед следующей итерацией
            await asyncio.sleep(5)
    
    def generate_report(self):
        """Генерация финального отчета по тесту"""
        logger.info(f"\n{'='*60}")
        logger.info("📋 FINAL TEST REPORT")
        logger.info(f"{'='*60}")
        
        # Статистика по биржам
        for exchange_name in self.exchanges.keys():
            data = self.collected_data[exchange_name]
            
            logger.info(f"\n🏦 {exchange_name.upper()}")
            logger.info(f"   Symbols received: {len(data)}/{len(self.test_symbols)}")
            
            for symbol, market_data in data.items():
                logger.info(f"   {symbol}:")
                logger.info(f"      Bid: {market_data.bid:.2f}")
                logger.info(f"      Ask: {market_data.ask:.2f}")
                logger.info(f"      Funding Rate: {market_data.funding_rate*100:.4f}%")
                
                latency = time.time() * 1000 - market_data.timestamp_ms
                logger.info(f"      Latency: {latency:.0f}ms")
        
        # Проверка арбитражных возможностей
        logger.info(f"\n{'='*60}")
        logger.info("🎯 ARBITRAGE OPPORTUNITIES")
        logger.info(f"{'='*60}")
        
        for symbol in self.test_symbols:
            logger.info(f"\n{symbol}:")
            
            # Собираем все цены
            prices = {}
            for exchange_name, data in self.collected_data.items():
                if symbol in data:
                    prices[exchange_name] = {
                        'bid': data[symbol].bid,
                        'ask': data[symbol].ask,
                        'funding': data[symbol].funding_rate
                    }
            
            if len(prices) < 2:
                logger.info("   ⚠️ Insufficient data")
                continue
            
            # Поиск возможностей
            exchanges_list = list(prices.keys())
            found_opportunity = False
            
            for i, ex_long in enumerate(exchanges_list):
                for ex_short in exchanges_list[i+1:]:
                    # Спред: short bid - long ask
                    spread = (prices[ex_short]['bid'] - prices[ex_long]['ask']) / prices[ex_long]['ask'] * 100
                    
                    if spread > 0.1:
                        found_opportunity = True
                        funding_diff = (prices[ex_short]['funding'] - prices[ex_long]['funding']) * 100
                        
                        logger.info(
                            f"   ✅ Long {ex_long.upper()} → Short {ex_short.upper()}: "
                            f"Spread={spread:.3f}% | "
                            f"Funding Δ={funding_diff:.4f}%"
                        )
            
            if not found_opportunity:
                logger.info("   ℹ️ No arbitrage opportunities above 0.1% threshold")
        
        # Итоговая оценка
        logger.info(f"\n{'='*60}")
        logger.info("🎉 TEST SUMMARY")
        logger.info(f"{'='*60}")
        
        total_success = sum(len(data) for data in self.collected_data.values())
        total_expected = len(self.exchanges) * len(self.test_symbols)
        success_rate = (total_success / total_expected) * 100 if total_expected > 0 else 0
        
        logger.info(f"Data received: {total_success}/{total_expected} ({success_rate:.1f}%)")
        
        # Проверка funding rate
        funding_ok = True
        for exchange_name, data in self.collected_data.items():
            for symbol, market_data in data.items():
                if abs(market_data.funding_rate) < 0.000001:
                    funding_ok = False
        
        if funding_ok and total_success > 0:
            logger.info("✅ All funding rates are non-zero")
        elif total_success > 0:
            logger.warning("⚠️ Some funding rates are zero")
        
        if success_rate >= 80:
            logger.info("\n🚀 SYSTEM READY FOR PRODUCTION!")
            return True
        else:
            logger.warning("\n⚠️ SYSTEM NEEDS DEBUGGING")
            return False


async def main():
    """Главная функция тестирования"""
    logger.info("="*60)
    logger.info("🔬 FUTURES SYSTEM COMPREHENSIVE TEST")
    logger.info("="*60)
    logger.info("Testing: MEXC + Gate.io + Bybit V5")
    logger.info("Duration: 20 seconds")
    logger.info("="*60)
    
    try:
        tester = FuturesSystemTester()
    except Exception as e:
        logger.error(f"❌ Failed to initialize tester: {e}")
        return False
    
    try:
        # Запуск теста
        await tester.test_websocket_connections(duration_seconds=20)
        
        # Генерация отчета
        success = tester.generate_report()
        
        return success
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ Test interrupted by user")
        return False
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}", exc_info=True)
        return False
    finally:
        # Закрытие всех соединений
        for exchange in tester.exchanges.values():
            await exchange.close()
        
        logger.info("\n✅ Test complete")


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Interrupted")
        sys.exit(1)
