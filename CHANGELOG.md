# Changelog

All notable changes to this project are documented here. Versioning follows
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`): patch for
fixes, minor for backwards-compatible additions, major for breaking changes
(e.g. a `config_local.py` key being renamed or removed).

## [2.1.0] - 2026-07-02

Reliability, cost, and chat-memory fixes from real usage feedback.

- **Fixed:** `analyze TICKER` sent every brief to Telegram twice. `cio_agent.py`
  was sending it directly (`send_telegram()`) *and* `bot.py` was separately
  relaying the same output — only one send now happens, from `bot.py`.
- **Fixed:** the bot was fully synchronous — a multi-minute analysis blocked
  the poll loop, so it looked unresponsive to anything sent in that window.
  Message handling now runs in a background thread per message.
- **Fixed:** free-form chat had no real memory — it shelled out to the
  `claude` CLI with the whole history flattened into one text blob per call.
  It now calls the Anthropic API directly with a proper multi-turn
  `messages` array, so the model actually sees prior turns. Also removes the
  Claude Code CLI as a runtime dependency for chat.
- **Cost/performance:** a full analysis used to fetch the same ticker's
  yfinance data independently in 6 places (once per agent, plus once more
  in the CIO synthesis step), and SPY history separately in both the macro
  and risk agents. All of that is now fetched once (`agents/market_data.py`)
  and shared. Also cut a redundant separate 3-month yfinance fetch in the
  macro agent by slicing the already-fetched 1-year history instead.
- **Cost:** health/technical/risk agents (which mostly narrate numbers
  Python already computed, not open-ended judgment) now run on
  `claude-haiku-4-5-20251001` instead of Sonnet. Fundamental, macro, and the
  CIO synthesis — the calls that need real judgment — stay on Sonnet.
  Configurable via `MODEL_MAIN`/`MODEL_FAST` in `config/settings.py`.
- **Leaner:** removed `FMP_API_KEY` — it was collected by the setup wizard
  but never actually used anywhere in the code. One less key to configure.
  (Non-breaking: an old `secrets_local.py` with a leftover `FMP_API_KEY`
  line still works fine, it's just unused.)

## [2.0.0] - 2026-07-01

**Breaking:** merged in the [claude-telegram-bot](https://github.com/iqnco/claude-telegram-bot)
repo — `bot.py` now lives here instead of a separate sibling repo. That
repo is archived; this is now the single source of truth for both the
analysis agents and the Telegram bot.

- `bot.py` moved into this repo (was `claude-telegram-bot/bot.py`); no more
  `CLAUDIO_INC_PATH` sibling-repo indirection — paths resolve within this repo
- Unified config: `TELEGRAM_TOKEN` (already in `secrets_local.py`) and
  `TELEGRAM_CHAT_ID` (already in `config_local.py`) now also drive the bot
  directly — `TELEGRAM_CHAT_ID` doubles as the bot's allowlist ID, replacing
  the separate `TELEGRAM_ALLOWED_ID` the old bot repo used
- `setup.py` is now one combined wizard covering both agents and bot,
  including the Claude Code CLI check and optional launchd auto-start that
  used to live in the separate bot repo's wizard
- If you have an old `claude-telegram-bot` checkout, it still runs, but
  won't receive further updates — migrate by following this repo's Quick Start

## [1.0.0] - 2026-07-01

Initial public release.

- `setup.py` interactive wizard: Anthropic + market-data API keys, optional
  Telegram integration, venv, database init
- Owner name and Telegram chat ID moved out of the previously-committed
  `config/settings.py` into a gitignored `config_local.py`
- All agent/database paths resolve relative to their own file location
  instead of a hardcoded `~/claudio-inc`
- Genericized the CIO agent's persona text to use the configured owner name
