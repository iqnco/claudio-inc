import requests, subprocess, time, os, sys, json, re
from datetime import datetime

from secrets_local import TELEGRAM_TOKEN  # gitignored secret
from config_local import TELEGRAM_CHAT_ID, OWNER  # gitignored personal config
ALLOWED_ID = int(TELEGRAM_CHAT_ID)
API        = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
offset     = 0
BASE         = os.path.dirname(os.path.abspath(__file__))
HISTORY_PATH = os.path.join(BASE, "conversation_history.json")
MAX_HISTORY  = 25
VENV_PY      = os.path.join(BASE, "venv", "bin", "python3")
# Clean env for agent subprocesses: drop PYTHONPATH so the venv's own (working) site-packages win
AGENT_ENV    = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
AGENT_ENV["PATH"] = f"{os.path.expanduser('~/.local/bin')}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"

def load_history():
    try:
        with open(HISTORY_PATH) as f: return json.load(f)
    except: return {}

def save_history(h):
    with open(HISTORY_PATH,"w") as f: json.dump(h,f)

def add_to_history(chat_id, role, content):
    h = load_history(); k = str(chat_id)
    if k not in h: h[k] = []
    h[k].append({"role":role,"content":content[:4000],"time":datetime.now().strftime("%Y-%m-%d %H:%M")})
    h[k] = h[k][-MAX_HISTORY:]
    save_history(h)

def get_context(chat_id):
    msgs = load_history().get(str(chat_id),[])
    if not msgs: return ""
    ctx = "CONVERSATION HISTORY (most recent last; timestamps are real — use them to judge what's current):\n"
    for m in msgs:
        who = OWNER if m["role"] == "user" else "Claudio"
        ctx += f"[{m.get('time','?')}] {who}: {m['content']}\n"
    return ctx

def send(chat_id, text):
    for chunk in [text[i:i+4000] for i in range(0,len(text),4000)]:
        requests.post(f"{API}/sendMessage", json={"chat_id":chat_id,"text":chunk})

def run_claude(chat_id, text):
    ctx = get_context(chat_id)
    now = datetime.now().strftime("%A, %B %d, %Y at %H:%M")
    prompt = f"""You are Claudio, {OWNER}'s personal AI assistant running on their Mac.
You help with anything — emails, research, scheduling, analysis, coding, questions.
You are direct, smart, and remember the conversation context.

CURRENT DATE & TIME: {now}. This is authoritative — trust it over any date implied by older messages.

{ctx}

{OWNER}: {text}

Use the conversation history above to stay in context — {OWNER} expects you to remember what was already said and not re-ask. If something in the history is from an earlier day, treat the CURRENT DATE above as now."""
    result = subprocess.run(["claude","-p",prompt],
        capture_output=True, text=True, timeout=120,
        env={**os.environ,"PATH":f"{os.path.expanduser('~/.local/bin')}:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"})
    return result.stdout.strip() or "No response"

def run_agent(script, ticker, chat_id, label):
    send(chat_id, f"🔬 Running {label} on {ticker}...")
    try:
        r = subprocess.run(
            [VENV_PY, os.path.join(BASE, "agents", script), ticker],
            capture_output=True, text=True, timeout=300, env=AGENT_ENV)
        out = r.stdout.strip()
        send(chat_id, out[-3500:] if out else f"❌ No output from {label}.\n{(r.stderr or '').strip()[-1500:]}")
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
            r = subprocess.run(
                [VENV_PY, os.path.join(BASE, "agents", "cio_agent.py"), ticker],
                capture_output=True, text=True, timeout=600, env=AGENT_ENV)
            out = r.stdout.strip()
            if "🏦" in out:
                send(chat_id, out[out.rfind("🏦"):])
            elif out:
                send(chat_id, out[-3500:])
            else:
                send(chat_id, f"❌ Analysis failed.\n{(r.stderr or '').strip()[-1500:]}")
        except Exception as e: send(chat_id,f"❌ Error: {e}")

    elif t.startswith("quick "):
        if len(parts)>1: run_agent("fundamental_agent.py",parts[1].upper(),chat_id,"Fundamental")
    elif t.startswith("technical "):
        if len(parts)>1: run_agent("technical_agent.py",parts[1].upper(),chat_id,"Technical")
    elif t.startswith("health "):
        if len(parts)>1: run_agent("health_agent.py",parts[1].upper(),chat_id,"Health")
    elif t.startswith("macro "):
        if len(parts)>1: run_agent("macro_agent.py",parts[1].upper(),chat_id,"Macro")

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
        add_to_history(chat_id,"user",text)
        response = run_claude(chat_id, text)
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
                if msg: handle_message(msg)
        except Exception as e:
            consecutive_errors += 1
            print(f"Error ({consecutive_errors}): {e}")
            if consecutive_errors >= MAX_ERRORS:
                print(f"Too many consecutive errors ({consecutive_errors}); exiting for launchd to restart with fresh sockets")
                sys.exit(1)
            time.sleep(5)
