# API Selection Log

## Selected API: yfinance

**Library:** [yfinance](https://github.com/ranaroussi/yfinance)

### Why yfinance Was Chosen

1. **Free to use** - No subscription or payment required
2. **No API key required** - Simplifies setup and avoids key management
3. **AlphaVantage limitations** - The free tier is not generous enough for constant screening. Our strategy requires frequent price checks for stop loss management without the use of limit stop loss orders, which would quickly exhaust AlphaVantage's rate limits.

### Limitations Encountered

1. **No real-time data feed** - yfinance does not support real-time streaming via FIX protocol or WebSocket connections. This is a common limitation across most free US stock data sources.

2. **Polling-based workaround required** - Due to the lack of streaming support, a custom solution was implemented:
   - Built a custom event loop that polls required data sequentially
   - Manually updates an in-memory cache with the latest prices
   - This introduces latency compared to true real-time feeds but is acceptable for the strategy's requirements

### Usage in This Project

- **Stock screening** - Using `yf.screen()` with `EquityQuery` to find liquid tech stocks
- **Price data** - Polling current prices for stop loss monitoring
- **Historical data** - Fetching OHLCV data for analysis
