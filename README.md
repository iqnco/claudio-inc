# Claudio Inc.

**Version:** see [VERSION](VERSION) · [CHANGELOG.md](CHANGELOG.md)

An AI-powered stock analysis "fund." Six Claude-driven agents (fundamental,
financial health, technical, macro, risk, and a CIO that synthesizes them)
research a ticker and produce a trade brief — paper trading by default.

This repo holds the analysis agents. Pair it with
[claude-telegram-bot](https://github.com/iqnco/claude-telegram-bot) to chat
with them over Telegram, or run them directly from the terminal.

## Quick start (~5 minutes)

```bash
git clone https://github.com/iqnco/claudio-inc.git
cd claudio-inc
python3 setup.py
```

The wizard asks for:
1. An **Anthropic API key** (console.anthropic.com) — powers every agent
2. Three free-tier market-data keys: **FMP**, **Finnhub**, **NewsAPI**
3. Optionally, a **Telegram bot token + chat ID** if you'll use the Telegram front-end

It then creates a virtual environment, installs dependencies, and initializes
the local SQLite database.

Nothing you enter is committed to git — it's written to gitignored
`secrets_local.py` / `config_local.py` files.

### Using it without Telegram

Every agent runs standalone from the terminal:

```bash
venv/bin/python3 agents/fundamental_agent.py AAPL
venv/bin/python3 agents/cio_agent.py AAPL        # full 5-agent CIO brief
venv/bin/python3 agents/technical_agent.py AAPL
venv/bin/python3 agents/health_agent.py AAPL
venv/bin/python3 agents/macro_agent.py AAPL
venv/bin/python3 agents/risk_agent.py AAPL
```

### Using it with Telegram (the full "Claudio Inc." experience)

Clone [claude-telegram-bot](https://github.com/iqnco/claude-telegram-bot) as
a **sibling directory** of this repo:

```bash
cd ..
git clone https://github.com/iqnco/claude-telegram-bot.git
cd claude-telegram-bot
python3 setup.py
```

Its setup wizard auto-detects this repo at `../claudio-inc` and points at
this repo's venv and agents. Then message your bot on Telegram — try
`analyze AAPL` or `help`.

## Project structure

```
claudio-inc/
├── setup.py                 ← run this first
├── secrets_local.example.py ← template (copy → secrets_local.py)
├── config_local.example.py  ← template (copy → config_local.py)
├── config/settings.py       ← non-secret strategy config (committed)
├── agents/
│   ├── cio_agent.py          ← synthesizes the other 5 into a trade brief
│   ├── fundamental_agent.py
│   ├── health_agent.py
│   ├── technical_agent.py
│   ├── macro_agent.py
│   └── risk_agent.py
├── database/
│   ├── setup_db.py           ← run by setup.py, creates claudio.db
│   └── claudio.db            ← gitignored, local SQLite state
├── reports/                  ← gitignored, agent output dumps
└── requirements.txt
```

## Configuration

`config/settings.py` holds non-secret strategy parameters you're welcome to
edit directly and commit: `FUND_NAME`, `INITIAL_CAPITAL`,
`MAX_POSITION_SIZE_PCT`, `MAX_SECTOR_CONCENTRATION_PCT`,
`MAX_PORTFOLIO_DRAWDOWN_PCT`, `PAPER_TRADING`, `MIN_CONVICTION_SCORE`,
`MAX_OPTIONS_RISK_PCT`, `FMP_DAILY_CALL_BUDGET`.

Your name and Telegram chat ID live in the gitignored `config_local.py`
instead, since they're personal rather than strategy settings.

## Manual setup (without the wizard)

1. `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
2. Copy `secrets_local.example.py` → `secrets_local.py`, fill in your API keys
3. Copy `config_local.example.py` → `config_local.py`, fill in `OWNER` and (optionally) `TELEGRAM_CHAT_ID`
4. `venv/bin/python3 database/setup_db.py`
5. `venv/bin/python3 agents/cio_agent.py AAPL`

## Known limitation

The `portfolio` command (in claude-telegram-bot) references a
`agents/portfolio_tracker.py` module that doesn't exist yet in this repo —
it's a stub for a future feature, not wired up. Everything else works.

## Notes

- `PAPER_TRADING = True` by default in `config/settings.py` — this does not
  place real trades, it's a research/brief tool.
- This is a personal-use project shared as-is — no warranty, use at your own risk.
