import yfinance as yf
from yfinance import EquityQuery


def get_top_liquid_tech_stocks(n=20):
    """Find the top N most liquid US tech stocks by average volume using yfinance screener."""
    print("Screening for all US technology stocks...")

    # Query for all US tech stocks on major exchanges
    query = EquityQuery("and", [
        EquityQuery("eq", ["sector", "Technology"]),
        EquityQuery("is-in", ["exchange", "NMS", "NYQ"]),
    ])

    # Screen and sort by average daily volume (descending)
    result = yf.screen(query, sortField="avgdailyvol3m", sortAsc=False, size=250)

    quotes = result.get("quotes", [])
    top_tickers = [stock["symbol"] for stock in quotes[:n]]

    print(f"\nTop {n} Most Liquid US Tech Stocks:")
    print(top_tickers)

    return top_tickers


if __name__ == "__main__":
    TOP_LIQUID_TECH = get_top_liquid_tech_stocks(20)
