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

### 3. NAS
1. ADM > App Central: install **Docker Engine** and **Portainer**.
2. Create a folder **outside the Firm share**, e.g. `Docker/sfl-telegram-bot`
   (the Firm share `F:\` is add-only and must not hold this).
3. Copy this whole `nas-telegram-bot` folder into it.
4. Copy `secrets.env.example` to `secrets.env`, fill in the Telegram and
   Smokeball values. Leave `CLAUDE_CODE_OAUTH_TOKEN` for step 5.
5. Claude sign-in token: on any PC with Claude Code, run `claude setup-token`,
   sign in with Luke's Claude account, and paste the token it prints into
   `secrets.env` as `CLAUDE_CODE_OAUTH_TOKEN`. (An Anthropic API key in
   `ANTHROPIC_API_KEY` also works, billed per use.)
6. Restrict the file: via SSH, `chmod 600 secrets.env`, or in File Explorer
   remove access for everyone except admin.
7. Start it: Portainer > Stacks > Add stack > "Upload"/"Repository" pointing at
   `docker-compose.yml`, or via SSH in that folder: `docker compose up -d --build`.
8. Check: `docker logs sfl-telegram-bot` should show `bot started`. Message the
   bot "list the folders in the Stringybark matter".

## Using it

- Send a task in plain words. Replies come back in the same chat.
- `/new` starts a fresh conversation, `/status` shows queued tasks,
  `/changes` lists the last 10 Smokeball writes.
- Send a file and Claude finds it in `inbox/`; files Claude makes come back as
  attachments.

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

Edit files here, copy them to the NAS folder, then `docker compose up -d --build`.
