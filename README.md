# Trading System

Please refer to API_LOG.md and SYSTEM_REVIEW.md for deliverables.

## What It Does

- Screens stocks based on liquidity (50-day avg volume > 300k) and price filters
- Identifies breakout patterns: 30% prior move, 4-40 day consolidation, < 25% retracement
- Executes trades with ATR-based stop losses and 2% account risk position sizing
- Monitors positions with trailing stops based on 10-day SMA

## Project Structure

```
main.py              # Entry point and strategy logic
state.py             # Portfolio and position tracking
ticker_selector.py   # Stock screening utility
md_feed/             # Market data system
  facade.py          # Simplified data interface
  feed.py            # Yahoo Finance polling
  cache.py           # 180-day rolling candlestick cache
```

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the trading bot:
```bash
python main.py
```

This will:
- Initialize 6 months of historical data for 20 tech stocks
- Poll Yahoo Finance every 10 seconds for updates
- Print buy/exit signals to the console

Screen for liquid tech stocks:
```bash
python ticker_selector.py
```

## Configuration

All parameters are in `main.py`:
- `TICKERS`: List of symbols to monitor
- `POLL_INTERVAL_S`: Polling frequency (default: 10s)
- `LOOKBACK_MONTHS`: Historical data period (default: 6)
- Account size: $100,000 with 2% risk per trade

## Requirements

- Python 3.11+
- yfinance
- pandas
- numpy
