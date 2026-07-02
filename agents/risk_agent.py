import os, sys
from datetime import datetime
import anthropic, numpy as np

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import ANTHROPIC_API_KEY, MODEL_FAST, MAX_POSITION_SIZE_PCT, MAX_PORTFOLIO_DRAWDOWN_PCT
import market_data

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def compute_risk(ticker, data, spy_hist=None):
    hist = data["hist"]
    info = data["info"]
    close = hist["Close"]
    rets = close.pct_change().dropna()
    curr = close.iloc[-1]
    ann_vol = rets.std()*np.sqrt(252)*100
    roll_max = close.cummax()
    max_dd = ((close-roll_max)/roll_max*100).min()
    ann_ret = rets.mean()*252*100
    sharpe = (ann_ret-5)/ann_vol if ann_vol>0 else 0
    if spy_hist is None:
        spy_hist = market_data.fetch_spy_history()
    spy_r = spy_hist["Close"].pct_change().dropna()
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
    atr_pct = round(atr/curr*100, 2)
    # Position sizing as % of total portfolio (half-Kelly, capped at the
    # portfolio's max-per-position rule) — works at any account size.
    suggested_position_pct = round(min(MAX_POSITION_SIZE_PCT, kelly_half) * 100, 2)
    max_position_pct = round(MAX_POSITION_SIZE_PCT * 100, 2)
    # If stopped out at 1 ATR while sized at the suggested %, how much of the
    # total portfolio is actually at risk on this one trade.
    max_loss_pct_1atr = round(suggested_position_pct * atr_pct / 100, 2)
    return {
        "price":round(curr,2), "ann_vol":round(ann_vol,2), "max_dd":round(max_dd,2),
        "sharpe":round(sharpe,2), "beta":round(float(beta),2), "var95":round(var95,2),
        "atr":round(atr,2), "atr_pct":atr_pct,
        "win_rate":round(win_rate*100,1), "kelly_half":round(kelly_half*100,2),
        "suggested_position_pct":suggested_position_pct, "max_position_pct":max_position_pct,
        "max_loss_pct_1atr":max_loss_pct_1atr,
        "stop_1atr":round(curr-atr,2), "stop_2atr":round(curr-2*atr,2),
        "stop_5pct":round(curr*0.95,2), "stop_8pct":round(curr*0.92,2)
    }

def analyze(ticker, m, fs, hs, ts, ms):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    avg = round((fs+hs+ts+ms)/4,1)

    prompt = f"""You are the Risk Manager at Claudio Inc.
Last line of defense. Size positions correctly. High risk tolerance but protect the portfolio.
Position sizing is always expressed as a % of total portfolio, never a dollar
amount or share count — this has to work for any account size.

MAX POSITION SIZE: {m['max_position_pct']}% of portfolio (hard cap per position)
TICKER: {ticker} | PRICE: ${m['price']}
ANN VOLATILITY: {m['ann_vol']}% | BETA: {m['beta']} | MAX DRAWDOWN: {m['max_dd']}%
SHARPE: {m['sharpe']} | 1-DAY VAR 95%: {m['var95']}%
ATR: ${m['atr']} ({m['atr_pct']}% of price)
WIN RATE: {m['win_rate']}% | HALF KELLY: {m['kelly_half']}%
SUGGESTED POSITION SIZE: {m['suggested_position_pct']}% of portfolio (≈{m['max_loss_pct_1atr']}% of total portfolio at risk if stopped at 1 ATR)
STOP OPTIONS: 1ATR ${m['stop_1atr']} | 2ATR ${m['stop_2atr']} | 5% ${m['stop_5pct']} | 8% ${m['stop_8pct']}
AGENT SCORES: Fundamental:{fs} Health:{hs} Technical:{ts} Macro:{ms} Avg:{avg}/10

RISK ASSESSMENT — {ticker}
{'='*50}

1. RISK PROFILE
2. POSITION SIZING RECOMMENDATION (as % of total portfolio — never $ or shares)
3. STOP LOSS RECOMMENDATION (which level and why)
4. PROFIT TARGETS (T1 and T2 as % gain)
5. OPTIONS CONSIDERATION (stock vs options for this setup)
6. RISK SCORE: [X/10] (10=lowest risk)
7. VERDICT: [APPROVED / APPROVED WITH CONDITIONS / REDUCED SIZE / REJECTED]

TRADE SUMMARY:
┌─────────────────────────────────────┐
│ TICKER:    {ticker:<27}│
│ ACTION:    [BUY/SELL/AVOID]         │
│ ENTRY:     $[price]                 │
│ POSITION:  [X]% of portfolio        │
│ STOP:      $[price] ([X]% price risk)│
│ TARGET 1:  $[price] ([X]% gain)     │
│ TARGET 2:  $[price] ([X]% gain)     │
│ R/R:       [X:1]                    │
│ PORTFOLIO RISK: [X]% max loss       │
└─────────────────────────────────────┘"""

    resp = client.messages.create(model=MODEL_FAST, max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text, m

def run(ticker, data=None, spy_hist=None, fs=5, hs=5, ts=5, ms=5):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  ⚖️  RISK AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    if data is None:
        print("  📊 Gathering data...")
        data = market_data.fetch_core(ticker)
    print("  📊 Computing risk metrics...")
    metrics = compute_risk(ticker, data, spy_hist)
    print("  🧠 Analyzing...")
    analysis, m = analyze(ticker, metrics, fs, hs, ts, ms)
    print(analysis)
    path = os.path.join(REPO_ROOT, "reports", f"risk_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/risk_{ticker}.txt")
    return analysis, m

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
