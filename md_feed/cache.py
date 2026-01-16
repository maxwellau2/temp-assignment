from datetime import timedelta

import pandas as pd


class KlineCache:
    """Rolling window cache for kline/candlestick data per ticker."""

    def __init__(self, max_period: timedelta = timedelta(days=180)):
        self._data: dict[str, pd.DataFrame] = {}
        self._max_period = max_period

    def update(self, ticker: str, new_candles: pd.DataFrame) -> bool:
        """
        Update cache with new candles (real-time).

        Expects new_candles to contain 2 rows:
        - index[-2]: the just-closed candle (final values)
        - index[-1]: the current open candle (in-progress)

        Returns True if cache was updated.

        Logic:
        - Update/replace the closed candle in cache with final values
        - Add/replace the open candle in cache
        - Evict candles older than max_period
        """
        if new_candles is None or new_candles.empty:
            return False

        n_candles = len(new_candles)

        if ticker not in self._data:
            # First load - store data
            self._data[ticker] = new_candles.copy()
            self._evict_old(ticker)
            return True

        existing = self._data[ticker]

        if n_candles >= 2:
            # Normal case: have both closed and open candle
            closed_candle = new_candles.iloc[[-2]]  # Second-to-last as DataFrame
            open_candle = new_candles.iloc[[-1]]    # Last as DataFrame

            # Update closed candle (replace if exists, else append)
            closed_idx = closed_candle.index[0]
            if closed_idx in existing.index:
                existing.loc[closed_idx] = closed_candle.iloc[0]
            else:
                existing = pd.concat([existing, closed_candle])

            # Update open candle (replace if exists, else append)
            open_idx = open_candle.index[0]
            if open_idx in existing.index:
                existing.loc[open_idx] = open_candle.iloc[0]
            else:
                existing = pd.concat([existing, open_candle])

        elif n_candles == 1:
            # Edge case: only one candle (treat as open candle)
            open_candle = new_candles.iloc[[-1]]
            open_idx = open_candle.index[0]
            if open_idx in existing.index:
                existing.loc[open_idx] = open_candle.iloc[0]
            else:
                existing = pd.concat([existing, open_candle])

        existing = existing.sort_index()
        self._data[ticker] = existing
        self._evict_old(ticker)

        return True

    def get(self, ticker: str) -> pd.DataFrame | None:
        """Get full DataFrame for ticker."""
        return self._data.get(ticker)

    def _evict_old(self, ticker: str) -> None:
        """Remove candles older than max_period from now."""
        if ticker not in self._data:
            return

        df = self._data[ticker]
        if df.empty:
            return

        # Handle timezone-aware and naive timestamps
        now = pd.Timestamp.now(tz=df.index.tz) if df.index.tz else pd.Timestamp.now()
        cutoff = now - self._max_period

        self._data[ticker] = df[df.index >= cutoff]
