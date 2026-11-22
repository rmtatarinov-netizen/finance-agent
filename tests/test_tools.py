import unittest
from unittest.mock import patch

from tools import format_market_snapshot, get_quotes, resolve_tickers


class FakeSearchResult:
    def __init__(self, quotes):
        self.quotes = quotes


class FakeTicker:
    def __init__(self, info=None, error=None):
        self._info = info or {}
        self._error = error
        self.fast_info = {}

    @property
    def info(self):
        if self._error:
            raise self._error
        return self._info


def fake_search(query, max_results):
    if query == "Apple":
        return FakeSearchResult([
            {"symbol": "AAPL", "shortname": "Apple Inc.", "quoteType": "EQUITY",
             "exchange": "NMS", "sector": "Technology"},
            {"symbol": "AAPU", "shortname": "Direxion Daily AAPL Bull", "quoteType": "ETF",
             "exchange": "NGM"},
        ])
    if query == "Microsoft":
        return FakeSearchResult([
            {"symbol": "MSFT", "longname": "Microsoft Corporation", "quoteType": "EQUITY",
             "exchange": "NMS", "sector": "Technology"},
        ])
    return FakeSearchResult([])


def fake_ticker(symbol):
    if symbol == "AAPL":
        return FakeTicker({
            "regularMarketPrice": 250.0,
            "regularMarketChangePercent": 1.25,
            "marketCap": 3_700_000_000_000,
            "regularMarketVolume": 50_000_000,
        })
    if symbol == "MSFT":
        return FakeTicker({
            "regularMarketPrice": 400.0,
            "regularMarketChangePercent": -0.5,
            "marketCap": 3_000_000_000_000,
            "trailingPE": 35.2,
            "regularMarketVolume": 20_000_000,
        })
    return FakeTicker(error=ValueError("unknown ticker"))


class FinanceToolTests(unittest.TestCase):
    def test_format_market_snapshot(self):
        result = format_market_snapshot.invoke({
            "ticker": "AAPL",
            "price": 250.0,
            "change_percent": 1.25,
            "market_cap": 3_700_000_000_000,
            "pe": 33.4,
        })
        self.assertIn("AAPL: цена $250.00", result)
        self.assertIn("Капитализация: $3,700,000,000,000.", result)
        self.assertIn("P/E: 33.40.", result)
        self.assertIn("изменение за день +1.25%", result)

    @patch("tools.yf.Search", side_effect=fake_search)
    def test_resolve_tickers_filters_non_equity(self, _search):
        result = resolve_tickers.invoke({"queries": ["Apple", "Microsoft", "Unknown"]})
        self.assertIn("Apple -> AAPL", result)
        self.assertIn("Microsoft -> MSFT", result)
        self.assertNotIn("AAPU", result)
        self.assertIn("акций не найдено", result)

    @patch("tools.yf.Ticker", side_effect=fake_ticker)
    def test_get_quotes_maps_fields_and_reports_missing(self, _ticker):
        result = get_quotes.invoke({
            "tickers": ["AAPL", "MSFT"],
            "fields": ["price", "pe", "volume"],
        })
        self.assertIn("AAPL: цена $250.00", result)
        self.assertIn("MSFT: цена $400.00", result)
        self.assertIn("P/E: 35.20.", result)
        self.assertIn("Нет данных: P/E.", result)
        self.assertIn("Объём: 50.00 млн.", result)

    @patch("tools.yf.Ticker", side_effect=fake_ticker)
    def test_get_quotes_rejects_bad_input(self, _ticker):
        result = get_quotes.invoke({"tickers": ["bad ticker!"], "fields": ["price"]})
        self.assertIn("Некорректные тикеры", result)
        result = get_quotes.invoke({"tickers": ["AAPL"], "fields": ["unknown_field"]})
        self.assertIn("Неподдерживаемые поля", result)

    @patch("tools.yf.Ticker", side_effect=fake_ticker)
    def test_get_quotes_handles_api_error(self, _ticker):
        result = get_quotes.invoke({"tickers": ["ZZZZ"], "fields": ["price"]})
        self.assertIn("ZZZZ: не удалось получить данные", result)


if __name__ == "__main__":
    unittest.main()
