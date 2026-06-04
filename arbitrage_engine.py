"""Arbitrage Engine — расчёт спредов и поиск возможностей"""
from typing import List, Dict
from models import MarketData, ArbitragePair
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor


class ArbitrageEngine:
    """Анализ арбитражных возможностей"""
    
    def __init__(self, max_workers: int = 4):
        self.spread_history = []
        self.stats = {
            "total_opportunities": 0,
            "spreads": []
        }
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
    
    def calculate_effective_spread(self, long_data: MarketData, short_data: MarketData) -> float:
        """Расчёт эффективного спреда с учётом funding rate"""
        # Спред: цена где покупаем - цена где продаём
        raw_spread = (short_data.bid - long_data.ask) / long_data.ask * 100
        
        # Разница funding rates (платим на шорт, получаем на лонг)
        funding_diff = short_data.funding_rate - long_data.funding_rate
        
        # Эффективный спред
        effective = raw_spread - funding_diff * 100
        
        return effective
    
    def _check_pair_batch(self, pairs_batch, threshold):
        """Проверка батча пар (для параллелизма)"""
        opportunities = []
        
        for ex_long, ex_short, symbol, data_long, data_short in pairs_batch:
            # Стратегия 1
            spread1 = self.calculate_effective_spread(data_long, data_short)
            if spread1 > threshold:
                opp = ArbitragePair(
                    exchange_long=ex_long, exchange_short=ex_short,
                    symbol=symbol, spread=spread1,
                    funding_diff=data_short.funding_rate - data_long.funding_rate,
                    price_long=data_long.ask, price_short=data_short.bid,
                    timestamp=datetime.now()
                )
                opportunities.append(opp)
                self.stats["spreads"].append(spread1)
            
            # Стратегия 2
            spread2 = self.calculate_effective_spread(data_short, data_long)
            if spread2 > threshold:
                opp = ArbitragePair(
                    exchange_long=ex_short, exchange_short=ex_long,
                    symbol=symbol, spread=spread2,
                    funding_diff=data_long.funding_rate - data_short.funding_rate,
                    price_long=data_short.ask, price_short=data_long.bid,
                    timestamp=datetime.now()
                )
                opportunities.append(opp)
                self.stats["spreads"].append(spread2)
        
        return opportunities
    
    def find_opportunities_parallel(self, market_data: Dict[str, Dict[str, MarketData]], threshold: float, batch_size: int = 50) -> List[ArbitragePair]:
        """Параллельный поиск возможностей (батчинг)"""
        exchanges = list(market_data.keys())
        
        # Собираем все пары
        all_pairs = []
        for i, ex_long in enumerate(exchanges):
            for ex_short in exchanges[i+1:]:
                symbols_long = set(market_data[ex_long].keys())
                symbols_short = set(market_data[ex_short].keys())
                common_symbols = symbols_long & symbols_short
                
                for symbol in common_symbols:
                    data_long = market_data[ex_long][symbol]
                    data_short = market_data[ex_short][symbol]
                    all_pairs.append((ex_long, ex_short, symbol, data_long, data_short))
        
        # Разбиваем на батчи
        batches = [all_pairs[i:i+batch_size] for i in range(0, len(all_pairs), batch_size)]
        
        # Параллельная обработка батчей
        futures = [self.executor.submit(self._check_pair_batch, batch, threshold) for batch in batches]
        
        # Собираем результаты
        opportunities = []
        for future in futures:
            opportunities.extend(future.result())
        
        self.stats["total_opportunities"] += len(opportunities)
        opportunities.sort(key=lambda x: x.spread, reverse=True)
        
        return opportunities
    
    def find_opportunities(self, market_data: Dict[str, Dict[str, MarketData]], threshold: float) -> List[ArbitragePair]:
        """Поиск арбитражных возможностей (последовательная версия для совместимости)"""
        opportunities = []
        exchanges = list(market_data.keys())
        
        # Собираем все комбинации для параллельной обработки
        pairs_to_check = []
        
        for i, ex_long in enumerate(exchanges):
            for ex_short in exchanges[i+1:]:
                symbols_long = set(market_data[ex_long].keys())
                symbols_short = set(market_data[ex_short].keys())
                common_symbols = symbols_long & symbols_short
                
                for symbol in common_symbols:
                    data_long = market_data[ex_long][symbol]
                    data_short = market_data[ex_short][symbol]
                    pairs_to_check.append((ex_long, ex_short, symbol, data_long, data_short))
        
        # Параллельно проверяем все пары
        for ex_long, ex_short, symbol, data_long, data_short in pairs_to_check:
            # Стратегия 1: LONG на ex_long, SHORT на ex_short
            spread1 = self.calculate_effective_spread(data_long, data_short)
            
            if spread1 > threshold:
                opp = ArbitragePair(
                    exchange_long=ex_long,
                    exchange_short=ex_short,
                    symbol=symbol,
                    spread=spread1,
                    funding_diff=data_short.funding_rate - data_long.funding_rate,
                    price_long=data_long.ask,
                    price_short=data_short.bid,
                    timestamp=datetime.now()
                )
                opportunities.append(opp)
                self.stats["total_opportunities"] += 1
                self.stats["spreads"].append(spread1)
            
            # Стратегия 2: LONG на ex_short, SHORT на ex_long
            spread2 = self.calculate_effective_spread(data_short, data_long)
            
            if spread2 > threshold:
                opp = ArbitragePair(
                    exchange_long=ex_short,
                    exchange_short=ex_long,
                    symbol=symbol,
                    spread=spread2,
                    funding_diff=data_long.funding_rate - data_short.funding_rate,
                    price_long=data_short.ask,
                    price_short=data_long.bid,
                    timestamp=datetime.now()
                )
                opportunities.append(opp)
                self.stats["total_opportunities"] += 1
                self.stats["spreads"].append(spread2)
        
        # Сортировка по спреду (топ возможности первыми)
        opportunities.sort(key=lambda x: x.spread, reverse=True)
        
        return opportunities
    
    def get_statistics(self) -> Dict:
        """Получить статистику"""
        if not self.stats["spreads"]:
            return {
                "total_opportunities": 0,
                "avg_spread": 0,
                "max_spread": 0
            }
        
        return {
            "total_opportunities": self.stats["total_opportunities"],
            "avg_spread": sum(self.stats["spreads"]) / len(self.stats["spreads"]),
            "max_spread": max(self.stats["spreads"])
        }

