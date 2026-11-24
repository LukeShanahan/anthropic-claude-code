# SFL Telegram bot on the NAS

Lets Luke give Claude tasks by Telegram while his PCs are off. The bot and
Claude Code run in a Docker container on the Asustor AS5402T NAS
(192.168.20.159), and Claude reads and writes Smokeball through the API.

```
Telegram  <-- outbound polling --  NAS container: bot.py -> claude -p -> smokeball.py -> Smokeball API
```

- No ports opened; the container only makes outbound connections.
- Answers one Telegram chat (Luke's); everyone else is ignored.
- Smokeball DELETE is blocked in code; every write is logged with its prior state.
- Claude's tools are limited to the Smokeball client, file reading/writing in its
  workspace, and web reading (`ALLOWED_TOOLS` in `bot.py`).

## One-off setup

### 1. Smokeball app (Developer Console, console.smokeball.com)
Use the "SFL Cloud Read-only" app (rename it, e.g. "SFL NAS bot"):
- Edit scopes: keep the `/read` scopes you want and add the write scopes the
  bot needs, at least `matters/write` and `documents/write` (both are needed to
  add files to a matter). Add `memos/write`, `tasks/write` etc. only if wanted.
- Set the access token expiry to 1 hour.
- Note the client ID and client secret, and the AU API Key (API page).

### 2. Telegram bot
- In Telegram, message **@BotFather** > `/newbot` > follow the prompts; copy the token.
  (Or reuse the mini PC bot's token, but then stop the mini PC bot: only one
  program can receive a bot's messages at a time.)
- Message **@userinfobot** to get your numeric chat id.

### 3. NAS (as deployed 24 Nov 2026)
Docker Engine and Portainer were already installed (Portainer at
http://192.168.20.159:19900). The SFL NAS cannot use `docker-compose.yml` and the
`Dockerfile` as they stand: plain-http apt mirrors are blocked on the office
network, and a Portainer stack cannot build from, or read `env_file` in, a share
folder. So the live set-up uses `portainer-stack.yml` and `start.sh` instead:

1. Folder **outside the Firm share**: `\\192.168.20.159\Docker\sfl-telegram-bot`
   (= `/share/Docker/sfl-telegram-bot`), holding `start.sh`, `app/` (bot.py,
   smokeball.py, decisions_bot.py), `workspace/`, `state/`, `home/`,
   `portainer-stack.yml` and `secrets.env`.
2. Secrets: Luke double-clicks the Desktop shortcut "Set up NAS Telegram bot",
   which runs `Set-BotSecrets.ps1`. It runs `claude setup-token` (Luke signs in)
   and picks each value up from the clipboard (Telegram code, Smokeball client
   ID, client secret and AU API key), so nothing is typed into a chat. "Update
   NAS bot Telegram code" (`-TelegramOnly`) replaces just the Telegram code; it
   also refreshes the routing digest's copy (`sfl-claude/home/.config/sfl/telegram-bot.env`).
3. Portainer > Stacks > Add stack > Web editor: paste `portainer-stack.yml`
   (image `node:22-bookworm`, host network, 2 GB, no build, no env_file).
   `start.sh` reads `secrets.env` (and sets it to owner-only), installs
   poppler-utils over https and Claude Code once into `home/`, then runs the bot
   as the unprivileged user `sfl` (1001). `app/` is mounted read-only.
4. Check: Portainer > Containers > sfl-telegram-bot > Logs shows `bot started`.
   Message the bot "list the folders in the Stringybark matter".

The original route (SSH, `docker compose up -d --build` with the Dockerfile)
still suits a Docker host with normal internet access.

## Using it

- Send a task in plain words. Replies come back in the same chat.
- `/new` starts a fresh conversation, `/status` shows queued tasks,
  `/changes` lists the last 10 Smokeball writes.
- Send a file and Claude finds it in `inbox/`; files Claude makes come back as
  attachments.
- Decision replies to the 7:45 am routing digest ("D3 b") are recorded in the
  shared register through `app/decisions_bot.py` (the routing folder of the
  `sfl-claude` container is mounted at `/routing-home/.claude/aios/routing`; the
  bot's decision log goes to `state/routing-log`). The digest itself is sent
  through this bot by the NAS routine runner (sendMessage only, so it does not
  clash with the bot's polling).
- On a Telegram 429 the bot waits the `retry_after` Telegram gives instead of
  retrying every few seconds.

## Reversing a change

`/changes` (or `state/smokeball_audit.jsonl` on the NAS) shows every write with
the record as it was before. Ask the bot to restore it, or do it in Smokeball.

## Limits

- The NAS has 4 GB RAM; the container is capped at 2 GB and runs one task at a time.
- Claude here has none of the PC connectors (Outlook, Plaud, Read AI, Xero,
  computer use) and none of the PC skills, only what is in `workspace/CLAUDE.md`.
- Smokeball's API key is shared with the PC scripts (5 requests/second).
- Tasks are stopped after 30 minutes (`CLAUDE_TIMEOUT_SECONDS`).

## Updating

Edit files here, copy them to the NAS folder (`app/` files into `app/`), then
restart the container in Portainer (or "Update the stack" if
`portainer-stack.yml` changed). With the Dockerfile route: `docker compose up -d --build`.
