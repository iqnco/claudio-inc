# Changelog

All notable changes to this project are documented here. Versioning follows
[Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`): patch for
fixes, minor for backwards-compatible additions, major for breaking changes
(e.g. a `config_local.py` key being renamed or removed).

## [1.0.0] - 2026-07-01

Initial public release.

- `setup.py` interactive wizard: Anthropic + market-data API keys, optional
  Telegram integration, venv, database init
- Owner name and Telegram chat ID moved out of the previously-committed
  `config/settings.py` into a gitignored `config_local.py`
- All agent/database paths resolve relative to their own file location
  instead of a hardcoded `~/claudio-inc`
- Genericized the CIO agent's persona text to use the configured owner name
