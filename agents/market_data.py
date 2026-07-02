"""
Shared market-data fetching for all agents.

A full analysis used to fetch the same ticker's info/history independently
in 6 different places (once per agent, plus once more in cio_agent for the
final brief), and macro/risk agents each fetched a full year of SPY history
separately. This module fetches everything once and every agent's analyze()
takes the resulting dict instead of hitting yfinance/Finnhub/NewsAPI itself.

Each agent still falls back to fetching its own data when run standalone
from the CLI (`python3 agents/technical_agent.py AAPL`) — see the `run()`
functions in each agent file.
"""
import requests
import yfinance as yf
from datetime import datetime, timedelta

SECTOR_ETF_MAP = {
    "Technology": "XLK", "Healthcare": "XLV", "Financials": "XLF",
    "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP",
    "Industrials": "XLI", "Energy": "XLE", "Utilities": "XLU",
    "Real Estate": "XLRE", "Materials": "XLB", "Communication Services": "XLC",
}


def fetch_core(ticker):
    """Ticker info + 1y price history — every agent needs this."""
    stock = yf.Ticker(ticker)
    return {"ticker": ticker, "info": stock.info, "hist": stock.history(period="1y")}


def fetch_spy_history():
    """1y SPY history alone — used for the risk agent's beta calc when it
    isn't already available from a fuller fetch_macro_extras() call."""
    return yf.Ticker("SPY").history(period="1y")


def fetch_macro_extras(ticker, info, finnhub_key, newsapi_key, spy_hist=None):
    """SPY/VIX/TNX/sector context + news/sentiment/earnings — macro + risk only.

    SPY is fetched once at 1y resolution (or reused if passed in); both the
    risk agent's beta calc (needs the full series) and macro's 3-month
    return (needs just the tail) are derived from the same fetch instead of
    two separate calls.
    """
    spy_hist = spy_hist if spy_hist is not None else fetch_spy_history()
    vix_hist = yf.Ticker("^VIX").history(period="5d")
    tnx_hist = yf.Ticker("^TNX").history(period="5d")
    etf = SECTOR_ETF_MAP.get(info.get("sector", ""), "SPY")
    sector_hist = spy_hist if etf == "SPY" else yf.Ticker(etf).history(period="3mo")

    return {
        "spy_hist": spy_hist,
        "vix_hist": vix_hist,
        "tnx_hist": tnx_hist,
        "sector_etf": etf,
        "sector_hist": sector_hist,
        "news": _get_company_news(ticker, finnhub_key),
        "mkt_news": _get_market_news(newsapi_key),
        "sentiment": _get_sentiment(ticker, finnhub_key),
        "earnings": _get_earnings(ticker, finnhub_key),
    }


def _get_company_news(ticker, finnhub_key):
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        r = requests.get("https://finnhub.io/api/v1/company-news",
            params={"symbol": ticker, "from": start, "to": end, "token": finnhub_key}, timeout=10).json()
        if isinstance(r, list) and r:
            return "\n".join([f"• {n['headline']}" for n in r[:6]])
        return "No recent news."
    except Exception:
        return "News unavailable."


def _get_market_news(newsapi_key):
    try:
        r = requests.get("https://newsapi.org/v2/top-headlines",
            params={"category": "business", "country": "us", "pageSize": 6, "apiKey": newsapi_key}, timeout=10).json()
        if r.get("articles"):
            return "\n".join([f"• {a['title']}" for a in r["articles"][:6]])
        return "No market news."
    except Exception:
        return "Market news unavailable."


def _get_sentiment(ticker, finnhub_key):
    try:
        r = requests.get("https://finnhub.io/api/v1/recommendation-trends",
            params={"symbol": ticker, "token": finnhub_key}, timeout=10).json()
        if isinstance(r, list) and r:
            l = r[0]
            return f"Strong Buy:{l.get('strongBuy',0)} Buy:{l.get('buy',0)} Hold:{l.get('hold',0)} Sell:{l.get('sell',0)}"
        return "N/A"
    except Exception:
        return "N/A"


def _get_earnings(ticker, finnhub_key):
    try:
        r = requests.get("https://finnhub.io/api/v1/calendar/earnings",
            params={"symbol": ticker, "token": finnhub_key}, timeout=10).json()
        e = r.get("earningsCalendar", [])
        if e:
            return f"{e[0].get('date')} (Est EPS: ${e[0].get('epsEstimate','N/A')})"
        return "Not found"
    except Exception:
        return "N/A"
