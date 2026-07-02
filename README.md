# Claudio Inc.

**Version:** see [VERSION](VERSION) · [CHANGELOG.md](CHANGELOG.md)

An AI-powered stock analysis "fund" you can talk to over Telegram. Six
Claude-driven agents (fundamental, financial health, technical, macro,
risk, and a CIO that synthesizes them) research a ticker and produce a
trade brief — paper trading by default. The Telegram bot also doubles as
a general-purpose chat assistant.

## Quick start (~5 minutes)

```bash
git clone https://github.com/iqnco/claudio-inc.git
cd claudio-inc
python3 setup.py
```

The wizard asks for:
1. An **Anthropic API key** (console.anthropic.com) — powers every agent
2. Two free-tier market-data keys: **Finnhub**, **NewsAPI** (fundamentals/technicals/risk all come from yfinance, no key needed)
3. Optionally, a **Telegram bot token** (via @BotFather) and your **Telegram user ID** (via @userinfobot), if you want the bot

It then creates a virtual environment, installs dependencies, initializes
the local SQLite database, and (on macOS, if you set up Telegram) offers
to auto-start the bot on login via `launchd`.

Nothing you enter is committed to git — it's written to gitignored
`secrets_local.py` / `config_local.py` files.

## Using it without Telegram

Every agent runs standalone from the terminal:

```bash
venv/bin/python3 agents/fundamental_agent.py AAPL
venv/bin/python3 agents/cio_agent.py AAPL        # full 5-agent CIO brief
venv/bin/python3 agents/technical_agent.py AAPL
venv/bin/python3 agents/health_agent.py AAPL
venv/bin/python3 agents/macro_agent.py AAPL
venv/bin/python3 agents/risk_agent.py AAPL
```

## Using it with Telegram

Once `secrets_local.py`/`config_local.py` have a Telegram token and chat ID
(from the wizard, or set manually), run the bot:

```bash
venv/bin/python3 bot.py
```

Message it on Telegram:

```
analyze TICKER    — Full 5-agent CIO brief
quick TICKER      — Fundamental analysis only
technical TICKER  — Chart analysis
health TICKER     — Balance sheet / financial health
macro TICKER      — Macro context & news
portfolio         — (not yet wired up, see "Known limitation" below)
clear             — Reset conversation history
[anything else]   — Chat with Claudio (remembers last 25 messages)
```

Free-form chat and every analysis command run through the Anthropic API
directly, with real multi-turn conversation memory for chat (the model
actually sees prior turns, not just a flattened summary of them).

## Project structure

```
claudio-inc/
├── setup.py                 ← run this first
├── bot.py                   ← Telegram bot (optional — skip if you only want the CLI agents)
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
├── conversation_history.json ← gitignored, bot chat state
└── requirements.txt
```

## Configuration

`config/settings.py` holds non-secret strategy parameters you're welcome to
edit directly and commit: `FUND_NAME`, `INITIAL_CAPITAL`,
`MAX_POSITION_SIZE_PCT`, `MAX_SECTOR_CONCENTRATION_PCT`,
`MAX_PORTFOLIO_DRAWDOWN_PCT`, `PAPER_TRADING`, `MIN_CONVICTION_SCORE`,
`MAX_OPTIONS_RISK_PCT`, `MODEL_MAIN`, `MODEL_FAST`.

Your name and Telegram chat ID live in the gitignored `config_local.py`
instead, since they're personal rather than strategy settings.
`TELEGRAM_CHAT_ID` doubles as `bot.py`'s allowlist — it only responds to
messages from that ID.

## Manual setup (without the wizard)

1. `python3 -m venv venv && venv/bin/pip install -r requirements.txt`
2. Copy `secrets_local.example.py` → `secrets_local.py`, fill in your API keys
3. Copy `config_local.example.py` → `config_local.py`, fill in `OWNER` and (optionally) `TELEGRAM_CHAT_ID`
4. `venv/bin/python3 database/setup_db.py`
5. `venv/bin/python3 agents/cio_agent.py AAPL` (or `venv/bin/python3 bot.py` for the Telegram front-end)

## Known limitation

The `portfolio` command references a `agents/portfolio_tracker.py` module
that doesn't exist yet — it's a stub for a future feature, not wired up.
It fails gracefully (a message, not a crash); everything else works.

## Notes

- `PAPER_TRADING = True` by default in `config/settings.py` — this does not
  place real trades, it's a research/brief tool.
- This is a personal-use project shared as-is — no warranty, use at your own risk.
