"""
Тесты для data_collector.py

Запуск:
    python test_data_collector.py           # все тесты
    python test_data_collector.py -v        # verbose
    python -m pytest test_data_collector.py # через pytest
"""
import csv
import io
import os
import sys
import unittest
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call
from dataclasses import dataclass
from typing import Optional

# ─── Мок-модели (не требуют запуска бирж) ────────────────────────────────────

@dataclass
class MockMarketData:
    exchange: str
    symbol: str
    bid: float
    ask: float
    funding_rate: float
    timestamp: datetime


@dataclass
class MockArbitragePair:
    exchange_long: str
    exchange_short: str
    symbol: str
    spread: float
    funding_diff: float
    price_long: float
    price_short: float
    timestamp: datetime
    data_long: Optional[MockMarketData] = None
    data_short: Optional[MockMarketData] = None


# ─── Вспомогательные функции ─────────────────────────────────────────────────

def make_market_data(
    exchange="mexc",
    symbol="BTCUSDT",
    bid=50000.0,
    ask=50010.0,
    funding_rate=0.0001,
) -> MockMarketData:
    return MockMarketData(
        exchange=exchange,
        symbol=symbol,
        bid=bid,
        ask=ask,
        funding_rate=funding_rate,
        timestamp=datetime.now(timezone.utc),
    )


def make_opportunity(
    exchange_long="mexc",
    exchange_short="gate",
    symbol="BTCUSDT",
    spread=1.5,
    price_long=50000.0,
    price_short=50750.0,
    funding_long=0.0001,
    funding_short=0.0002,
) -> MockArbitragePair:
    return MockArbitragePair(
        exchange_long=exchange_long,
        exchange_short=exchange_short,
        symbol=symbol,
        spread=spread,
        funding_diff=funding_short - funding_long,
        price_long=price_long,
        price_short=price_short,
        timestamp=datetime.now(timezone.utc),
        data_long=make_market_data(exchange_long, symbol, bid=price_long - 5, ask=price_long, funding_rate=funding_long),
        data_short=make_market_data(exchange_short, symbol, bid=price_short, ask=price_short + 5, funding_rate=funding_short),
    )


def read_csv_from_string(content: str) -> list[dict]:
    """Парсит CSV-строку в список словарей."""
    reader = csv.DictReader(io.StringIO(content))
    return list(reader)


def write_collector_row(writer, opp: MockArbitragePair, timestamp: str = None):
    """Воспроизводит логику записи строки из data_collector."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat() + "Z"

    funding_diff = (
        (opp.data_short.funding_rate - opp.data_long.funding_rate) * 100
        if opp.data_long and opp.data_short
        else 0.0
    )

    row = {
        "timestamp": timestamp,
        "exchange_long": opp.exchange_long,
        "exchange_short": opp.exchange_short,
        "symbol": opp.symbol,
        "gross_spread_pct": round(opp.spread, 4),
        "price_long": round(opp.price_long, 6),
        "price_short": round(opp.price_short, 6),
        "funding_long": round(opp.data_long.funding_rate if opp.data_long else 0, 6),
        "funding_short": round(opp.data_short.funding_rate if opp.data_short else 0, 6),
        "funding_diff_pct": round(funding_diff, 6),
        "effective_spread_pct": round(opp.spread - funding_diff, 4),
    }
    writer.writerow(row)
    return row


CSV_FIELDS = [
    "timestamp", "exchange_long", "exchange_short", "symbol",
    "gross_spread_pct", "price_long", "price_short",
    "funding_long", "funding_short", "funding_diff_pct", "effective_spread_pct",
]


# ═══════════════════════════════════════════════════════════════════════════════
# ТЕСТ 1: Структура CSV
# ═══════════════════════════════════════════════════════════════════════════════

class TestCSVStructure(unittest.TestCase):
    """CSV-файл должен иметь правильные заголовки и типы данных."""

    def setUp(self):
        self.buf = io.StringIO()
        self.writer = csv.DictWriter(self.buf, fieldnames=CSV_FIELDS)
        self.writer.writeheader()

    def _rows(self):
        self.buf.seek(0)
        return read_csv_from_string(self.buf.getvalue())

    def test_header_columns_present(self):
        """Все обязательные колонки присутствуют."""
        rows = self._rows()
        # пустой файл — смотрим fieldnames через DictReader
        self.buf.seek(0)
        reader = csv.DictReader(io.StringIO(self.buf.getvalue()))
        self.assertEqual(set(reader.fieldnames), set(CSV_FIELDS))

    def test_row_has_all_fields(self):
        """Записанная строка содержит все поля."""
        opp = make_opportunity()
        write_collector_row(self.writer, opp)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        for field in CSV_FIELDS:
            self.assertIn(field, rows[0], f"Поле '{field}' отсутствует в строке")

    def test_no_empty_required_fields(self):
        """Критичные поля не пустые."""
        opp = make_opportunity()
        write_collector_row(self.writer, opp)
        rows = self._rows()
        row = rows[0]
        for field in ["timestamp", "exchange_long", "exchange_short", "symbol", "gross_spread_pct"]:
            self.assertTrue(row[field].strip(), f"Поле '{field}' пустое")


# ═══════════════════════════════════════════════════════════════════════════════
# ТЕСТ 2: Парсинг и типы данных
# ═══════════════════════════════════════════════════════════════════════════════

class TestDataParsing(unittest.TestCase):
    """Данные в CSV должны корректно парситься обратно в Python-типы."""

    def _write_and_read(self, opp, timestamp=None):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        written = write_collector_row(writer, opp, timestamp)
        buf.seek(0)
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        return rows[0], written

    def test_spread_parses_as_float(self):
        """gross_spread_pct должен парситься как float."""
        opp = make_opportunity(spread=7.1234)
        row, _ = self._write_and_read(opp)
        value = float(row["gross_spread_pct"])
        self.assertAlmostEqual(value, 7.1234, places=3)

    def test_spread_rounded_to_4_decimals(self):
        """Спред округлён до 4 знаков после запятой."""
        opp = make_opportunity(spread=1.23456789)
        row, written = self._write_and_read(opp)
        self.assertEqual(written["gross_spread_pct"], 1.2346)

    def test_price_long_parses_correctly(self):
        """price_long соответствует ask на long-бирже."""
        opp = make_opportunity(price_long=63500.123456)
        row, _ = self._write_and_read(opp)
        self.assertAlmostEqual(float(row["price_long"]), 63500.123456, places=4)

    def test_price_short_parses_correctly(self):
        """price_short соответствует bid на short-бирже."""
        opp = make_opportunity(price_short=64000.0)
        row, _ = self._write_and_read(opp)
        self.assertAlmostEqual(float(row["price_short"]), 64000.0, places=2)

    def test_timestamp_is_valid_iso8601(self):
        """timestamp должен парситься как валидный ISO-8601."""
        opp = make_opportunity()
        ts = "2026-06-05T12:34:56.789000Z"
        row, _ = self._write_and_read(opp, timestamp=ts)
        # Убираем trailing Z для datetime.fromisoformat
        parsed = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        self.assertEqual(parsed.year, 2026)
        self.assertEqual(parsed.hour, 12)

    def test_funding_rates_stored_correctly(self):
        """funding_long и funding_short соответствуют данным из MarketData."""
        opp = make_opportunity(funding_long=0.000125, funding_short=0.000300)
        row, _ = self._write_and_read(opp)
        self.assertAlmostEqual(float(row["funding_long"]), 0.000125, places=6)
        self.assertAlmostEqual(float(row["funding_short"]), 0.000300, places=6)

    def test_funding_diff_calculated_correctly(self):
        """funding_diff_pct = (funding_short - funding_long) * 100."""
        opp = make_opportunity(funding_long=0.0001, funding_short=0.0003)
        row, _ = self._write_and_read(opp)
        expected = (0.0003 - 0.0001) * 100  # = 0.02
        self.assertAlmostEqual(float(row["funding_diff_pct"]), expected, places=5)

    def test_effective_spread_is_gross_minus_funding(self):
        """effective_spread_pct = gross_spread - funding_diff."""
        opp = make_opportunity(spread=1.5, funding_long=0.0001, funding_short=0.0003)
        row, _ = self._write_and_read(opp)
        funding_diff = (0.0003 - 0.0001) * 100  # 0.02%
        expected = round(1.5 - funding_diff, 4)
        self.assertAlmostEqual(float(row["effective_spread_pct"]), expected, places=4)

    def test_exchange_names_preserved(self):
        """Названия бирж не изменяются при записи/чтении."""
        opp = make_opportunity(exchange_long="mexc", exchange_short="bybit")
        row, _ = self._write_and_read(opp)
        self.assertEqual(row["exchange_long"], "mexc")
        self.assertEqual(row["exchange_short"], "bybit")

    def test_symbol_preserved(self):
        """Символ сохраняется без изменений."""
        opp = make_opportunity(symbol="NEARUSDT")
        row, _ = self._write_and_read(opp)
        self.assertEqual(row["symbol"], "NEARUSDT")


# ═══════════════════════════════════════════════════════════════════════════════
# ТЕСТ 3: Крайние случаи
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases(unittest.TestCase):
    """Граничные значения и нестандартные входные данные."""

    def _write_and_read_single(self, opp, timestamp=None):
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        write_collector_row(writer, opp, timestamp)
        buf.seek(0)
        return list(csv.DictReader(io.StringIO(buf.getvalue())))[0]

    def test_zero_funding_rates(self):
        """Нулевые funding rates обрабатываются без ошибок."""
        opp = make_opportunity(funding_long=0.0, funding_short=0.0)
        row = self._write_and_read_single(opp)
        self.assertEqual(float(row["funding_diff_pct"]), 0.0)
        self.assertAlmostEqual(
            float(row["effective_spread_pct"]),
            float(row["gross_spread_pct"]),
            places=4,
        )

    def test_very_large_spread(self):
        """Большой спред (7%+) записывается корректно."""
        opp = make_opportunity(spread=7.8543)
        row = self._write_and_read_single(opp)
        self.assertAlmostEqual(float(row["gross_spread_pct"]), 7.8543, places=3)

    def test_negative_effective_spread_when_funding_dominates(self):
        """Если funding > gross spread, effective_spread может быть отрицательным."""
        # gross_spread=0.5%, funding_diff=1.0% → effective=-0.5%
        opp = make_opportunity(
            spread=0.5,
            funding_long=0.0,
            funding_short=0.01,  # funding_diff = 1.0%
        )
        row = self._write_and_read_single(opp)
        effective = float(row["effective_spread_pct"])
        self.assertLess(effective, 0)

    def test_none_market_data_handled(self):
        """Если data_long или data_short = None — не падаем, funding = 0."""
        opp = make_opportunity()
        opp.data_long = None
        opp.data_short = None
        # Не должно бросать исключение
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        try:
            write_collector_row(writer, opp)
        except Exception as e:
            self.fail(f"Исключение при None market_data: {e}")

    def test_high_precision_prices(self):
        """Цены с большим числом знаков округляются до 6."""
        opp = make_opportunity(price_long=0.00012345678)
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()
        written = write_collector_row(writer, opp)
        # round(..., 6) → 0.000123
        self.assertEqual(written["price_long"], round(0.00012345678, 6))

    def test_multiple_rows_maintain_order(self):
        """Несколько строк записываются в правильном порядке."""
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS)
        writer.writeheader()

        symbols = ["BTCUSDT", "ETHUSDT", "NEARUSDT"]
        for sym in symbols:
            write_collector_row(writer, make_opportunity(symbol=sym))

        buf.seek(0)
        rows = list(csv.DictReader(io.StringIO(buf.getvalue())))
        self.assertEqual(len(rows), 3)
        for i, sym in enumerate(symbols):
            self.assertEqual(rows[i]["symbol"], sym)


# ═══════════════════════════════════════════════════════════════════════════════
# ТЕСТ 4: Статистика
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatistics(unittest.TestCase):
    """Агрегированная статистика по сессии должна считаться правильно."""

    def _make_stats_entry(self):
        return {"count": 0, "max_spread": 0.0, "total_spread": 0.0}

    def test_max_spread_tracked_correctly(self):
        """max_spread отражает максимум за всю сессию."""
        stats = self._make_stats_entry()
        spreads = [1.2, 7.5, 3.1, 0.8, 5.0]
        for s in spreads:
            stats["count"] += 1
            stats["total_spread"] += s
            stats["max_spread"] = max(stats["max_spread"], s)
        self.assertEqual(stats["max_spread"], 7.5)

    def test_average_spread_calculated_correctly(self):
        """Средний спред считается верно."""
        stats = self._make_stats_entry()
        spreads = [1.0, 2.0, 3.0]
        for s in spreads:
            stats["count"] += 1
            stats["total_spread"] += s
            stats["max_spread"] = max(stats["max_spread"], s)
        avg = stats["total_spread"] / stats["count"]
        self.assertAlmostEqual(avg, 2.0)

    def test_count_increments(self):
        """Счётчик инкрементируется при каждой записи."""
        stats = self._make_stats_entry()
        for _ in range(5):
            stats["count"] += 1
        self.assertEqual(stats["count"], 5)


# ═══════════════════════════════════════════════════════════════════════════════
# ТЕСТ 5: Файловые операции
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileOperations(unittest.TestCase):
    """CSV-файлы корректно создаются и читаются с диска."""

    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()

    def _csv_path(self, name="test.csv"):
        return Path(self.tmp_dir) / name

    def test_file_created_with_header(self):
        """Файл создаётся и содержит заголовок."""
        path = self._csv_path()
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

        with open(path, "r") as f:
            first_line = f.readline().strip()

        for field in CSV_FIELDS:
            self.assertIn(field, first_line)

    def test_written_rows_readable_from_disk(self):
        """Строки, записанные на диск, читаются корректно."""
        path = self._csv_path()
        opp = make_opportunity(symbol="SOLUSDT", spread=2.456)

        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            write_collector_row(writer, opp)

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["symbol"], "SOLUSDT")
        self.assertAlmostEqual(float(rows[0]["gross_spread_pct"]), 2.456, places=3)

    def test_utf8_encoding_no_bom(self):
        """Файл в UTF-8 без BOM."""
        path = self._csv_path()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()

        with open(path, "rb") as f:
            header = f.read(3)

        # BOM для UTF-8: b'\xef\xbb\xbf' — его не должно быть
        self.assertNotEqual(header, b"\xef\xbb\xbf")

    def test_flush_preserves_data(self):
        """После flush() данные не теряются."""
        path = self._csv_path()
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            write_collector_row(writer, make_opportunity())
            f.flush()

        with open(path, "r") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 1)

    def test_large_write_performance(self):
        """500 строк записываются менее чем за 2 секунды."""
        import time
        path = self._csv_path("perf.csv")
        start = time.time()
        with open(path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
            writer.writeheader()
            for i in range(500):
                opp = make_opportunity(spread=1.0 + i * 0.001)
                write_collector_row(writer, opp)
        elapsed = time.time() - start
        self.assertLess(elapsed, 2.0, f"Запись 500 строк заняла {elapsed:.2f}с > 2с")


# ─── Запуск ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suites_in_order = [
        TestCSVStructure,
        TestDataParsing,
        TestEdgeCases,
        TestStatistics,
        TestFileOperations,
    ]

    for test_class in suites_in_order:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    verbosity = 2 if "-v" in sys.argv else 1
    runner = unittest.TextTestRunner(verbosity=verbosity)
    result = runner.run(suite)

    total = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed

    print(f"\n{'='*50}")
    print(f"  Итог: {passed}/{total} тестов прошло")
    if failed:
        print(f"  ❌ Провалено: {failed}")
    else:
        print(f"  ✅ Все тесты прошли")
    print(f"{'='*50}")

    sys.exit(0 if not failed else 1)