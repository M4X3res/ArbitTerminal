"""
Data Collector — сбор статистики спредов для анализа прибыльности.

Запуск:
    python data_collector.py          # 24 часа
    python data_collector.py 48       # 48 часов
    python data_collector.py 2        # 2 часа (тест)

Результат: data_collection/spreads_YYYYMMDD_HHMMSS.csv
"""
import asyncio
import csv
import sys
import os
import logging
from datetime import datetime, timezone
from pathlib import Path
from collections import defaultdict

from exchanges.mexc import MEXCExchange
from exchanges.gate import GateExchange
from exchanges.normalize import validate_spread

# Настройка логирования аномалий
logging.basicConfig(level=logging.INFO)
anomaly_logger = logging.getLogger("anomaly")
anomaly_handler = logging.FileHandler("data_collection/anomalies.log")
anomaly_handler.setLevel(logging.CRITICAL)
anomaly_logger.addHandler(anomaly_handler)
from exchanges.bybit import BybitExchange
from core.engines.market_data_engine import MarketDataEngine
from core.engines.arbitrage_engine import ArbitrageEngine


# ─── Конфигурация ────────────────────────────────────────────────────────────

OUTPUT_DIR = Path("data_collection")

# Порог для записи: пишем ТОЛЬКО спреды выше этого значения.
# 0 = писать всё (большие файлы), 0.5 = только интересное.
MIN_SPREAD_TO_RECORD = 0.5

# Интервал анализа в секундах
ANALYSIS_INTERVAL = 2.0

# Максимум строк в одном файле (защита от гигантских CSV)
MAX_ROWS_PER_FILE = 500_000


# ─── CSV-схема ────────────────────────────────────────────────────────────────

CSV_FIELDS = [
    "timestamp",          # ISO-8601, UTC
    "exchange_long",      # биржа где LONG
    "exchange_short",     # биржа где SHORT
    "symbol",             # BTCUSDT
    "gross_spread_pct",   # сырой спред, %
    "price_long",         # ask на long-бирже
    "price_short",        # bid на short-бирже
    "funding_long",       # funding rate long-биржи
    "funding_short",      # funding rate short-биржи
    "funding_diff_pct",   # разница funding, %
    "effective_spread_pct",  # спред с учётом funding
]


# ─── Collector ────────────────────────────────────────────────────────────────

class SpreadDataCollector:
    """Собирает и записывает статистику спредов в CSV."""

    def __init__(self, duration_hours: float = 24.0):
        self.duration_seconds = duration_hours * 3600
        self.exchanges = {
            "mexc": MEXCExchange(),
            "gate": GateExchange(),
            "bybit": BybitExchange(),
        }
        self.market_data_engine = MarketDataEngine(self.exchanges)
        self.arbitrage_engine = ArbitrageEngine(max_workers=4)

        OUTPUT_DIR.mkdir(exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.csv_path = OUTPUT_DIR / f"spreads_{ts}.csv"

        self._csv_file = None
        self._writer = None
        self._rows_written = 0
        self._file_index = 0

        # Статистика сессии
        self.stats = defaultdict(lambda: {
            "count": 0,
            "max_spread": 0.0,
            "total_spread": 0.0,
        })

    # ── Файловые операции ────────────────────────────────────────────────────

    def _open_csv(self):
        """Открывает новый CSV-файл для записи."""
        if self._csv_file:
            self._csv_file.close()

        if self._file_index == 0:
            path = self.csv_path
        else:
            stem = self.csv_path.stem
            path = OUTPUT_DIR / f"{stem}_part{self._file_index}.csv"

        self._csv_file = open(path, "w", newline="", encoding="utf-8")
        self._writer = csv.DictWriter(self._csv_file, fieldnames=CSV_FIELDS)
        self._writer.writeheader()
        self._rows_written = 0
        self._file_index += 1
        print(f"   📄 Запись в: {path}")

    def _write_row(self, row: dict):
        """Записывает строку, при необходимости ротирует файл."""
        if self._writer is None or self._rows_written >= MAX_ROWS_PER_FILE:
            self._open_csv()
        self._writer.writerow(row)
        self._rows_written += 1
        # Сбрасываем буфер каждые 100 строк
        if self._rows_written % 100 == 0:
            self._csv_file.flush()

    def _close(self):
        if self._csv_file and not self._csv_file.closed:
            self._csv_file.flush()
            self._csv_file.close()

    # ── Основной цикл ────────────────────────────────────────────────────────

    async def run(self):
        """Запускает сбор данных."""
        print(f"\n{'='*60}")
        print(f"  DATA COLLECTOR — сбор спредов")
        print(f"  Длительность: {self.duration_seconds/3600:.1f} ч")
        print(f"  Min спред для записи: {MIN_SPREAD_TO_RECORD}%")
        print(f"  Интервал: {ANALYSIS_INTERVAL}s")
        print(f"{'='*60}\n")

        # Инициализация бирж
        print("🔌 Инициализация бирж...")
        for name, exchange in self.exchanges.items():
            await exchange.initialize()
            print(f"   ✓ {name}")

        # Подписка на символы
        print("\n🔍 Получение торговых пар...")
        pairwise = await self.market_data_engine.get_common_symbols(limit=None)
        all_symbols = set()
        for k, v in pairwise.items():
            if k != "all":
                all_symbols.update(v)
        print(f"   ✓ {len(all_symbols)} уникальных пар")

        await self.market_data_engine.subscribe_all(list(all_symbols))

        print("\n⏳ Прогрев (10 сек)...")
        await asyncio.sleep(10)

        self._open_csv()

        start = asyncio.get_event_loop().time()
        end = start + self.duration_seconds
        iteration = 0
        total_recorded = 0

        print(f"\n▶  Сбор данных до {datetime.now(timezone.utc).strftime('%H:%M UTC')} + "
              f"{self.duration_seconds/3600:.1f}ч\n")

        try:
            while asyncio.get_event_loop().time() < end:
                iteration += 1
                market_data = self.market_data_engine.get_latest_data()

                if not market_data or not any(market_data.values()):
                    await asyncio.sleep(ANALYSIS_INTERVAL)
                    continue

                # Ищем все возможности без порога (порог применяем при записи)
                opportunities = await asyncio.get_event_loop().run_in_executor(
                    None,
                    self.arbitrage_engine.find_opportunities_parallel,
                    market_data,
                    MIN_SPREAD_TO_RECORD,
                    50,
                )

                now_iso = datetime.now(timezone.utc).isoformat() + "Z"

                for opp in opportunities:
                    # Funding rate уже в %, не нужно умножать на 100!
                    funding_diff = (
                        (opp.data_short.funding_rate - opp.data_long.funding_rate)
                        if opp.data_long and opp.data_short
                        else 0.0
                    )

                    row = {
                        "timestamp": now_iso,
                        "exchange_long": opp.exchange_long,
                        "exchange_short": opp.exchange_short,
                        "symbol": opp.symbol,
                        "gross_spread_pct": round(opp.spread, 4),
                        "price_long": round(opp.price_long, 6),
                        "price_short": round(opp.price_short, 6),
                        "funding_long": round(
                            opp.data_long.funding_rate if opp.data_long else 0, 6
                        ),
                        "funding_short": round(
                            opp.data_short.funding_rate if opp.data_short else 0, 6
                        ),
                        "funding_diff_pct": round(funding_diff, 6),
                        "effective_spread_pct": round(opp.spread - funding_diff, 4),
                    }
                    self._write_row(row)
                    total_recorded += 1

                    # Обновляем статистику
                    key = f"{opp.symbol}|{opp.exchange_long}↔{opp.exchange_short}"
                    s = self.stats[key]
                    s["count"] += 1
                    s["total_spread"] += opp.spread
                    s["max_spread"] = max(s["max_spread"], opp.spread)

                # Прогресс каждые 5 минут
                elapsed = asyncio.get_event_loop().time() - start
                if iteration % int(300 / ANALYSIS_INTERVAL) == 0:
                    self._print_progress(elapsed, total_recorded)

                await asyncio.sleep(ANALYSIS_INTERVAL)

        except KeyboardInterrupt:
            print("\n\n⚠  Остановлено пользователем")
        finally:
            self._close()
            self._print_summary(total_recorded)
            await self._cleanup()

    def _print_progress(self, elapsed: float, total: int):
        pct = elapsed / self.duration_seconds * 100
        top = sorted(
            self.stats.items(),
            key=lambda x: x[1]["max_spread"],
            reverse=True,
        )[:3]
        print(f"[{elapsed/3600:.1f}ч / {pct:.0f}%] Записано: {total}")
        for key, s in top:
            sym, pair = key.split("|")
            avg = s["total_spread"] / s["count"] if s["count"] else 0
            print(f"   {sym} {pair}: max={s['max_spread']:.2f}% avg={avg:.2f}% n={s['count']}")

    def _print_summary(self, total: int):
        print(f"\n{'='*60}")
        print(f"  ИТОГ: {total} записей")
        print(f"  Файл: {self.csv_path}")
        print(f"\n  Топ-10 пар по максимальному спреду:")

        top = sorted(
            self.stats.items(),
            key=lambda x: x[1]["max_spread"],
            reverse=True,
        )[:10]

        for key, s in top:
            sym, pair = key.split("|")
            avg = s["total_spread"] / s["count"] if s["count"] else 0
            print(f"  {sym:12s} {pair:30s}  max={s['max_spread']:5.2f}%  "
                  f"avg={avg:5.2f}%  n={s['count']}")
        print(f"{'='*60}\n")

    async def _cleanup(self):
        for exchange in self.exchanges.values():
            try:
                await exchange.close()
            except Exception:
                pass


# ─── Точка входа ─────────────────────────────────────────────────────────────

async def main():
    hours = float(sys.argv[1]) if len(sys.argv) > 1 else 24.0
    collector = SpreadDataCollector(duration_hours=hours)
    await collector.run()


if __name__ == "__main__":
    asyncio.run(main())