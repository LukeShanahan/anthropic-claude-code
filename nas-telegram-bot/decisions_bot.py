#!/usr/bin/env python3
"""Run the routing decisions.py (shared register) from the Telegram bot.

The routing folder of the sfl-claude container is mounted at
/routing-home/.claude/aios/routing. The register is saved by write-then-rename,
which works for the bot user; the shared daily log files are created by root,
so this wrapper points the log at the bot's own /state/routing-log instead.
Usage: python3 /app/decisions_bot.py <decisions.py arguments>
"""
import json
import os
import runpy
import sys

HOME = "/routing-home"
ROUTING = HOME + "/.claude/aios/routing"
LOG_DIR = "/state/routing-log"

os.environ["HOME"] = HOME
with open(os.path.join(ROUTING, "config.json"), encoding="utf-8") as fh:
    cfg = json.load(fh)
cfg["paths"]["log_dir"] = LOG_DIR
os.makedirs(LOG_DIR, exist_ok=True)
tmp = "/tmp/sfl-routing-config.json"
with open(tmp, "w", encoding="utf-8") as fh:
    json.dump(cfg, fh)
os.environ["SFL_ROUTING_CONFIG"] = tmp

sys.path.insert(0, ROUTING)
sys.argv = [os.path.join(ROUTING, "decisions.py")] + sys.argv[1:]
runpy.run_path(sys.argv[0], run_name="__main__")
