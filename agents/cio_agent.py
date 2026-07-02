import os, sys, re
from datetime import datetime
import anthropic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import (ANTHROPIC_API_KEY, FINNHUB_API_KEY, NEWSAPI_KEY,
                              MODEL_MAIN, OWNER)
import market_data
from fundamental_agent import run as run_fundamental
from health_agent import run as run_health
from technical_agent import run as run_technical
from macro_agent import run as run_macro
from risk_agent import run as run_risk

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def extract_score(text):
    matches = re.findall(r'(\d+)/10', text)
    return int(matches[-1]) if matches else 5

def run_full_analysis(ticker):
    ticker = ticker.upper()
    print(f"\n{'#'*55}\n  CLAUDIO INC. — FULL ANALYSIS: {ticker}\n  {now()}\n{'#'*55}\n")

    print("📊 Gathering shared market data (fetched once, reused by every agent below)...")
    data = market_data.fetch_core(ticker)
    extras = market_data.fetch_macro_extras(ticker, data["info"], FINNHUB_API_KEY, NEWSAPI_KEY)

    print("\n🔍 [1/5] Fundamental Agent...")
    fund = run_fundamental(ticker, data=data)

    print("\n🏦 [2/5] Financial Health Agent...")
    health = run_health(ticker, data=data)

    print("\n📈 [3/5] Technical Agent...")
    tech = run_technical(ticker, data=data)

    print("\n🌍 [4/5] Macro & Sentiment Agent...")
    macro = run_macro(ticker, data=data, extras=extras)

    fs = extract_score(fund)
    hs = extract_score(health)
    ts = extract_score(tech)
    ms = extract_score(macro)
    avg = round((fs+hs+ts+ms)/4, 1)

    print(f"\n⚖️  [5/5] Risk Manager...")
    risk, metrics = run_risk(ticker, data=data, spy_hist=extras["spy_hist"], fs=fs, hs=hs, ts=ts, ms=ms)

    print(f"\n{'#'*55}\n  🧠 CIO COMPILING BRIEF...\n{'#'*55}\n")

    name = data["info"].get("longName", ticker)
    price = data["info"].get("currentPrice", "N/A")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are the CIO of Claudio Inc., an elite AI hedge fund run by {OWNER}.
Synthesize all agent reports into one decisive trade brief.
{OWNER} has high risk tolerance. Be specific, direct, and actionable.

TICKER: {ticker} | PRICE: ${price} | DATE: {now()}
SCORES — F:{fs}/10 H:{hs}/10 T:{ts}/10 M:{ms}/10 AVG:{avg}/10

FUNDAMENTAL REPORT:
{fund[:600]}

HEALTH REPORT:
{health[:600]}

TECHNICAL REPORT:
{tech[:600]}

MACRO REPORT:
{macro[:600]}

RISK REPORT:
{risk[:600]}

Write the final brief in this exact format:

🏦 CLAUDIO INC. — {ticker} BRIEF
{'='*45}
Company: {name}
Price: ${price} | {now()}
{'='*45}

EXECUTIVE SUMMARY
[3 sentences max — what is this company, why now, key driver]

BULL CASE
1. [specific reason with data]
2. [specific reason with data]
3. [specific reason with data]

BEAR CASE
1. [specific risk with impact]
2. [specific risk with impact]
3. [specific risk with impact]

AGENT SCORES
Fundamental:  {fs}/10
Health:       {hs}/10
Technical:    {ts}/10
Macro:        {ms}/10
Average:      {avg}/10

RECOMMENDATION: [STRONG BUY / BUY / HOLD / AVOID / SHORT]
CONVICTION: [X/10]

EXECUTION PLAN
Entry:         $[price or range]
Position Size: [X]% of portfolio (risk-based, see RISK REPORT)
Stop Loss:     $[price] — [X]% price risk ([Y]% of portfolio at risk at that size)
Target 1:      $[price] — [X]% gain (take 50%)
Target 2:      $[price] — [X]% gain (exit rest)
R/R Ratio:     [X:1]
Timeframe:     [X weeks/months]
Instrument:    [Stock / Calls / Puts / Spread]

WATCH FOR
- [catalyst 1]
- [catalyst 2]
- [catalyst 3]

CIO NOTE TO {OWNER.upper()}
[Direct paragraph — honest conviction, biggest risk, clear action directive]

— Claudio Inc. AI Investment Team"""

    resp = client.messages.create(model=MODEL_MAIN, max_tokens=2500,
                                   messages=[{"role":"user","content":prompt}])
    brief = resp.content[0].text
    print(brief)

    path = os.path.join(REPO_ROOT, "reports", f"CIO_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"CLAUDIO INC. — CIO BRIEF\nGenerated: {now()}\n\n{brief}")
    print(f"\n  💾 Saved: {os.path.basename(path)}")

    # Telegram delivery is the caller's job (bot.py relays this return value to
    # the requesting chat). Sending it here too used to double-post every brief.
    return brief

if __name__ == "__main__":
    result = run_full_analysis(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
    print(f"\n  📱 Run this through bot.py to have it delivered to Telegram.")
