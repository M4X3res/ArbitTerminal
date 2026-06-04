"""Market Data Engine — получение данных через WebSocket"""
import asyncio
from typing import Dict, List, Callable
from collections import defaultdict
from models import MarketData

# Импорт конфигурации
try:
    from performance_config import SYMBOLS_PER_EXCHANGE
except ImportError:
    SYMBOLS_PER_EXCHANGE = 10


class MarketDataEngine:
    """Управление потоками рыночных данных"""
    
    def __init__(self, exchanges: Dict):
        self.exchanges = exchanges
        self.market_data: Dict[str, Dict[str, MarketData]] = defaultdict(dict)
        self.subscribed_symbols = []
        self.data_queue = asyncio.Queue(maxsize=1000)
        self.listeners: List[Callable] = []
        self._tasks = []
    
    async def get_common_symbols(self, limit=None) -> Dict:
        """Получить общие пары символов между биржами (попарно)"""
        print("\n🔍 Поиск общих торговых пар попарно...")
        
        # Параллельно получаем инструменты со всех бирж
        tasks = [exchange.get_instruments() for exchange in self.exchanges.values()]
        all_instruments = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Собираем инструменты по биржам
        exchange_symbols = {}
        for idx, (name, exchange) in enumerate(self.exchanges.items()):
            instruments = all_instruments[idx]
            if isinstance(instruments, Exception):
                print(f"   ⚠️  {name}: ошибка получения инструментов")
                continue
            
            print(f"   ✓ {name}: {len(instruments)} инструментов")
            
            # Нормализуем символы
            normalized = set()
            for symbol in instruments:
                norm = symbol.replace("-", "").replace("_", "").upper()
                normalized.add(norm)
            
            exchange_symbols[name] = normalized
        
        # Находим пересечения попарно
        exchange_names = list(exchange_symbols.keys())
        pairwise_common = {}
        
        for i, ex1 in enumerate(exchange_names):
            for ex2 in exchange_names[i+1:]:
                common = exchange_symbols[ex1] & exchange_symbols[ex2]
                pair_key = f"{ex1}-{ex2}"
                pairwise_common[pair_key] = list(common)
                print(f"   📊 {ex1} ↔ {ex2}: {len(common)} общих пар")
        
        # Также найдем общие для всех (для совместимости)
        all_common = set.intersection(*exchange_symbols.values()) if exchange_symbols else set()
        pairwise_common['all'] = list(all_common)
        print(f"   📊 Все биржи: {len(all_common)} общих пар")
        
        # Применяем лимит к каждой паре
        if limit:
            pairwise_common = {k: v[:limit] for k, v in pairwise_common.items()}
        
        return pairwise_common
    
    async def subscribe_all(self, symbols: List[str]):
        """Подписаться на символы на всех биржах и запустить фоновые слушатели"""
        self.subscribed_symbols = symbols
        
        print(f"\n📡 Подписка на {len(symbols)} символов...")
        
        # Параллельно получаем инструменты и подписываемся
        subscribe_tasks = []
        
        for name, exchange in self.exchanges.items():
            task = self._subscribe_exchange(name, exchange, symbols)
            subscribe_tasks.append(task)
        
        await asyncio.gather(*subscribe_tasks, return_exceptions=True)
        
        print("   ✓ Все подписки активны\n")
    
    async def _subscribe_exchange(self, name: str, exchange, symbols: List[str]):
        """Подписка на конкретную биржу"""
        try:
            instruments = await exchange.get_instruments()
            
            # Найти соответствующие символы
            exchange_symbols = []
            for symbol in symbols:
                for inst in instruments:
                    normalized = inst.replace("-", "").replace("_", "").upper()
                    if normalized == symbol:
                        exchange_symbols.append(inst)
                        break
            
            if exchange_symbols:
                # Ограничиваем количество символов
                exchange_symbols = exchange_symbols[:SYMBOLS_PER_EXCHANGE]
                
                await exchange.subscribe_orderbook(exchange_symbols)
                await exchange.subscribe_funding_rate(exchange_symbols)
                
                print(f"   ✓ {name}: подписка на {len(exchange_symbols)} пар")
                
                # Запускаем фоновый слушатель
                task = asyncio.create_task(self._listen_exchange(name, exchange))
                self._tasks.append(task)
        except Exception as e:
            print(f"   ✗ {name}: ошибка подписки - {e}")
    
    async def _listen_exchange(self, name: str, exchange):
        """Непрерывное чтение накопленных данных с биржи"""
        while True:
            try:
                await asyncio.sleep(0.1)  # Опрос каждые 100ms
                
                # Читаем все доступные символы из локального хранилища
                for symbol in list(exchange.orderbooks.keys()):
                    if symbol in exchange.funding_rates:
                        # Получаем готовые данные
                        data = await exchange.get_market_data(symbol)
                        
                        if data is None:
                            continue
                        
                        normalized = data.symbol.replace("-", "").replace("_", "").replace("/", "").upper()
                        self.market_data[name][normalized] = data
                        
                        # Отправляем в очередь для обработки
                        try:
                            self.data_queue.put_nowait(data)
                        except asyncio.QueueFull:
                            pass
                        
                        # Уведомляем слушателей
                        for listener in self.listeners:
                            asyncio.create_task(listener(data))
                    
            except Exception as e:
                print(f"   ⚠️  {name}: {e}")
                await asyncio.sleep(1)
                
                # Автоматическое переподключение
                try:
                    await exchange.connect_ws()
                except:
                    pass
                
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
    
    def add_listener(self, callback: Callable):
        """Добавить слушателя обновлений"""
        self.listeners.append(callback)
    
    def get_latest_data(self) -> Dict[str, Dict[str, MarketData]]:
        """Получить последние данные (синхронно)"""
        return dict(self.market_data)
    
    async def stop(self):
        """Остановить все фоновые задачи"""
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
