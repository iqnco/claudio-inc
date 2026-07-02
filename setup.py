#!/usr/bin/env python3
"""
Claudio Inc. — setup wizard.

Run this once after cloning the repo:

    python3 setup.py

It walks you through the API keys the analysis agents (and the Telegram
bot) need, creates a virtual environment, installs dependencies,
initializes the local SQLite database, and optionally sets up the bot
to auto-start on login.

No third-party packages are required to run this script itself — only
the Python standard library.
"""

import getpass
import os
import platform
import re
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


def ask_yes_no(prompt, default=False):
    d = "Y/n" if default else "y/N"
    raw = input(f"{prompt} [{d}]: ").strip().lower()
    if not raw:
        return default
    return raw in ("y", "yes")


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
    print("This configures the analysis agents and the Telegram bot.\n")
    print(f"Repo location: {REPO_ROOT}")

    step(1, 7, "Anthropic API key")
    print("Used by every agent to write its analysis. Get one at:")
    print("  https://console.anthropic.com/settings/keys\n")
    anthropic_key = ask_secret(
        "Paste your Anthropic API key",
        validate=lambda v: v.startswith("sk-ant-"),
        error_msg='Anthropic keys start with "sk-ant-". Try again.',
    )

    step(2, 6, "Market-data API keys")
    print(textwrap.dedent("""\
        Two free-tier API keys power the macro agent's news/sentiment data
        (fundamentals/technicals/risk all come from yfinance, no key needed):
          Finnhub   (news/sentiment/earnings) — https://finnhub.io/register
          NewsAPI   (macro news)              — https://newsapi.org/register
        Both have free tiers. Leave either blank to skip that data source.
    """))
    finnhub_key = ask_secret("Paste your Finnhub API key", optional=True)
    newsapi_key = ask_secret("Paste your NewsAPI key", optional=True)

    step(3, 6, "Telegram bot")
    print(textwrap.dedent("""\
        1. Open Telegram and message @BotFather
        2. Send: /newbot
        3. Give it a name and a username (must end in "bot")
        4. BotFather replies with a token like: 123456789:AAExampleTokenTextGoesHere
        Leave blank to skip Telegram entirely (agents still work standalone
        from the terminal, just no bot.py).
    """))
    telegram_token = ask_secret(
        "Paste your bot token (or leave blank to skip)",
        optional=True,
        validate=lambda v: bool(re.match(r"^\d+:[\w-]+$", v)),
        error_msg='That doesn\'t look like a bot token (expected "digits:letters"). Try again.',
    )
    owner_name = ask("What's your first name? (used in agent and bot prompts)", default="there")
    telegram_chat_id = ""
    if telegram_token:
        print("\nGet your numeric Telegram user ID by messaging @userinfobot.")
        telegram_chat_id = ask(
            "Your numeric Telegram chat ID (the bot only responds to this ID)",
            validate=lambda v: v.isdigit(),
            error_msg="That should be a number. Try again.",
        )

    write_file_guarded(
        REPO_ROOT / "secrets_local.py",
        f'# GITIGNORED — real secrets.\n'
        f'TELEGRAM_TOKEN    = {telegram_token!r}\n'
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

    step(4, 6, "Python environment")
    if VENV_PY.exists():
        print(f"Virtual environment already exists at {VENV_DIR}, skipping creation.")
    else:
        print(f"Creating virtual environment at {VENV_DIR} ...")
        venv.EnvBuilder(with_pip=True).create(str(VENV_DIR))
    req_file = REPO_ROOT / "requirements.txt"
    print(f"Installing dependencies from {req_file} (this can take a minute) ...")
    run([str(VENV_PIP), "install", "-q", "-r", str(req_file)])

    step(5, 6, "Database")
    run([str(VENV_PY), str(REPO_ROOT / "database" / "setup_db.py")])

    step(6, 6, "Auto-start")
    if not telegram_token:
        print("No Telegram bot configured — nothing to auto-start.")
    elif platform.system() != "Darwin":
        print(f"Run manually with:\n  {VENV_PY} {REPO_ROOT / 'bot.py'}")
    elif ask_yes_no("Set up bot.py auto-start on login via launchd (macOS)?", default=True):
        label = "com.claudioinc.bot"
        plist_path = Path.home() / "Library" / "LaunchAgents" / f"{label}.plist"
        log_path = REPO_ROOT / "bot.log"
        plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{VENV_PY}</string>
        <string>-u</string>
        <string>{REPO_ROOT / 'bot.py'}</string>
    </array>
    <key>WorkingDirectory</key><string>{REPO_ROOT}</string>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><true/>
    <key>StandardOutPath</key><string>{log_path}</string>
    <key>StandardErrorPath</key><string>{log_path}</string>
</dict>
</plist>
"""
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(plist)
        print(f"Wrote {plist_path}")
        try:
            subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)])
            print(f"\nBot is now running and will auto-start on login.")
            print(f"Restart: launchctl kickstart -k gui/$(id -u)/{label}")
            print(f"Logs:    tail -f {log_path}")
        except subprocess.CalledProcessError:
            print(f"Could not load automatically — run: launchctl bootstrap gui/$(id -u) {plist_path}")
    else:
        print(f"Skipping. Run manually with:\n  {VENV_PY} {REPO_ROOT / 'bot.py'}")

    banner("Done!")
    print(textwrap.dedent(f"""\
        Try an analysis directly from the terminal:
          {VENV_PY} agents/fundamental_agent.py AAPL
          {VENV_PY} agents/cio_agent.py AAPL       (full 5-agent CIO brief)
    """))
    if telegram_token:
        print("Message your bot on Telegram — try \"help\" for the command list.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup cancelled.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"\nA command failed: {e}")
        sys.exit(1)
