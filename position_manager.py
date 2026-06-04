"""Position Manager — управление открытыми позициями"""
import asyncio
from typing import Dict, List
from datetime import datetime
from models import Trade, MarketData
from strategy_selector import StrategySelector


class PositionManager:
    """Автоматическое управление открытыми позициями"""
    
    def __init__(self, trading_engine, strategy_selector, telegram_logger, risk_manager=None):
        self.trading_engine = trading_engine
        self.strategy_selector = strategy_selector
        self.telegram = telegram_logger
        self.risk_manager = risk_manager  # Опционально для обновления баланса
        self.positions: Dict[str, Trade] = {}
        self.total_pnl = 0.0
        self.closed_positions = []
    
    def register_position(self, trade: Trade):
        """Регистрация новой позиции"""
        self.positions[trade.pair_id] = trade
        print(f"   ✅ Позиция зарегистрирована: {trade.symbol} ({trade.pair_id[:8]})")
    
    async def monitor_positions(self, market_data: Dict[str, Dict[str, MarketData]]):
        """Мониторинг и автоматическое закрытие позиций"""
        if not self.positions:
            return
        
        for pair_id, trade in list(self.positions.items()):
            should_close, reason = self.strategy_selector.should_close(trade, market_data)
            
            if should_close:
                await self.close_position(pair_id, market_data, reason)
    
    async def close_position(self, pair_id: str, market_data: Dict, reason: str):
        """Закрытие позиции"""
        if pair_id not in self.positions:
            return
        
        trade = self.positions[pair_id]
        
        print(f"\n🔄 Закрытие позиции: {trade.symbol}")
        print(f"   Причина: {reason}")
        
        # Закрываем на биржах
        success = await self.trading_engine.close_position(pair_id)
        
        if success:
            # Расчёт PnL
            long_data = market_data.get(trade.exchange_long, {}).get(trade.symbol)
            short_data = market_data.get(trade.exchange_short, {}).get(trade.symbol)
            
            if long_data and short_data:
                # PnL в процентах
                pnl_long = (long_data.bid - trade.entry_price_long) / trade.entry_price_long * 100
                pnl_short = (trade.entry_price_short - short_data.ask) / trade.entry_price_short * 100
                pnl_pct = pnl_long + pnl_short
                
                # PnL в USD
                pnl_usd = pnl_pct * trade.position_size_usd / 100
                
                # Текущий спред
                current_spread = (short_data.bid - long_data.ask) / long_data.ask * 100
                
                # Обновляем трейд
                trade.close_spread = current_spread
                trade.pnl = pnl_usd
                trade.status = 'closed'
                trade.close_time = datetime.now()
                
                hold_time = (trade.close_time - trade.open_time).total_seconds()
                
                self.total_pnl += pnl_usd
                self.closed_positions.append(trade)
                
                # Обновляем баланс в risk manager
                if self.risk_manager:
                    self.risk_manager.update_balance(pnl_usd)
                    # Удаляем позицию из risk manager
                    self.risk_manager.unregister_position(trade.symbol, trade.exchange_long, trade.exchange_short)
                
                # Вывод
                emoji = "✅" if pnl_usd > 0 else "❌"
                print(f"   {emoji} PnL: {pnl_usd:+.2f} USD ({pnl_pct:+.3f}%)")
                print(f"   ⏱️  Время: {hold_time:.1f}s")
                print(f"   💹 Спред: {trade.entry_spread:.3f}% → {current_spread:.3f}%")
                
                # Telegram
                await self.telegram.log_position_closed(
                    symbol=trade.symbol,
                    spread_open=trade.entry_spread,
                    spread_close=current_spread,
                    pnl=pnl_usd,
                    hold_time=hold_time,
                    reason=reason
                )
            
            # Удаляем из активных
            del self.positions[pair_id]
    
    def get_statistics(self) -> Dict:
        """Статистика по позициям"""
        if not self.closed_positions:
            return {
                "total_trades": 0,
                "profitable": 0,
                "total_pnl": 0,
                "win_rate": 0,
                "avg_hold_time": 0
            }
        
        profitable = sum(1 for t in self.closed_positions if t.pnl > 0)
        avg_hold = sum(
            (t.close_time - t.open_time).total_seconds() 
            for t in self.closed_positions
        ) / len(self.closed_positions)
        
        return {
            "total_trades": len(self.closed_positions),
            "profitable": profitable,
            "total_pnl": self.total_pnl,
            "win_rate": profitable / len(self.closed_positions) * 100,
            "avg_hold_time": avg_hold
        }
