from datetime import timedelta

import pandas as pd
import pytest

from md_feed.cache import KlineCache


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


class TestKlineCacheUpdate:
    def test_first_load_returns_false(self):
        """First load should not trigger handler (returns False)."""
        cache = KlineCache()
        candles = make_candles([2, 1], [100.0, 101.0])  # 2 days ago, 1 day ago

        result = cache.update("AAPL", candles)

        assert result is False
        assert cache.get("AAPL") is not None
        assert len(cache.get("AAPL")) == 2

    def test_empty_dataframe_returns_false(self):
        """Empty DataFrame should return False and not crash."""
        cache = KlineCache()
        empty_df = pd.DataFrame()

        result = cache.update("AAPL", empty_df)

        assert result is False
        assert cache.get("AAPL") is None

    def test_same_candles_returns_false(self):
        """Polling same candles should not trigger handler."""
        cache = KlineCache()
        candles = make_candles([2, 1], [100.0, 101.0])

        cache.update("AAPL", candles)
        result = cache.update("AAPL", candles)

        assert result is False

    def test_new_closed_candle_returns_true(self):
        """When a new candle closes, should return True."""
        cache = KlineCache()

        # Initial load: 2 days ago and 1 day ago (1 day ago is "current")
        initial = make_candles([2, 1], [100.0, 101.0])
        cache.update("AAPL", initial)

        # Poll: 1 day ago and today (1 day ago is now closed, today is current)
        poll = make_candles([1, 0], [101.0, 102.0])
        result = cache.update("AAPL", poll)

        assert result is True
        assert len(cache.get("AAPL")) == 3

    def test_updates_existing_candle_data(self):
        """Should update existing candle with fresh data (keep='last')."""
        cache = KlineCache()

        initial = make_candles([2, 1], [100.0, 101.0])
        cache.update("AAPL", initial)

        # Same dates but updated close price for day 1
        updated = make_candles([2, 1], [100.0, 105.0])
        cache.update("AAPL", updated)

        df = cache.get("AAPL")
        assert df.iloc[-1]["Close"] == 105.0

    def test_multiple_tickers_independent(self):
        """Each ticker should have independent cache."""
        cache = KlineCache()

        aapl = make_candles([1], [150.0])
        msft = make_candles([1], [400.0])

        cache.update("AAPL", aapl)
        cache.update("MSFT", msft)

        assert cache.get("AAPL").iloc[0]["Close"] == 150.0
        assert cache.get("MSFT").iloc[0]["Close"] == 400.0


class TestKlineCacheEviction:
    def test_evicts_old_candles(self):
        """Candles older than max_period should be evicted."""
        cache = KlineCache(max_period=timedelta(days=30))

        # Create candles: 60 days ago (should evict), 20 days ago, today
        candles = make_candles([60, 20, 0], [100.0, 101.0, 102.0])
        cache.update("AAPL", candles)

        df = cache.get("AAPL")
        # 60-day-old candle should be evicted, only 2 remain
        assert len(df) == 2

    def test_default_max_period_is_180_days(self):
        """Default max_period should be 180 days (6 months)."""
        cache = KlineCache()
        assert cache._max_period == timedelta(days=180)


class TestKlineCacheGet:
    def test_get_nonexistent_ticker_returns_none(self):
        """Getting a ticker that doesn't exist should return None."""
        cache = KlineCache()
        assert cache.get("UNKNOWN") is None

    def test_get_returns_full_dataframe(self):
        """Get should return the full cached DataFrame."""
        cache = KlineCache()
        candles = make_candles([3, 2, 1], [100.0, 101.0, 102.0])

        cache.update("AAPL", candles)
        df = cache.get("AAPL")

        assert len(df) == 3
        assert list(df.columns) == ["Open", "High", "Low", "Close", "Volume"]
