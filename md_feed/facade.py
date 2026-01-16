from typing import TYPE_CHECKING

import pandas as pd

from md_feed.cache import KlineCache
from md_feed.feed import MDFeed

if TYPE_CHECKING:
    from md_feed.handler import KlineHandler


class MDFeedFacade:
    """Simplified facade for the market data feed system."""

    def __init__(
        self,
        tickers: list[str],
        handler: "KlineHandler",
        poll_interval: float = 60.0,
        interval: str = "1d",
        lookback_period: str = "6mo",
    ):
        """
        Initialize the market data feed facade.

        Args:
            tickers: List of ticker symbols to track.
            handler: Handler object with on_kline_data method.
            poll_interval: Seconds between polls (default 60).
            interval: Candle interval (default "1d").
            lookback_period: Period for initial historical fetch (default "6mo").
        """
        self._tickers = tickers
        self._cache = KlineCache()
        self._feed = MDFeed(
            tickers=tickers,
            cache=self._cache,
            poll_interval=poll_interval,
            interval=interval,
            lookback_period=lookback_period,
        )
        self._feed.set_handler(handler)

    def initialize(self) -> dict[str, int]:
        """
        Fetch initial historical data for all tickers.

        Returns:
            Dict mapping ticker to number of candles loaded.
        """
        self._feed.initialize()

        result = {}
        for ticker in self._tickers:
            df = self._cache.get(ticker)
            result[ticker] = len(df) if df is not None else 0
        return result

    def run(self) -> None:
        """Start the polling loop (blocking)."""
        self._feed.run()

    def stop(self) -> None:
        """Stop the polling loop."""
        self._feed.stop()

    def get(self, ticker: str) -> pd.DataFrame | None:
        """Get cached DataFrame for a ticker."""
        return self._cache.get(ticker)
