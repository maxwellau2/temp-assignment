from dataclasses import dataclass
from typing import Optional

import pandas as pd

from md_feed import MDFeedFacade
from state import PortfolioState


@dataclass
class Order:
    """buy order details."""
    ticker: str
    shares: int
    entry_price: float
    stop_loss: float
    stop_distance: float
    atr: float
    risk_amount: float


@dataclass
class ExitResult:
    """exit details."""
    ticker: str
    entry_price: float
    exit_price: float
    shares: int
    pnl: float
    pnl_pct: float
    exit_reason: str
    sma_10: float


def calc_atr(df: pd.DataFrame, period: int = 14) -> Optional[float]:
    if df is None or len(df) < period + 1:
        return None

    high = df["High"]
    low = df["Low"]
    close = df["Close"]

    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()

    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.iloc[-period:].mean()

    return float(atr)


def screen(df: pd.DataFrame) -> bool:
    """
    liquidity and trend filters.

    criteria:
    1. price > $3 AND 50-day average volume > 300k shares
    2. price above 50-day SMA

    returns True if stock passes all filters.
    """
    if df is None or len(df) < 50:
        return False

    current_price = df["Close"].iloc[-1]

    # Filter 1: Price > $3 and 50-day avg volume > 300k
    if current_price <= 3.0:
        return False

    avg_volume_50d = df["Volume"].iloc[-50:].mean()
    if avg_volume_50d <= 300_000:
        return False

    # Filter 2: Current price above 50-day SMA
    sma_50 = df["Close"].iloc[-50:].mean()
    if current_price <= sma_50:
        return False

    return True


def signal(df: pd.DataFrame) -> bool:
    """
    buy signal based on breakout from consolidation.

    criteria:
    1. price increased by at least 30% in recent 63-day window
    2. stock stabilized for 4-40 days with max retracement from peak < 25%
    3. buy when price breaks above the high of the consolidated range

    return True if buy signal is triggered.
    """
    if df is None or len(df) < 63:
        return False

    lookback_63d = df.iloc[-63:]
    current_price = df["Close"].iloc[-1]

    # Criterion 1: Find if there was a 30%+ move in the 63-day window
    # Compare peak to the low before the peak
    peak_price = lookback_63d["High"].max()
    peak_idx = lookback_63d["High"].idxmax()

    # Get data before the peak to find the base
    pre_peak = lookback_63d.loc[:peak_idx]
    if len(pre_peak) < 1:
        return False

    base_price = pre_peak["Low"].min()
    if base_price <= 0:
        return False

    price_increase_pct = (peak_price - base_price) / base_price
    if price_increase_pct < 0.30:
        return False

    # Criterion 2: Stock must have stabilized for 4-40 days
    # with max retracement from peak < 25%
    post_peak = lookback_63d.loc[peak_idx:]
    consolidation_days = len(post_peak)

    if consolidation_days < 4 or consolidation_days > 40:
        return False

    # Check retracement from peak
    lowest_since_peak = post_peak["Low"].min()
    retracement_pct = (peak_price - lowest_since_peak) / peak_price
    if retracement_pct >= 0.25:
        return False

    # Criterion 3: Signal buy when price breaks above the consolidation high
    # The consolidation range high is the peak price in the 63-day window
    consolidation_high = post_peak["High"].max()
    previous_close = df["Close"].iloc[-2] if len(df) >= 2 else 0

    # Breakout: current price above consolidation high AND previous close was below
    if current_price > consolidation_high and previous_close <= consolidation_high:
        return True

    return False


def execute(
    df: pd.DataFrame,
    ticker: str,
    state: PortfolioState,
) -> Optional[Order]:
    """
    signals a buy order with position sizing.

    position sizing:
    - risk: 2% of account ($2,000 on $100k)
    - stop loss: min(low of day, 1x ATR)

    returns Order or None if trade is invalid.
    """
    if df is None or len(df) < 14:
        return None

    if state.has_position(ticker):
        return None

    latest = df.iloc[-1]
    entry_price = float(latest["Close"])
    low_of_day = float(latest["Low"])

    atr = calc_atr(df, period=14)
    if atr is None:
        return None

    # Stop distance = min(low of day distance, 1x ATR)
    low_distance = entry_price - low_of_day
    stop_distance = min(low_distance, atr) if low_distance > 0 else atr

    if stop_distance <= 0:
        return None

    stop_loss = entry_price - stop_distance

    shares = int(state.risk_amount / stop_distance)
    if shares <= 0:
        return None

    entry_date = str(latest.name)

    state.open_position(
        ticker=ticker,
        entry_price=entry_price,
        shares=shares,
        stop_loss=stop_loss,
        entry_date=entry_date,
    )

    return Order(
        ticker=ticker,
        shares=shares,
        entry_price=entry_price,
        stop_loss=stop_loss,
        stop_distance=stop_distance,
        atr=atr,
        risk_amount=state.risk_amount,
    )


def check_exit(
    df: pd.DataFrame,
    ticker: str,
    state: PortfolioState,
) -> Optional[ExitResult]:
    """
    check trailing stop exit based on 10-day SMA.
    exit when price closes below the 10-day SMA and when in position
    """
    if df is None or len(df) < 10:
        return None

    position = state.get_position(ticker)
    if position is None:
        return None

    current_price = float(df["Close"].iloc[-1])
    sma_10 = float(df["Close"].iloc[-10:].mean())

    if current_price < sma_10:
        result = state.close_position(ticker, current_price)
        if result:
            return ExitResult(
                ticker=result["ticker"],
                entry_price=result["entry_price"],
                exit_price=result["exit_price"],
                shares=result["shares"],
                pnl=result["pnl"],
                pnl_pct=result["pnl_pct"],
                exit_reason="trailing_stop_10sma",
                sma_10=sma_10,
            )

    return None


class MyStrategy:
    """main strategy"""

    def __init__(self):
        self.state = PortfolioState()

    def on_kline_data(self, df: pd.DataFrame, ticker: str) -> None:
        exit_result = check_exit(df, ticker, self.state)
        if exit_result:
            r = exit_result
            print(f"EXIT {ticker} - {r.shares} @{r.exit_price:.2f} PnL:{r.pnl:+.0f}")
            return

        if not screen(df) or not signal(df):
            return

        order = execute(df, ticker, self.state)
        if order:
            print(f"BUY {ticker} - {order.shares} @{order.entry_price:.2f} stop:{order.stop_loss:.2f}")


def main():
    feed = MDFeedFacade(
        tickers=["TSLA", "MSFT"],
        handler=MyStrategy(),
        poll_interval=10.0,
        interval="1d",
        lookback_period="6mo"
    )

    print("Initializing with 6 months of historical data...")
    loaded = feed.initialize()
    for ticker, count in loaded.items():
        print(f"[{ticker}] Loaded {count} candles")

    print("Starting polling loop (Ctrl+C to stop)...")
    try:
        feed.run()
    except KeyboardInterrupt:
        feed.stop()
        print("\nStopped.")


if __name__ == "__main__":
    main()
