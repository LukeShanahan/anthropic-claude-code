#!/bin/bash
# SFL NAS Telegram bot start-up (24 Nov 2026). Image node:22-bookworm already has python3, curl and git.
# Plain-http (port 80) is blocked on the office network, so apt uses https and Claude Code comes from claude.ai.
# Runs as root only to prepare, then drops to the unprivileged user "sfl" (uid 1001) to run the bot.
set -u
export TZ=Australia/Brisbane
log() { echo "$(date '+%F %T') start: $*"; }

# 1. Secrets: read from the mounted file (never printed), lock the file to its owner, export for the bot.
SECRETS=/run/sfl/secrets.env
[ -f "$SECRETS" ] || { log "secrets.env missing"; sleep 3600; exit 1; }
chmod 600 "$SECRETS" 2>/dev/null || log "could not chmod secrets.env"
while IFS= read -r line || [ -n "$line" ]; do
  line="${line%$'\r'}"
  case "$line" in ''|\#*) continue ;; esac
  k="${line%%=*}"; v="${line#*=}"
  [ -n "$v" ] && export "$k=$v"
done < "$SECRETS"
for k in TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_CHAT_ID SMOKEBALL_CLIENT_ID SMOKEBALL_CLIENT_SECRET SMOKEBALL_API_KEY; do
  [ -n "${!k:-}" ] || { log "$k is empty in secrets.env"; sleep 3600; exit 1; }
done
[ -n "${CLAUDE_CODE_OAUTH_TOKEN:-}${ANTHROPIC_API_KEY:-}" ] || { log "no Claude token in secrets.env"; sleep 3600; exit 1; }

# 2. Bot user and folders it may write to. /app is mounted read-only, so Claude cannot edit the bot or the
#    Smokeball client (and its no-DELETE guard).
id sfl >/dev/null 2>&1 || useradd -M -u 1001 -d /home/sfl -s /bin/bash sfl
mkdir -p /workspace/inbox /workspace/outbox /state /home/sfl
chown -R sfl:sfl /workspace /state /home/sfl

# 3. pdftotext (optional): apt over https.
if ! command -v pdftotext >/dev/null; then
  sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null
  (apt-get update -qq && apt-get install -y -qq --no-install-recommends poppler-utils) >/dev/null 2>&1 \
    && log "installed poppler-utils" || log "poppler-utils not installed (pdftotext unavailable)"
fi

# 4. Claude Code, installed once into the bot user's persistent home.
export HOME=/home/sfl PATH="/home/sfl/.local/bin:$PATH"
if [ ! -x /home/sfl/.local/bin/claude ]; then
  log "installing Claude Code"
  setpriv --reuid=1001 --regid=1001 --init-groups bash -c 'curl -fsSL https://claude.ai/install.sh | bash' \
    || { log "Claude Code install failed"; sleep 600; exit 1; }
fi
log "claude $(setpriv --reuid=1001 --regid=1001 --init-groups claude --version 2>/dev/null)"

# 5. Run the bot as sfl.
cd /workspace
exec setpriv --reuid=1001 --regid=1001 --init-groups python3 -u /app/bot.py
