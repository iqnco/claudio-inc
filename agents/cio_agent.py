import os, sys, re, requests
from datetime import datetime
import anthropic, yfinance as yf

sys.path.insert(0, os.path.expanduser("~/claudio-inc"))
from config.settings import (ANTHROPIC_API_KEY, TELEGRAM_TOKEN,
                              TELEGRAM_CHAT_ID, PAPER_TRADING, MIN_CONVICTION_SCORE)
sys.path.insert(0, os.path.expanduser("~/claudio-inc/agents"))
from fundamental_agent import run as run_fundamental
from health_agent import run as run_health
from technical_agent import run as run_technical
from macro_agent import run as run_macro
from risk_agent import run as run_risk

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [message[i:i+4000] for i in range(0,len(message),4000)]:
        try:
            r = requests.post(url, json={"chat_id":TELEGRAM_CHAT_ID,"text":chunk}, timeout=15)
            if not r.ok: print(f"  ⚠️ Telegram error: {r.status_code}")
        except Exception as e: print(f"  ⚠️ Telegram failed: {e}")

def extract_score(text):
    matches = re.findall(r'(\d+)/10', text)
    return int(matches[-1]) if matches else 5

def run_full_analysis(ticker):
    ticker = ticker.upper()
    print(f"\n{'#'*55}\n  CLAUDIO INC. — FULL ANALYSIS: {ticker}\n  {now()}\n{'#'*55}\n")

    print("🔍 [1/5] Fundamental Agent...")
    fund = run_fundamental(ticker)

    print("\n🏦 [2/5] Financial Health Agent...")
    health = run_health(ticker)

    print("\n📈 [3/5] Technical Agent...")
    tech = run_technical(ticker)

    print("\n🌍 [4/5] Macro & Sentiment Agent...")
    macro = run_macro(ticker)

    fs = extract_score(fund)
    hs = extract_score(health)
    ts = extract_score(tech)
    ms = extract_score(macro)
    avg = round((fs+hs+ts+ms)/4, 1)

    print(f"\n⚖️  [5/5] Risk Manager...")
    risk, metrics = run_risk(ticker, fs, hs, ts, ms)

    print(f"\n{'#'*55}\n  🧠 CIO COMPILING BRIEF...\n{'#'*55}\n")

    info = yf.Ticker(ticker).info
    name = info.get("longName", ticker)
    price = info.get("currentPrice", "N/A")

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = f"""You are the CIO of Claudio Inc., an elite AI hedge fund run by Nacho Diaz.
Synthesize all agent reports into one decisive trade brief.
Nacho has high risk tolerance. Be specific, direct, and actionable.

TICKER: {ticker} | PRICE: ${price} | DATE: {now()}
SCORES — F:{fs}/10 H:{hs}/10 T:{ts}/10 M:{ms}/10 AVG:{avg}/10
MODE: {'PAPER TRADE' if PAPER_TRADING else 'LIVE TRADE'}

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
Mode: {'PAPER TRADE' if PAPER_TRADING else 'LIVE TRADE'}
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
Entry:      $[price or range]
Position:   $[USD] / [shares]
Stop Loss:  $[price] — [X]% max loss = $[USD]
Target 1:   $[price] — [X]% gain (take 50%)
Target 2:   $[price] — [X]% gain (exit rest)
R/R Ratio:  [X:1]
Timeframe:  [X weeks/months]
Instrument: [Stock / Calls / Puts / Spread]

WATCH FOR
- [catalyst 1]
- [catalyst 2]
- [catalyst 3]

CIO NOTE TO NACHO
[Direct paragraph — honest conviction, biggest risk, clear action directive]

— Claudio Inc. AI Investment Team"""

    resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=2500,
                                   messages=[{"role":"user","content":prompt}])
    brief = resp.content[0].text
    print(brief)

    path = os.path.expanduser(f"~/claudio-inc/reports/CIO_{ticker}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"CLAUDIO INC. — CIO BRIEF\nGenerated: {now()}\n\n{brief}")
    print(f"\n  💾 Saved: {os.path.basename(path)}")

    print(f"\n  📱 Sending to Telegram...")
    send_telegram(brief)
    print(f"  ✅ Sent!")

    return brief

if __name__ == "__main__":
    run_full_analysis(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
