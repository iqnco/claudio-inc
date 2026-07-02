# Non-secret config is committed. Secrets are imported from secrets_local.py (gitignored).
# Personal (non-secret) config is imported from config_local.py (gitignored).
from secrets_local import (TELEGRAM_TOKEN, ANTHROPIC_API_KEY,
                           FINNHUB_API_KEY, NEWSAPI_KEY)
from config_local import OWNER, TELEGRAM_CHAT_ID

FUND_NAME = "Claudio Inc."
# Position sizing is percentage-of-portfolio based, not tied to a fixed
# dollar capital figure — works the same whether your account is $1k or $1M.
MAX_POSITION_SIZE_PCT = 0.10
MAX_SECTOR_CONCENTRATION_PCT = 0.30
MAX_PORTFOLIO_DRAWDOWN_PCT = 0.20
MIN_CONVICTION_SCORE = 7
MAX_OPTIONS_RISK_PCT = 0.05

# Model routing: judgment-heavy analysis (valuation calls, news/narrative
# interpretation, final synthesis) uses the capable model; agents that
# mostly narrate numbers Python already computed use the cheap one.
MODEL_MAIN = "claude-sonnet-4-6"          # fundamental, macro, cio
MODEL_FAST = "claude-haiku-4-5-20251001"  # health, technical, risk
