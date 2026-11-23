#!/usr/bin/env python3
"""Smokeball API client for the SFL Telegram bot (runs on the NAS).

Usage (Claude calls this; you can too):
  smokeball.py get    <path> [--query k=v ...] [--all]
  smokeball.py post   <path> --json '<body>' --reason "<why>"
  smokeball.py put    <path> --json '<body>' --reason "<why>"
  smokeball.py patch  <path> --json '<body>' --reason "<why>"
  smokeball.py download <url-or-path> <local-file>
  smokeball.py history [N]

Rules enforced here, not just in instructions:
  * DELETE is never sent (Luke's standing rule: Smokeball is never deleted from).
  * Every write is logged to the audit log, with the record's state before a
    PUT/PATCH, so any change can be reversed by hand.

Secrets come from environment variables (set in secrets.env, never in chat):
  SMOKEBALL_CLIENT_ID, SMOKEBALL_CLIENT_SECRET, SMOKEBALL_API_KEY
"""
import argparse
import base64
import datetime as dt
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = os.environ.get("SMOKEBALL_AUTH_URL", "https://auth.smokeball.com.au/oauth2/token")
API_BASE = os.environ.get("SMOKEBALL_API_BASE", "https://api.smokeball.com.au").rstrip("/")
STATE_DIR = os.environ.get("SFL_STATE_DIR", "/state")
TOKEN_FILE = os.path.join(STATE_DIR, "smokeball_token.json")
AUDIT_LOG = os.path.join(STATE_DIR, "smokeball_audit.jsonl")
WRITE_METHODS = {"POST", "PUT", "PATCH"}


class SmokeballError(Exception):
    pass


def _env(name):
    v = os.environ.get(name)
    if not v:
        raise SmokeballError(f"{name} is not set (add it to secrets.env)")
    return v


def _now():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def get_token(force=False):
    if not force:
        try:
            with open(TOKEN_FILE) as f:
                cached = json.load(f)
            if cached["expires_at"] - 120 > time.time():
                return cached["access_token"]
        except (OSError, ValueError, KeyError):
            pass
    cid, secret = _env("SMOKEBALL_CLIENT_ID"), _env("SMOKEBALL_CLIENT_SECRET")
    basic = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": cid}).encode()
    req = urllib.request.Request(AUTH_URL, data=body, method="POST", headers={
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
    except urllib.error.HTTPError as e:
        raise SmokeballError(f"token request failed: HTTP {e.code} {e.read()[:200]!r}")
    os.makedirs(STATE_DIR, exist_ok=True)
    fd = os.open(TOKEN_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump({"access_token": data["access_token"],
                   "expires_at": time.time() + int(data.get("expires_in", 3600))}, f)
    return data["access_token"]


def _url(path, query=None):
    if path.startswith("http"):
        if not path.startswith(API_BASE + "/"):
            raise SmokeballError(f"refusing non-Smokeball API URL: {path}")
        url = path
    else:
        url = f"{API_BASE}/{path.lstrip('/')}"
    if query:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode(query)
    return url


def request(method, path, body=None, query=None, raw=False):
    method = method.upper()
    if method == "DELETE":
        raise SmokeballError("DELETE is blocked: Smokeball is never deleted from. "
                             "Label the item and list it for staff instead.")
    if method not in WRITE_METHODS | {"GET"}:
        raise SmokeballError(f"method {method} not allowed")
    url = _url(path, query)
    for attempt in range(4):
        headers = {"Authorization": f"Bearer {get_token(force=attempt == 1)}",
                   "x-api-key": _env("SMOKEBALL_API_KEY"),
                   "Accept": "application/json"}
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                payload = r.read()
                if raw:
                    return payload
                return json.loads(payload) if payload.strip() else {"status": r.status}
        except urllib.error.HTTPError as e:
            if e.code == 401 and attempt == 0:
                continue  # refresh token once
            if e.code == 429 and attempt < 3:
                time.sleep(2 ** attempt)  # Smokeball rate limit is 5 req/s
                continue
            raise SmokeballError(f"{method} {url} -> HTTP {e.code}: {e.read()[:500].decode(errors='replace')}")
    raise SmokeballError(f"{method} {url} failed after retries")


def get_all(path, query=None):
    """Follow Smokeball paging ('next' links) and return every item."""
    out, page = [], request("GET", path, query=query)
    while True:
        items = page.get("value") if isinstance(page, dict) else None
        if items is None:
            return page
        out.extend(items)
        nxt = (page.get("next") or {}).get("href") if isinstance(page.get("next"), dict) else page.get("next")
        if not nxt:
            return out
        page = request("GET", nxt)


def _audit(entry):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(AUDIT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")


def write(method, path, body, reason):
    if not reason or len(reason.strip()) < 5:
        raise SmokeballError("every write needs --reason (what Luke asked for)")
    before = None
    if method.upper() in {"PUT", "PATCH"}:
        try:
            before = request("GET", path)
        except SmokeballError as e:
            before = f"(could not read before-state: {e})"
    entry = {"time": _now(), "method": method.upper(), "path": path,
             "reason": reason, "body": body, "before": before}
    _audit({**entry, "status": "attempt"})
    result = request(method, path, body=body)
    _audit({**entry, "status": "done", "result": result})
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("get")
    g.add_argument("path")
    g.add_argument("--query", nargs="*", default=[])
    g.add_argument("--all", action="store_true", help="follow paging")
    for m in ("post", "put", "patch"):
        w = sub.add_parser(m)
        w.add_argument("path")
        w.add_argument("--json", required=True)
        w.add_argument("--reason", required=True)
    d = sub.add_parser("download")
    d.add_argument("src")
    d.add_argument("dest")
    h = sub.add_parser("history")
    h.add_argument("n", nargs="?", type=int, default=20)
    sub.add_parser("delete").add_argument("path", nargs="?")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "delete":
            request("DELETE", a.path or "")
        elif a.cmd == "get":
            q = dict(kv.split("=", 1) for kv in a.query)
            res = get_all(a.path, q) if a.all else request("GET", a.path, query=q)
            print(json.dumps(res, indent=2))
        elif a.cmd in ("post", "put", "patch"):
            print(json.dumps(write(a.cmd, a.path, json.loads(a.json), a.reason), indent=2))
        elif a.cmd == "download":
            if a.src.startswith("https://") and not a.src.startswith(API_BASE + "/"):
                # pre-signed file URL returned by the API: fetch without our headers
                with urllib.request.urlopen(a.src, timeout=120) as r:
                    data = r.read()
            else:
                data = request("GET", a.src, raw=True)
            with open(a.dest, "wb") as f:
                f.write(data)
            print(f"saved {len(data)} bytes to {a.dest}")
        elif a.cmd == "history":
            try:
                with open(AUDIT_LOG) as f:
                    lines = f.readlines()[-a.n:]
            except OSError:
                lines = []
            print("".join(lines) or "no writes logged")
    except SmokeballError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
