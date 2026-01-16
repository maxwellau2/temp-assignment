from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Position:
    """Represents an open position."""
    ticker: str
    entry_price: float
    shares: int
    stop_loss: float
    entry_date: str


@dataclass
class PortfolioState:
    """Simple state management for the trading strategy."""
    account_size: float = 100_000.0
    risk_pct: float = 0.02  # 2% risk per trade
    positions: dict[str, Position] = field(default_factory=dict)

    @property
    def risk_amount(self) -> float:
        """Dollar amount to risk per trade."""
        return self.account_size * self.risk_pct

    def has_position(self, ticker: str) -> bool:
        return ticker in self.positions

    def open_position(
        self,
        ticker: str,
        entry_price: float,
        shares: int,
        stop_loss: float,
        entry_date: str,
    ) -> Position:
        """Record a new position."""
        position = Position(
            ticker=ticker,
            entry_price=entry_price,
            shares=shares,
            stop_loss=stop_loss,
            entry_date=entry_date,
        )
        self.positions[ticker] = position
        return position

    def close_position(self, ticker: str, exit_price: float) -> Optional[dict]:
        """Close a position and return P&L details."""
        if ticker not in self.positions:
            return None

        pos = self.positions.pop(ticker)
        pnl = (exit_price - pos.entry_price) * pos.shares
        pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * 100

        return {
            "ticker": ticker,
            "entry_price": pos.entry_price,
            "exit_price": exit_price,
            "shares": pos.shares,
            "pnl": pnl,
            "pnl_pct": pnl_pct,
        }

    def get_position(self, ticker: str) -> Optional[Position]:
        return self.positions.get(ticker)
