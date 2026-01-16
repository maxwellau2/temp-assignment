from typing import Protocol

import pandas as pd


class KlineHandler(Protocol):
    """Protocol for objects that handle kline data updates."""

    def on_kline_data(self, df: pd.DataFrame, ticker: str) -> None:
        """
        Called when a candle closes.

        Args:
            df: Full DataFrame with all cached candles for the ticker.
            ticker: The ticker symbol.
        """
        ...
