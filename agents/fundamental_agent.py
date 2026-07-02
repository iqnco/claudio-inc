import os, sys
from datetime import datetime
import anthropic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import ANTHROPIC_API_KEY, MODEL_MAIN
import market_data

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def analyze(ticker, data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    info = data["info"]
    price = info.get("currentPrice") or info.get("regularMarketPrice", "N/A")
    target = info.get("targetMeanPrice", "N/A")
    upside = f"{((target-price)/price*100):.1f}%" if isinstance(price,(int,float)) and isinstance(target,(int,float)) and price>0 else "N/A"

    prompt = f"""You are the Fundamental Analyst at Claudio Inc., an elite AI hedge fund.
Be ruthless, specific, direct. No fluff.

COMPANY: {info.get('longName',ticker)} ({ticker}) | {info.get('sector')} / {info.get('industry')}
PRICE: ${price} | TARGET: ${target} | UPSIDE: {upside}
P/E: {info.get('trailingPE')} | FWD P/E: {info.get('forwardPE')} | PEG: {info.get('pegRatio')}
P/B: {info.get('priceToBook')} | EV/EBITDA: {info.get('enterpriseToEbitda')}
ROE: {info.get('returnOnEquity')} | ROA: {info.get('returnOnAssets')}
GROSS MARGIN: {info.get('grossMargins')} | NET MARGIN: {info.get('profitMargins')}
REV GROWTH: {info.get('revenueGrowth')} | EARN GROWTH: {info.get('earningsGrowth')}
EPS: ${info.get('trailingEps')} | FWD EPS: ${info.get('forwardEps')}
MARKET CAP: ${info.get('marketCap')} | BETA: {info.get('beta')}
SHORT %: {info.get('shortPercentOfFloat')} | INST %: {info.get('heldPercentInstitutions')}
52W: ${info.get('fiftyTwoWeekLow')} - ${info.get('fiftyTwoWeekHigh')}
FCF: ${info.get('freeCashflow')} | DEBT: ${info.get('totalDebt')} | CASH: ${info.get('totalCash')}
DESCRIPTION: {info.get('longBusinessSummary','')[:400]}

Produce this exact analysis:

FUNDAMENTAL ANALYSIS — {ticker}
{'='*50}

1. VALUATION ASSESSMENT
2. BUSINESS QUALITY
3. EARNINGS POWER & GROWTH
4. BALANCE SHEET STRENGTH
5. TOP 3 RISKS
6. FUNDAMENTAL SCORE: [X/10]
7. VERDICT: [INVESTIGATE FURTHER / MONITOR / PASS]
[Two paragraph directional bias — bullish, bearish, or neutral]"""

    resp = client.messages.create(model=MODEL_MAIN, max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def run(ticker, data=None):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  🔍 FUNDAMENTAL AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    if data is None:
        print("  📊 Gathering data...")
        data = market_data.fetch_core(ticker)
    print("  🧠 Analyzing...")
    analysis = analyze(ticker, data)
    print(analysis)
    path = os.path.join(REPO_ROOT, "reports", f"fundamental_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/fundamental_{ticker}.txt")
    return analysis

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
