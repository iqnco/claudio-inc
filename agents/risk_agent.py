import os, sys
from datetime import datetime
import anthropic, yfinance as yf, numpy as np

sys.path.insert(0, os.path.expanduser("~/claudio-inc"))
from config.settings import ANTHROPIC_API_KEY, INITIAL_CAPITAL, MAX_POSITION_SIZE_PCT, MAX_PORTFOLIO_DRAWDOWN_PCT

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def compute_risk(ticker):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1y")
    info = stock.info
    close = hist["Close"]
    rets = close.pct_change().dropna()
    curr = close.iloc[-1]
    ann_vol = rets.std()*np.sqrt(252)*100
    roll_max = close.cummax()
    max_dd = ((close-roll_max)/roll_max*100).min()
    ann_ret = rets.mean()*252*100
    sharpe = (ann_ret-5)/ann_vol if ann_vol>0 else 0
    spy_h = yf.Ticker("SPY").history(period="1y")
    spy_r = spy_h["Close"].pct_change().dropna()
    n = min(len(rets),len(spy_r))
    beta = np.cov(rets[-n:],spy_r[-n:])[0][1]/np.var(spy_r[-n:]) if n>30 else info.get("beta",1)
    var95 = np.percentile(rets,5)*100
    high = hist["High"]; low = hist["Low"]
    tr = np.maximum(high-low, np.maximum(abs(high-close.shift(1)), abs(low-close.shift(1))))
    atr = tr.rolling(14).mean().iloc[-1]
    win_rate = len(rets[rets>0])/len(rets)
    avg_win = rets[rets>0].mean()*100
    avg_loss = abs(rets[rets<0].mean()*100)
    kelly = (win_rate/avg_loss-(1-win_rate)/avg_win) if avg_win>0 and avg_loss>0 else 0
    kelly_half = max(0, kelly/2)
    suggested = min(INITIAL_CAPITAL*MAX_POSITION_SIZE_PCT, INITIAL_CAPITAL*kelly_half)
    return {
        "price":round(curr,2), "ann_vol":round(ann_vol,2), "max_dd":round(max_dd,2),
        "sharpe":round(sharpe,2), "beta":round(float(beta),2), "var95":round(var95,2),
        "atr":round(atr,2), "atr_pct":round(atr/curr*100,2),
        "win_rate":round(win_rate*100,1), "kelly_half":round(kelly_half*100,2),
        "suggested_usd":round(suggested,2), "shares":int(suggested/curr) if curr>0 else 0,
        "max_pos":INITIAL_CAPITAL*MAX_POSITION_SIZE_PCT,
        "stop_1atr":round(curr-atr,2), "stop_2atr":round(curr-2*atr,2),
        "stop_5pct":round(curr*0.95,2), "stop_8pct":round(curr*0.92,2)
    }

def analyze(ticker, m, fs, hs, ts, ms):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    avg = round((fs+hs+ts+ms)/4,1)

    prompt = f"""You are the Risk Manager at Claudio Inc.
Last line of defense. Size positions correctly. High risk tolerance but protect the portfolio.

PORTFOLIO: ${INITIAL_CAPITAL:,} capital | MAX POSITION: ${m['max_pos']:,}
TICKER: {ticker} | PRICE: ${m['price']}
ANN VOLATILITY: {m['ann_vol']}% | BETA: {m['beta']} | MAX DRAWDOWN: {m['max_dd']}%
SHARPE: {m['sharpe']} | 1-DAY VAR 95%: {m['var95']}%
ATR: ${m['atr']} ({m['atr_pct']}% of price)
WIN RATE: {m['win_rate']}% | HALF KELLY: {m['kelly_half']}%
SUGGESTED POSITION: ${m['suggested_usd']:,} / {m['shares']} shares
STOP OPTIONS: 1ATR ${m['stop_1atr']} | 2ATR ${m['stop_2atr']} | 5% ${m['stop_5pct']} | 8% ${m['stop_8pct']}
AGENT SCORES: Fundamental:{fs} Health:{hs} Technical:{ts} Macro:{ms} Avg:{avg}/10

RISK ASSESSMENT — {ticker}
{'='*50}

1. RISK PROFILE
2. POSITION SIZING RECOMMENDATION (exact $ and shares)
3. STOP LOSS RECOMMENDATION (which level and why)
4. PROFIT TARGETS (T1 and T2 with $ amounts)
5. OPTIONS CONSIDERATION (stock vs options for this setup)
6. RISK SCORE: [X/10] (10=lowest risk)
7. VERDICT: [APPROVED / APPROVED WITH CONDITIONS / REDUCED SIZE / REJECTED]

TRADE SUMMARY:
┌─────────────────────────────────────┐
│ TICKER:    {ticker:<27}│
│ ACTION:    [BUY/SELL/AVOID]         │
│ ENTRY:     $[price]                 │
│ POSITION:  $[USD] / [shares]        │
│ STOP:      $[price] ([X]% risk)     │
│ TARGET 1:  $[price] ([X]% gain)     │
│ TARGET 2:  $[price] ([X]% gain)     │
│ R/R:       [X:1]                    │
│ MAX LOSS:  $[USD]                   │
└─────────────────────────────────────┘"""

    resp = client.messages.create(model="claude-sonnet-4-6", max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text, m

def run(ticker, fs=5, hs=5, ts=5, ms=5):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  ⚖️  RISK AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    print("  📊 Computing risk metrics...")
    metrics = compute_risk(ticker)
    print("  🧠 Analyzing...")
    analysis, m = analyze(ticker, metrics, fs, hs, ts, ms)
    print(analysis)
    path = os.path.expanduser(f"~/claudio-inc/reports/risk_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/risk_{ticker}.txt")
    return analysis, m

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
