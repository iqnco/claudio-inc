import os, sys
from datetime import datetime
import anthropic

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "agents"))
from config.settings import ANTHROPIC_API_KEY, MODEL_FAST
import market_data

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def analyze(ticker, data):
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    info = data["info"]
    ebitda = info.get("ebitda", 0) or 0
    int_exp = info.get("interestExpense", 0) or 0
    coverage = round(ebitda/abs(int_exp), 2) if int_exp != 0 else "N/A"
    debt = info.get("totalDebt", 0) or 0
    cash = info.get("totalCash", 0) or 0

    prompt = f"""You are the Financial Health Agent at Claudio Inc.
Forensic accounting and balance sheet specialist. Be ruthless finding red flags.

COMPANY: {info.get('longName',ticker)} ({ticker}) | {info.get('sector')}
TOTAL DEBT: ${debt} | CASH: ${cash} | NET DEBT: ${debt-cash}
D/E: {info.get('debtToEquity')} | CURRENT RATIO: {info.get('currentRatio')} | QUICK RATIO: {info.get('quickRatio')}
INTEREST COVERAGE: {coverage}x | EBITDA: ${ebitda}
FCF: ${info.get('freeCashflow')} | OP CF: ${info.get('operatingCashflow')}
NET INCOME: ${info.get('netIncomeToCommon')} | REVENUE: ${info.get('totalRevenue')}
INSIDER %: {info.get('heldPercentInsiders')} | INST %: {info.get('heldPercentInstitutions')}
SHORT RATIO: {info.get('shortRatio')} | AUDIT RISK: {info.get('auditRisk')}/10

FINANCIAL HEALTH ANALYSIS — {ticker}
{'='*50}

1. BALANCE SHEET STRENGTH
2. CASH FLOW QUALITY
3. LIQUIDITY ASSESSMENT
4. EARNINGS QUALITY & ACCOUNTING FLAGS
5. CAPITAL ALLOCATION
6. RED FLAGS (or confirm balance sheet is clean)
7. HEALTH SCORE: [X/10]
8. VERDICT: [STRONG / ADEQUATE / WEAK / CRITICAL]
[One paragraph bottom line]"""

    resp = client.messages.create(model=MODEL_FAST, max_tokens=2000,
                                   messages=[{"role":"user","content":prompt}])
    return resp.content[0].text

def run(ticker, data=None):
    ticker = ticker.upper()
    print(f"\n{'='*50}\n  🏦 HEALTH AGENT — {ticker}\n  {now()}\n{'='*50}\n")
    if data is None:
        print("  📊 Gathering data...")
        data = market_data.fetch_core(ticker)
    print("  🧠 Analyzing...")
    analysis = analyze(ticker, data)
    print(analysis)
    path = os.path.join(REPO_ROOT, "reports", f"health_{ticker}.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f: f.write(f"Generated: {now()}\n\n{analysis}")
    print(f"\n  💾 Saved to reports/health_{ticker}.txt")
    return analysis

if __name__ == "__main__":
    run(sys.argv[1].upper() if len(sys.argv)>1 else "AAPL")
