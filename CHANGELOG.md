# Changelog

All notable changes to this project are documented here. Versioning follows
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`): patch for
fixes, minor for backwards-compatible additions, major for breaking changes
(e.g. a `config_local.py` key being renamed or removed).

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
