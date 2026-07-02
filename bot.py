import requests, time, os, sys, json, threading
from datetime import datetime

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

from secrets_local import TELEGRAM_TOKEN  # gitignored secret
from config_local import TELEGRAM_CHAT_ID, OWNER  # gitignored personal config
from config.settings import ANTHROPIC_API_KEY, MODEL_MAIN
from agents.cio_agent import run_full_analysis
from agents.fundamental_agent import run as run_fundamental
from agents.health_agent import run as run_health
from agents.technical_agent import run as run_technical
from agents.macro_agent import run as run_macro

import anthropic

ALLOWED_ID   = int(TELEGRAM_CHAT_ID)
API          = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
offset       = 0
HISTORY_PATH = os.path.join(BASE, "conversation_history.json")
MAX_HISTORY  = 25
HISTORY_LOCK = threading.Lock()

CLIENT = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def load_history():
    with HISTORY_LOCK:
        try:
            with open(HISTORY_PATH) as f: return json.load(f)
        except: return {}

def save_history(h):
    with HISTORY_LOCK:
        with open(HISTORY_PATH,"w") as f: json.dump(h,f)

def add_to_history(chat_id, role, content):
    h = load_history(); k = str(chat_id)
    if k not in h: h[k] = []
    h[k].append({"role":role,"content":content[:4000],"time":datetime.now().strftime("%Y-%m-%d %H:%M")})
    h[k] = h[k][-MAX_HISTORY:]
    save_history(h)

def send(chat_id, text):
    for chunk in [text[i:i+4000] for i in range(0,len(text),4000)]:
        requests.post(f"{API}/sendMessage", json={"chat_id":chat_id,"text":chunk})

def run_claude(chat_id, text):
    """Real multi-turn conversation via the Anthropic API (not the claude CLI),
    so the model actually sees prior turns as proper history instead of a
    flattened text blob — this is what gives it real memory."""
    prior = load_history().get(str(chat_id), [])[-MAX_HISTORY:]
    messages = [{"role": m["role"], "content": m["content"]} for m in prior]
    messages.append({"role": "user", "content": text})

    now_str = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    system = (
        f"You are Claudio, {OWNER}'s personal AI assistant running on their Mac.\n"
        f"You help with anything — research, analysis, quick questions, brainstorming, coding.\n"
        f"Be direct, smart, and concise — this is Telegram, not an essay.\n\n"
        f"Current date & time: {now_str}. Trust this over anything implied by earlier messages."
    )
    resp = CLIENT.messages.create(model=MODEL_MAIN, max_tokens=1500, system=system, messages=messages)
    return resp.content[0].text

def run_agent(fn, ticker, chat_id, label):
    send(chat_id, f"🔬 Running {label} on {ticker}...")
    try:
        result = fn(ticker)
        analysis = result[0] if isinstance(result, tuple) else result
        send(chat_id, analysis[-3500:])
    except Exception as e:
        send(chat_id, f"❌ {label} error: {e}")

def handle_message(msg):
    chat_id = msg.get("chat",{}).get("id")
    user_id = msg.get("from",{}).get("id")
    text    = msg.get("text","").strip()
    if user_id!=ALLOWED_ID or not chat_id or not text: return

    t = text.lower().strip()
    parts = text.split()

    if t.startswith(("analyze ","analyse ")):
        ticker = parts[1].upper() if len(parts)>1 else None
        if not ticker: send(chat_id,"Usage: analyze TICKER"); return
        send(chat_id,f"🏦 Full analysis on {ticker}...\n⏱ ~3 minutes. Stand by.")
        try:
            brief = run_full_analysis(ticker)
            send(chat_id, brief)
        except Exception as e:
            send(chat_id, f"❌ Analysis failed: {e}")

    elif t.startswith("quick "):
        if len(parts)>1: run_agent(run_fundamental, parts[1].upper(), chat_id, "Fundamental")
    elif t.startswith("technical "):
        if len(parts)>1: run_agent(run_technical, parts[1].upper(), chat_id, "Technical")
    elif t.startswith("health "):
        if len(parts)>1: run_agent(run_health, parts[1].upper(), chat_id, "Health")
    elif t.startswith("macro "):
        if len(parts)>1: run_agent(run_macro, parts[1].upper(), chat_id, "Macro")

    elif t in ["portfolio","positions","port","p"]:
        try:
            from agents.portfolio_tracker import get_portfolio_summary
            send(chat_id, get_portfolio_summary())
        except Exception as e: send(chat_id,f"❌ Portfolio error: {e}")

    elif t in ["clear","reset","new chat"]:
        h = load_history(); h[str(chat_id)]=[]; save_history(h)
        send(chat_id,"✅ Conversation cleared!")

    elif t in ["help","/help","/start","menu"]:
        send(chat_id,"""🏦 CLAUDIO INC. — COMMANDS

📊 ANALYSIS
- analyze TICKER — Full 5-agent CIO brief
- quick TICKER — Fundamental only
- technical TICKER — Chart analysis
- health TICKER — Balance sheet
- macro TICKER — Macro & live news

💰 PORTFOLIO
- portfolio — Open positions & P&L

💬 CHAT
- clear — Reset conversation history
- [anything] — Chat with Claudio
  (remembers last 25 messages)""")

    else:
        try:
            response = run_claude(chat_id, text)
        except Exception as e:
            send(chat_id, f"❌ Error: {e}")
            return
        add_to_history(chat_id,"user",text)
        add_to_history(chat_id,"assistant",response)
        send(chat_id, response)

if __name__ == "__main__":
    print("🏦 Claudio Inc. — Bot Online")
    consecutive_errors = 0
    MAX_ERRORS = 15
    while True:
        try:
            r = requests.get(f"{API}/getUpdates",params={"offset":offset,"timeout":20},timeout=25).json()
            consecutive_errors = 0
            for u in r.get("result",[]):
                offset = u["update_id"]+1
                msg = u.get("message",{})
                # Handle in a thread so a multi-minute analysis never blocks polling
                # — otherwise the bot looks unresponsive to any message sent while one is running.
                if msg: threading.Thread(target=handle_message, args=(msg,), daemon=True).start()
        except Exception as e:
            consecutive_errors += 1
            print(f"Error ({consecutive_errors}): {e}")
            if consecutive_errors >= MAX_ERRORS:
                print(f"Too many consecutive errors ({consecutive_errors}); exiting for launchd to restart with fresh sockets")
                sys.exit(1)
            time.sleep(5)
