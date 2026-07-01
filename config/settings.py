# Non-secret config is committed. Secrets are imported from secrets_local.py (gitignored).
# Personal (non-secret) config is imported from config_local.py (gitignored).
from secrets_local import (TELEGRAM_TOKEN, FMP_API_KEY, ANTHROPIC_API_KEY,
                           FINNHUB_API_KEY, NEWSAPI_KEY)
from config_local import OWNER, TELEGRAM_CHAT_ID

FUND_NAME = "Claudio Inc."
INITIAL_CAPITAL = 10000
MAX_POSITION_SIZE_PCT = 0.10
MAX_SECTOR_CONCENTRATION_PCT = 0.30
MAX_PORTFOLIO_DRAWDOWN_PCT = 0.20
PAPER_TRADING = True
MIN_CONVICTION_SCORE = 7
MAX_OPTIONS_RISK_PCT = 0.05
FMP_DAILY_CALL_BUDGET = 240
