#!/usr/bin/env python3
"""SFL Telegram bot: relays Luke's Telegram messages to Claude Code on the NAS.

* Long polling only: no inbound ports, nothing exposed to the internet.
* Answers only TELEGRAM_ALLOWED_CHAT_ID; every other sender is ignored and logged.
* One conversation at a time; /new starts a fresh one.
* Files Luke sends land in /workspace/inbox; files Claude puts in
  /workspace/outbox are sent back after the reply.

Commands: /new  /status  /changes  /help
"""
import json
import os
import subprocess
import sys
import threading
import time
import queue
import urllib.parse
import urllib.request

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED = int(os.environ["TELEGRAM_ALLOWED_CHAT_ID"])
WORKSPACE = os.environ.get("SFL_WORKSPACE", "/workspace")
STATE_DIR = os.environ.get("SFL_STATE_DIR", "/state")
SESSION_FILE = os.path.join(STATE_DIR, "claude_session.json")
TIMEOUT = int(os.environ.get("CLAUDE_TIMEOUT_SECONDS", "1800"))
API = f"https://api.telegram.org/bot{TOKEN}"
FILE_API = f"https://api.telegram.org/file/bot{TOKEN}"
INBOX = os.path.join(WORKSPACE, "inbox")
OUTBOX = os.path.join(WORKSPACE, "outbox")

# What Claude may do without asking. Anything not listed is refused in -p mode.
ALLOWED_TOOLS = [
    "Bash(python3 /app/smokeball.py:*)",
    "Bash(ls:*)", "Bash(mkdir:*)", "Bash(cp:*)", "Bash(mv:*)", "Bash(pdftotext:*)",
    "Read", "Write", "Edit", "Glob", "Grep", "WebFetch", "WebSearch", "TodoWrite",
]
DISALLOWED_TOOLS = ["Bash(rm:*)", "Bash(curl:*)", "Bash(wget:*)"]

jobs = queue.Queue()


def log(*a):
    print(time.strftime("%Y-%m-%d %H:%M:%S"), *a, flush=True)


def tg(method, timeout=70, **params):
    data = urllib.parse.urlencode(params).encode()
    with urllib.request.urlopen(f"{API}/{method}", data=data, timeout=timeout) as r:
        return json.load(r)


def send(text):
    text = text.strip() or "(no reply)"
    for i in range(0, len(text), 4000):
        tg("sendMessage", chat_id=ALLOWED, text=text[i:i + 4000])


def send_file(path):
    boundary = "----sflbot" + str(time.time_ns())
    name = os.path.basename(path)
    with open(path, "rb") as f:
        content = f.read()
    body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{ALLOWED}\r\n"
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"document\"; filename=\"{name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + content + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{API}/sendDocument", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    urllib.request.urlopen(req, timeout=120).read()


def load_session():
    try:
        with open(SESSION_FILE) as f:
            return json.load(f).get("session_id")
    except (OSError, ValueError):
        return None


def save_session(sid):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(SESSION_FILE, "w") as f:
        json.dump({"session_id": sid, "updated": time.time()}, f)


def keep_typing(stop):
    while not stop.is_set():
        try:
            tg("sendChatAction", timeout=10, chat_id=ALLOWED, action="typing")
        except Exception:
            pass
        stop.wait(5)


def run_claude(prompt, sid):
    cmd = ["claude", "-p", prompt, "--output-format", "json",
           "--allowedTools", *ALLOWED_TOOLS, "--disallowedTools", *DISALLOWED_TOOLS]
    if sid:
        cmd += ["--resume", sid]
    p = subprocess.run(cmd, cwd=WORKSPACE, capture_output=True, text=True, timeout=TIMEOUT)
    try:
        return json.loads(p.stdout), p
    except ValueError:
        return None, p


def handle(prompt):
    before = set(os.listdir(OUTBOX))
    stop = threading.Event()
    threading.Thread(target=keep_typing, args=(stop,), daemon=True).start()
    try:
        sid = load_session()
        out, p = run_claude(prompt, sid)
        if out is None and sid:  # stale session: start fresh once
            log("resume failed, starting new session:", p.stderr[-300:])
            out, p = run_claude(prompt, None)
        if out is None:
            send(f"Claude failed to run (exit {p.returncode}).\n{p.stderr[-1500:]}")
            return
        if out.get("session_id"):
            save_session(out["session_id"])
        send(out.get("result") or json.dumps(out)[:3500])
    except subprocess.TimeoutExpired:
        send(f"Stopped: the task ran longer than {TIMEOUT // 60} minutes.")
    finally:
        stop.set()
    for name in sorted(set(os.listdir(OUTBOX)) - before):
        try:
            send_file(os.path.join(OUTBOX, name))
        except Exception as e:
            send(f"Could not send {name}: {e}")


def worker():
    while True:
        prompt = jobs.get()
        try:
            handle(prompt)
        except Exception as e:
            log("job error:", repr(e))
            try:
                send(f"Error: {e}")
            except Exception:
                pass


def save_incoming_file(msg):
    doc = msg.get("document") or (msg.get("photo") or [None])[-1]
    if not doc:
        return None
    info = tg("getFile", file_id=doc["file_id"])["result"]
    name = doc.get("file_name") or os.path.basename(info["file_path"])
    dest = os.path.join(INBOX, time.strftime("%Y%m%d-%H%M%S-") + name)
    with urllib.request.urlopen(f"{FILE_API}/{info['file_path']}", timeout=120) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def on_message(msg):
    chat = msg.get("chat", {}).get("id")
    if chat != ALLOWED:
        log("ignored message from chat", chat)
        return
    text = (msg.get("text") or msg.get("caption") or "").strip()
    if text in ("/start", "/help"):
        send("Send a task in plain words. /new starts a fresh conversation, "
             "/status shows the queue, /changes lists recent Smokeball changes.")
        return
    if text == "/new":
        save_session(None)
        send("Started a new conversation.")
        return
    if text == "/status":
        send(f"{jobs.qsize()} task(s) waiting. Session: {load_session() or 'new'}")
        return
    if text == "/changes":
        p = subprocess.run(["python3", "/app/smokeball.py", "history", "10"], capture_output=True, text=True)
        send(p.stdout or p.stderr)
        return
    path = save_incoming_file(msg)
    if path:
        text = f"{text}\n\n[Luke attached a file, saved at {path}]".strip()
    if not text:
        return
    jobs.put(text)
    if jobs.qsize() > 1:
        send(f"Queued ({jobs.qsize()} waiting).")


def main():
    for d in (INBOX, OUTBOX, STATE_DIR):
        os.makedirs(d, exist_ok=True)
    threading.Thread(target=worker, daemon=True).start()
    offset = 0
    log("bot started; allowed chat", ALLOWED)
    while True:
        try:
            res = tg("getUpdates", offset=offset, timeout=50)
            for upd in res.get("result", []):
                offset = upd["update_id"] + 1
                if "message" in upd:
                    on_message(upd["message"])
        except Exception as e:
            log("poll error:", repr(e))
            time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
