import os, sys
from datetime import datetime
import anthropic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import ANTHROPIC_API_KEY, FINNHUB_API_KEY, NEWSAPI_KEY, MODEL_MAIN
import market_data

TRADING_DAYS_3M = 63  # ~21 trading days/month × 3, used to slice 1y history instead of a separate 3mo fetch

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _pct_return(hist, days=TRADING_DAYS_3M):
    close = hist["Close"].tail(days)
    if len(close) < 2 or close.iloc[0] == 0:
        return "N/A"
    return round(((close.iloc[-1] - close.iloc[0]) / close.iloc[0]) * 100, 2)

def analyze(ticker, info, spy_ret, vix, tnx, sector_ret, stock_ret, sector_etf, news, mkt_news, sentiment, earnings):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    name = info.get("longName", ticker)
    curr = info.get("currentPrice","N/A")
    target = info.get("targetMeanPrice","N/A")
    upside = f"{((target-curr)/curr*100):.1f}%" if isinstance(curr,(int,float)) and isinstance(target,(int,float)) and curr>0 else "N/A"
    rel = round(stock_ret-sector_ret,2) if isinstance(stock_ret,float) and isinstance(sector_ret,float) else "N/A"

    prompt = f"""You are the Macro & Sentiment Analyst at Claudio Inc.
Live news and real-time sentiment available. Determine if NOW is the right time to trade {ticker}.

COMPANY: {name} ({ticker}) | {info.get('sector')} / {info.get('industry')} | BETA: {info.get('beta')}
S&P 500 3M: {spy_ret}% | VIX: {vix} | 10YR YIELD: {tnx}%
SECTOR ({sector_etf}): {sector_ret}% | STOCK 3M: {stock_ret}% | VS SECTOR: {rel}%
ANALYST CONSENSUS: {info.get('recommendationKey')} ({info.get('numberOfAnalystOpinions')} analysts)
PRICE TARGET: ${target} (Upside: {upside}) | SHORT %: {info.get('shortPercentOfFloat')}
SENTIMENT: {sentiment} | NEXT EARNINGS: {earnings}

COMPANY NEWS (last 7 days):
{news}

MARKET NEWS (today):
{mkt_news}

MACRO & SENTIMENT ANALYSIS — {ticker}
{'='*50}

1. MACRO ENVIRONMENT
2. SECTOR DYNAMICS
3. NEWS ANALYSIS
4. EARNINGS CATALYST
5. SENTIMENT & POSITIONING
6. NARRATIVE
7. MACRO SCORE: [X/10]
8. VERDICT: [FAVORABLE / NEUTRAL / UNFAVORABLE]
[One paragraph — is macro a tailwind or headwind right now]"""

    resp = client.messages.create(model=MODEL_MAIN, max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def run(ticker, data=None, extras=None):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  🌍 MACRO AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    if data is None:
        print("  📊 Gathering data...")
        data = market_data.fetch_core(ticker)
    info = data["info"]
    if extras is None:
        print("  📰 Fetching live news & sentiment...")
        extras = market_data.fetch_macro_extras(ticker, info, FINNHUB_API_KEY, NEWSAPI_KEY)

    spy_ret = _pct_return(extras["spy_hist"])
    vix_v = round(extras["vix_hist"]["Close"].iloc[-1], 2) if not extras["vix_hist"].empty else "N/A"
    tnx_v = round(extras["tnx_hist"]["Close"].iloc[-1], 2) if not extras["tnx_hist"].empty else "N/A"
    sec_ret = _pct_return(extras["sector_hist"])
    stk_ret = _pct_return(data["hist"])

    print("  🧠 Analyzing...")
    analysis = analyze(ticker, info, spy_ret, vix_v, tnx_v, sec_ret, stk_ret, extras["sector_etf"],
                       extras["news"], extras["mkt_news"], extras["sentiment"], extras["earnings"])
    print(analysis)
    path = os.path.join(REPO_ROOT, "reports", f"macro_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/macro_{ticker}.txt")
    return analysis

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
