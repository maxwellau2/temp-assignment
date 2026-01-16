import time
from typing import TYPE_CHECKING

import yfinance as yf

from md_feed.cache import KlineCache

if TYPE_CHECKING:
    from md_feed.handler import KlineHandler


class MDFeed:
    """Market data feed that polls yfinance at fixed intervals."""

    def __init__(
        self,
        tickers: list[str],
        cache: KlineCache,
        poll_interval: float = 60.0,
        lookback_period: str = "6mo",
        poll_lookback: str = "2d",
        interval: str = "1d",
    ):
        """
        Initialize the market data feed.

        Args:
            tickers: List of ticker symbols to poll.
            cache: KlineCache instance for storing data.
            poll_interval: Seconds between polls (default 60).
            lookback_period: Period for initial historical fetch (default "6mo").
            poll_lookback: Period for polling fetch (default "2d").
            interval: Candle interval (default "1d").
        """
        self._tickers = tickers
        self._cache = cache
        self._poll_interval = poll_interval
        self._lookback_period = lookback_period
        self._poll_lookback = poll_lookback
        self._interval = interval
        self._handler: "KlineHandler | None" = None
        self._running = False

    def set_handler(self, handler: "KlineHandler") -> None:
        """Register handler for kline data callbacks."""
        self._handler = handler

    def initialize(self) -> None:
        """Fetch initial historical data for all tickers."""
        for ticker in self._tickers:
            df = yf.Ticker(ticker).history(
                period=self._lookback_period,
                interval=self._interval,
            )
            self._cache.update(ticker, df)

    def run(self) -> None:
        """
        Main event loop (blocking, single-threaded).

        Polls yfinance for each ticker, updates cache, and notifies
        handler when candles close.
        """
        self._running = True
        last_poll = 0.0

        while self._running:
            now = time.time()

            if now - last_poll >= self._poll_interval:
                self._poll_all()
                last_poll = now

            # Small sleep to prevent busy-waiting
            time.sleep(0.1)

    def _poll_all(self) -> None:
        """Poll all tickers and notify handler of closed candles."""
        for ticker in self._tickers:
            df = yf.Ticker(ticker).history(
                period=self._poll_lookback,
                interval=self._interval,
            )
            # print(df)

            has_new_closed = self._cache.update(ticker, df)

            if has_new_closed and self._handler:
                full_df = self._cache.get(ticker)
                if full_df is not None:
                    self._handler.on_kline_data(full_df, ticker)

    def stop(self) -> None:
        """Signal the event loop to stop."""
        self._running = False
