#!/usr/bin/env python3
"""
Claudio Inc. — setup wizard.

Run this once after cloning the repo:

    python3 setup.py

It walks you through the API keys the analysis agents need, creates a
virtual environment, installs dependencies, and initializes the local
SQLite database.

Note: this repo only runs the *analysis agents*. To chat with them over
Telegram, also clone https://github.com/iqnco/claude-telegram-bot as a
sibling directory and run its setup.py too — see README.md.

No third-party packages are required to run this script itself — only
the Python standard library.
"""

import getpass
import os
import subprocess
import sys
import textwrap
import venv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
VENV_DIR  = REPO_ROOT / "venv"
VENV_PY   = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python3")
VENV_PIP  = VENV_DIR / ("Scripts/pip.exe" if os.name == "nt" else "bin/pip")


def banner(text):
    print("\n" + "=" * 64)
    print(text)
    print("=" * 64)


def step(n, total, title):
    print(f"\n[{n}/{total}] {title}")
    print("-" * 64)


def ask(prompt, default=None, validate=None, error_msg="That doesn't look right, try again."):
    while True:
        suffix = f" [{default}]" if default is not None else ""
        raw = input(f"{prompt}{suffix}: ").strip()
        if not raw and default is not None:
            raw = default
        if not raw:
            print("This can't be empty.")
            continue
        if validate is None or validate(raw):
            return raw
        print(error_msg)


def ask_secret(prompt, optional=False, validate=None, error_msg="That doesn't look right, try again."):
    while True:
        raw = getpass.getpass(f"{prompt}: ").strip()
        if not raw:
            if optional:
                return ""
            print("This can't be empty.")
            continue
        if validate is None or validate(raw):
            return raw
        print(error_msg)


def write_file_guarded(path: Path, content: str, label: str):
    if path.exists():
        ans = input(f"{label} already exists at {path} — overwrite? [y/N]: ").strip().lower()
        if ans not in ("y", "yes"):
            print(f"Keeping existing {path}.")
            return False
    path.write_text(content)
    print(f"Wrote {path}")
    return True


def run(cmd, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def main():
    banner("Claudio Inc. — setup")
    print("This configures the analysis agents (Anthropic, market-data APIs, Telegram).\n")
    print(f"Repo location: {REPO_ROOT}")

    step(1, 5, "Anthropic API key")
    print("Used by every agent to write its analysis. Get one at:")
    print("  https://console.anthropic.com/settings/keys\n")
    anthropic_key = ask_secret(
        "Paste your Anthropic API key",
        validate=lambda v: v.startswith("sk-ant-"),
        error_msg='Anthropic keys start with "sk-ant-". Try again.',
    )

    step(2, 5, "Market-data API keys")
    print(textwrap.dedent("""\
        Three free-tier API keys power the agents' data:
          FMP       (fundamentals/valuation) — https://site.financialmodelingprep.com/developer/docs
          Finnhub   (health/technical data)  — https://finnhub.io/register
          NewsAPI   (macro news)             — https://newsapi.org/register
        All have free tiers. Leave any blank to skip that agent's data source.
    """))
    fmp_key     = ask_secret("Paste your FMP API key", optional=True)
    finnhub_key = ask_secret("Paste your Finnhub API key", optional=True)
    newsapi_key = ask_secret("Paste your NewsAPI key", optional=True)

    step(3, 5, "Telegram (optional, only needed if you'll also run claude-telegram-bot)")
    print(textwrap.dedent("""\
        Claudio can send you analysis briefs over Telegram, via the same bot
        used by the claude-telegram-bot repo. If you haven't set that up yet,
        create a bot with @BotFather first, then come back here.
        Leave blank to skip (agents still work, just print to the terminal).
    """))
    telegram_token = ask_secret("Paste your Telegram bot token", optional=True)
    telegram_chat_id = ""
    owner_name = ask("What's your first name? (used in the CIO agent's prompts)", default="there")
    if telegram_token:
        print("\nGet your numeric Telegram user ID by messaging @userinfobot.")
        telegram_chat_id = ask(
            "Your numeric Telegram chat ID",
            validate=lambda v: v.isdigit(),
            error_msg="That should be a number. Try again.",
        )

    write_file_guarded(
        REPO_ROOT / "secrets_local.py",
        f'# GITIGNORED — real secrets.\n'
        f'TELEGRAM_TOKEN    = {telegram_token!r}\n'
        f'FMP_API_KEY       = {fmp_key!r}\n'
        f'ANTHROPIC_API_KEY = {anthropic_key!r}\n'
        f'FINNHUB_API_KEY   = {finnhub_key!r}\n'
        f'NEWSAPI_KEY       = {newsapi_key!r}\n',
        "secrets_local.py",
    )
    write_file_guarded(
        REPO_ROOT / "config_local.py",
        f'# GITIGNORED — personal (non-secret) config.\n'
        f'OWNER            = {owner_name!r}\n'
        f'TELEGRAM_CHAT_ID = {telegram_chat_id!r}\n',
        "config_local.py",
    )

    step(4, 5, "Python environment")
    if VENV_PY.exists():
        print(f"Virtual environment already exists at {VENV_DIR}, skipping creation.")
    else:
        print(f"Creating virtual environment at {VENV_DIR} ...")
        venv.EnvBuilder(with_pip=True).create(str(VENV_DIR))
    req_file = REPO_ROOT / "requirements.txt"
    print(f"Installing dependencies from {req_file} (this can take a minute) ...")
    run([str(VENV_PIP), "install", "-q", "-r", str(req_file)])

    step(5, 5, "Database")
    run([str(VENV_PY), str(REPO_ROOT / "database" / "setup_db.py")])

    banner("Done!")
    print(textwrap.dedent(f"""\
        Try an analysis directly from the terminal:
          {VENV_PY} agents/fundamental_agent.py AAPL
          {VENV_PY} agents/cio_agent.py AAPL       (full 5-agent CIO brief)

        To chat with Claudio and run analyses over Telegram, also set up
        https://github.com/iqnco/claude-telegram-bot as a sibling directory
        of this repo (see README.md for the "clone both, run both setups"
        flow) — it points at this repo's venv and agents automatically.
    """))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nA command failed: {e}")
        sys.exit(1)
