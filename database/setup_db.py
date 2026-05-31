import sqlite3, os
DB_PATH = os.path.expanduser("~/claudio-inc/database/claudio.db")
def setup():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS companies (ticker TEXT PRIMARY KEY, name TEXT, sector TEXT, industry TEXT, description TEXT, employees INTEGER, country TEXT, exchange TEXT, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fundamentals (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT, pe_ratio REAL, pb_ratio REAL, ev_ebitda REAL, price_to_sales REAL, dcf_value REAL, current_price REAL, upside_pct REAL, revenue REAL, net_income REAL, gross_margin REAL, net_margin REAL, roe REAL, eps REAL, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS financial_health (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT, debt_to_equity REAL, current_ratio REAL, quick_ratio REAL, interest_coverage REAL, free_cash_flow REAL, operating_cash_flow REAL, cash_and_equivalents REAL, total_debt REAL, altman_z_score REAL, health_score INTEGER, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS technicals (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT, current_price REAL, ma_50 REAL, ma_200 REAL, rsi_14 REAL, macd REAL, macd_signal REAL, volume REAL, avg_volume REAL, week_52_high REAL, week_52_low REAL, technical_score INTEGER, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS portfolio (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, entry_date TEXT, entry_price REAL, current_price REAL, shares REAL, position_size_usd REAL, unrealized_pnl REAL, unrealized_pnl_pct REAL, stop_loss REAL, target_price REAL, instrument TEXT, status TEXT DEFAULT 'open')''')
    c.execute('''CREATE TABLE IF NOT EXISTS trade_history (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, entry_date TEXT, exit_date TEXT, entry_price REAL, exit_price REAL, shares REAL, pnl REAL, pnl_pct REAL, instrument TEXT, notes TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memory (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT, analysis_type TEXT, conviction_score INTEGER, verdict TEXT, key_points TEXT, price_at_analysis REAL, recommendation TEXT, outcome TEXT, last_updated TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS analysis_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ticker TEXT, date TEXT, screener_score INTEGER, conviction INTEGER, verdict TEXT, sent_telegram INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
    print("✅ Database ready.")
if __name__ == "__main__":
    setup()
