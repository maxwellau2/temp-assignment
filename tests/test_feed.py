from datetime import timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from md_feed.cache import KlineCache
from md_feed.feed import MDFeed


def make_candles(
    days_ago: list[int], close_prices: list[float], tz: str = "UTC"
) -> pd.DataFrame:
    """Helper to create test candle DataFrames with relative dates."""
    now = pd.Timestamp.now(tz=tz)
    dates = [(now - timedelta(days=d)).normalize() for d in days_ago]
    return pd.DataFrame(
        {
            "Open": close_prices,
            "High": [p + 1 for p in close_prices],
            "Low": [p - 1 for p in close_prices],
            "Close": close_prices,
            "Volume": [1000] * len(days_ago),
        },
        index=pd.DatetimeIndex(dates),
    )


class TestMDFeedInit:
    def test_default_parameters(self):
        """Should have sensible defaults."""
        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)

        assert feed._poll_interval == 60.0
        assert feed._lookback_period == "6mo"
        assert feed._poll_lookback == "2d"
        assert feed._interval == "1d"
        assert feed._handler is None
        assert feed._running is False

    def test_custom_parameters(self):
        """Should accept custom parameters."""
        cache = KlineCache()
        feed = MDFeed(
            tickers=["AAPL", "MSFT"],
            cache=cache,
            poll_interval=30.0,
            lookback_period="1y",
            poll_lookback="5d",
            interval="1h",
        )

        assert feed._tickers == ["AAPL", "MSFT"]
        assert feed._poll_interval == 30.0
        assert feed._lookback_period == "1y"
        assert feed._poll_lookback == "5d"
        assert feed._interval == "1h"


class TestMDFeedSetHandler:
    def test_set_handler(self):
        """Should register handler."""
        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)

        handler = MagicMock()
        feed.set_handler(handler)

        assert feed._handler is handler


class TestMDFeedInitialize:
    @patch("md_feed.feed.yf.Ticker")
    def test_initialize_fetches_historical_data(self, mock_ticker_class):
        """Initialize should fetch 6mo of data for each ticker."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = make_candles([2, 1], [100.0, 101.0])
        mock_ticker_class.return_value = mock_ticker

        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL", "MSFT"], cache=cache)
        feed.initialize()

        assert mock_ticker_class.call_count == 2
        mock_ticker_class.assert_any_call("AAPL")
        mock_ticker_class.assert_any_call("MSFT")
        mock_ticker.history.assert_called_with(period="6mo", interval="1d")

    @patch("md_feed.feed.yf.Ticker")
    def test_initialize_populates_cache(self, mock_ticker_class):
        """Initialize should populate cache for all tickers."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = make_candles([2, 1], [100.0, 101.0])
        mock_ticker_class.return_value = mock_ticker

        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)
        feed.initialize()

        assert cache.get("AAPL") is not None
        assert len(cache.get("AAPL")) == 2


class TestMDFeedPollAll:
    @patch("md_feed.feed.yf.Ticker")
    def test_poll_all_fetches_poll_lookback(self, mock_ticker_class):
        """Poll should fetch poll_lookback period (2d by default)."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = make_candles([2, 1], [100.0, 101.0])
        mock_ticker_class.return_value = mock_ticker

        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache, poll_lookback="2d")

        # Initialize first
        feed.initialize()
        mock_ticker.history.reset_mock()

        # Now poll
        feed._poll_all()

        mock_ticker.history.assert_called_with(period="2d", interval="1d")

    @patch("md_feed.feed.yf.Ticker")
    def test_poll_calls_handler_on_new_candle(self, mock_ticker_class):
        """Handler should be called when a new candle closes."""
        mock_ticker = MagicMock()
        mock_ticker_class.return_value = mock_ticker

        # Initial load: 2 days ago and 1 day ago
        mock_ticker.history.return_value = make_candles([2, 1], [100.0, 101.0])

        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)
        handler = MagicMock()
        feed.set_handler(handler)
        feed.initialize()

        # Poll with new closed candle: 1 day ago and today
        mock_ticker.history.return_value = make_candles([1, 0], [101.0, 102.0])
        feed._poll_all()

        handler.on_kline_data.assert_called_once()
        call_args = handler.on_kline_data.call_args
        assert call_args[0][1] == "AAPL"  # ticker argument
        assert len(call_args[0][0]) == 3  # DataFrame with 3 candles

    @patch("md_feed.feed.yf.Ticker")
    def test_poll_does_not_call_handler_on_same_data(self, mock_ticker_class):
        """Handler should NOT be called when no new candle closes."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = make_candles([2, 1], [100.0, 101.0])
        mock_ticker_class.return_value = mock_ticker

        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)
        handler = MagicMock()
        feed.set_handler(handler)
        feed.initialize()

        # Poll with same data
        feed._poll_all()

        handler.on_kline_data.assert_not_called()


class TestMDFeedStop:
    def test_stop_sets_running_false(self):
        """Stop should set _running to False."""
        cache = KlineCache()
        feed = MDFeed(tickers=["AAPL"], cache=cache)
        feed._running = True

        feed.stop()

        assert feed._running is False
