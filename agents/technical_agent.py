import os, sys
from datetime import datetime
import anthropic, numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import ANTHROPIC_API_KEY, MODEL_FAST
import market_data

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def compute(hist):
    close = hist["Close"]; volume = hist["Volume"]
    high = hist["High"]; low = hist["Low"]
    curr = close.iloc[-1]
    ma20 = close.rolling(20).mean().iloc[-1]
    ma50 = close.rolling(50).mean().iloc[-1]
    ma200 = close.rolling(200).mean().iloc[-1]
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rsi = (100-(100/(1+(gain/loss)))).iloc[-1]
    ema12 = close.ewm(span=12).mean()
    ema26 = close.ewm(span=26).mean()
    macd = ema12-ema26
    signal = macd.ewm(span=9).mean()
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up = (bb_mid+2*bb_std).iloc[-1]
    bb_lo = (bb_mid-2*bb_std).iloc[-1]
    bb_pct = (curr-bb_lo)/(bb_up-bb_lo) if (bb_up-bb_lo)>0 else 0.5
    avgvol = volume.rolling(20).mean().iloc[-1]
    tr = np.maximum(high-low, np.maximum(abs(high-close.shift(1)), abs(low-close.shift(1))))
    atr = tr.rolling(14).mean().iloc[-1]
    roc1m = ((curr-close.iloc[-22])/close.iloc[-22]*100) if len(close)>=22 else 0
    roc3m = ((curr-close.iloc[-66])/close.iloc[-66]*100) if len(close)>=66 else 0
    return {
        "price":round(curr,2), "ma20":round(ma20,2), "ma50":round(ma50,2), "ma200":round(ma200,2),
        "rsi":round(rsi,2), "macd":round(macd.iloc[-1],4), "signal":round(signal.iloc[-1],4),
        "bb_up":round(bb_up,2), "bb_lo":round(bb_lo,2), "bb_pct":round(bb_pct,2),
        "avgvol":int(avgvol), "currvol":int(volume.iloc[-1]),
        "atr":round(atr,2), "atr_pct":round(atr/curr*100,2),
        "roc1m":round(roc1m,2), "roc3m":round(roc3m,2),
        "high52":round(close.max(),2), "low52":round(close.min(),2),
        "golden":ma50>ma200, "bull_macd":macd.iloc[-1]>signal.iloc[-1]
    }

def analyze(ticker, data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    t = compute(data["hist"])
    name = data["info"].get("longName", ticker)

    prompt = f"""You are the Technical Analyst at Claudio Inc.
Identify precise entry/exit points with clearly defined risk/reward.

COMPANY: {name} ({ticker})
PRICE: ${t['price']} | MA20: ${t['ma20']} | MA50: ${t['ma50']} | MA200: ${t['ma200']}
ABOVE MA20: {'YES' if t['price']>t['ma20'] else 'NO'} | ABOVE MA50: {'YES' if t['price']>t['ma50'] else 'NO'} | ABOVE MA200: {'YES' if t['price']>t['ma200'] else 'NO'}
GOLDEN CROSS: {'YES' if t['golden'] else 'NO'} | MACD BULLISH: {'YES' if t['bull_macd'] else 'NO'}
RSI: {t['rsi']} | MACD: {t['macd']} | SIGNAL: {t['signal']}
BB%: {t['bb_pct']} | BB UPPER: ${t['bb_up']} | BB LOWER: ${t['bb_lo']}
ATR: ${t['atr']} ({t['atr_pct']}%) | VOL RATIO: {round(t['currvol']/t['avgvol'],2) if t['avgvol']>0 else 'N/A'}x
1M RETURN: {t['roc1m']}% | 3M RETURN: {t['roc3m']}%
52W RANGE: ${t['low52']} - ${t['high52']}

TECHNICAL ANALYSIS — {ticker}
{'='*50}

1. TREND ANALYSIS (primary, medium, short term)
2. MOMENTUM ASSESSMENT (RSI, MACD, volume confirmation)
3. KEY PRICE LEVELS (support, resistance, breakdown level)
4. ENTRY SETUP (trigger, aggressive vs conservative)
5. TRADE PARAMETERS
   Entry Zone: $
   Stop Loss:  $ (X% risk)
   Target 1:   $ (X% gain — take 50%)
   Target 2:   $ (X% gain — exit rest)
   R/R Ratio:  X:1
   Timeframe:  X weeks/months
6. TECHNICAL SCORE: [X/10]
7. VERDICT: [STRONG SETUP / DEVELOPING / WAIT / NO SETUP]
[One paragraph — what needs to happen to trigger entry]"""

    resp = client.messages.create(model=MODEL_FAST, max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def run(ticker, data=None):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  📈 TECHNICAL AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    if data is None:
        print("  📊 Gathering data...")
        data = market_data.fetch_core(ticker)
    print("  🧠 Computing indicators & analyzing...")
    analysis = analyze(ticker, data)
    print(analysis)
    path = os.path.join(REPO_ROOT, "reports", f"technical_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/technical_{ticker}.txt")
    return analysis

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
