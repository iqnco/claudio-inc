import os, sys, requests
from datetime import datetime, timedelta
import anthropic, yfinance as yf

sys.path.insert(0, os.path.expanduser("~/claudio-inc"))
from config.settings import ANTHROPIC_API_KEY, FINNHUB_API_KEY, NEWSAPI_KEY

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_news(ticker):
    try:
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now()-timedelta(days=7)).strftime("%Y-%m-%d")
        r = requests.get("https://finnhub.io/api/v1/company-news",
            params={"symbol":ticker,"from":start,"to":end,"token":FINNHUB_API_KEY},timeout=10).json()
        if isinstance(r,list) and r:
            return "\n".join([f"• {n['headline']}" for n in r[:6]])
        return "No recent news."
    except: return "News unavailable."

def get_market_news():
    try:
        r = requests.get("https://newsapi.org/v2/top-headlines",
            params={"category":"business","country":"us","pageSize":6,"apiKey":NEWSAPI_KEY},timeout=10).json()
        if r.get("articles"):
            return "\n".join([f"• {a['title']}" for a in r["articles"][:6]])
        return "No market news."
    except: return "Market news unavailable."

def get_sentiment(ticker):
    try:
        r = requests.get("https://finnhub.io/api/v1/recommendation-trends",
            params={"symbol":ticker,"token":FINNHUB_API_KEY},timeout=10).json()
        if isinstance(r,list) and r:
            l = r[0]
            return f"Strong Buy:{l.get('strongBuy',0)} Buy:{l.get('buy',0)} Hold:{l.get('hold',0)} Sell:{l.get('sell',0)}"
        return "N/A"
    except: return "N/A"

def get_earnings(ticker):
    try:
        r = requests.get("https://finnhub.io/api/v1/calendar/earnings",
            params={"symbol":ticker,"token":FINNHUB_API_KEY},timeout=10).json()
        e = r.get("earningsCalendar",[])
        if e: return f"{e[0].get('date')} (Est EPS: ${e[0].get('epsEstimate','N/A')})"
        return "Not found"
    except: return "N/A"

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

    resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def run(ticker):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  🌍 MACRO AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    print("  📰 Fetching live news & sentiment...")
    stock = yf.Ticker(ticker)
    info = stock.info
    spy = yf.Ticker("SPY").history(period="3mo")
    vix_h = yf.Ticker("^VIX").history(period="5d")
    tnx_h = yf.Ticker("^TNX").history(period="5d")
    sector_map = {"Technology":"XLK","Healthcare":"XLV","Financials":"XLF",
                  "Consumer Cyclical":"XLY","Consumer Defensive":"XLP",
                  "Industrials":"XLI","Energy":"XLE","Utilities":"XLU",
                  "Real Estate":"XLRE","Materials":"XLB","Communication Services":"XLC"}
    etf = sector_map.get(info.get("sector",""),"SPY")
    sec_h = yf.Ticker(etf).history(period="3mo")
    stk_h = stock.history(period="3mo")
    spy_ret = round(((spy["Close"].iloc[-1]-spy["Close"].iloc[0])/spy["Close"].iloc[0])*100,2) if not spy.empty else "N/A"
    vix_v = round(vix_h["Close"].iloc[-1],2) if not vix_h.empty else "N/A"
    tnx_v = round(tnx_h["Close"].iloc[-1],2) if not tnx_h.empty else "N/A"
    sec_ret = round(((sec_h["Close"].iloc[-1]-sec_h["Close"].iloc[0])/sec_h["Close"].iloc[0])*100,2) if not sec_h.empty else "N/A"
    stk_ret = round(((stk_h["Close"].iloc[-1]-stk_h["Close"].iloc[0])/stk_h["Close"].iloc[0])*100,2) if not stk_h.empty else "N/A"
    print("  🧠 Analyzing...")
    analysis = analyze(ticker, info, spy_ret, vix_v, tnx_v, sec_ret, stk_ret, etf,
                       get_news(ticker), get_market_news(), get_sentiment(ticker), get_earnings(ticker))
    print(analysis)
    path = os.path.expanduser(f"~/claudio-inc/reports/macro_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/macro_{ticker}.txt")
    return analysis

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
