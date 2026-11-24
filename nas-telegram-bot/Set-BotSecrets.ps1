# Guided set-up of secrets.env for the SFL NAS Telegram bot.
# Luke runs it by double-clicking "Set up NAS Telegram bot" on his Desktop. Each value is copied to the
# clipboard and picked up from there, so nothing has to be typed and nothing goes into a chat or a log.
param([switch]$TelegramOnly)   # -TelegramOnly: replace just the Telegram bot code, keep the rest
$ErrorActionPreference = 'Stop'
$path = Join-Path $PSScriptRoot 'secrets.env'
$claude = Join-Path $env:USERPROFILE '.local\bin\claude.exe'

function Say([string]$t, [string]$c = 'White') { Write-Host $t -ForegroundColor $c }
function Wait-Enter([string]$t = 'Press Enter when ready') { [void](Read-Host "  >> $t") }
function Tail([string]$v) { if ($v.Length -gt 4) { '...' + $v.Substring($v.Length - 4) } else { '(short)' } }

function Get-FromClipboard([string]$name, [string]$pattern, [string]$find) {
    # $find: pick the code out of a longer copied message (the last match wins).
    while ($true) {
        Wait-Enter "When you have copied the $name, press Enter"
        $v = (Get-Clipboard -Raw)
        if ($v -and $find) {
            $m = [regex]::Matches($v, $find)
            $v = if ($m.Count) { $m[$m.Count - 1].Value } else { $null }
        }
        if ($v) { $v = ($v -replace '\s', '') }
        if ($v -and $v -match $pattern) { Say "     Got it (ends in $(Tail $v))." 'Green'; return $v }
        Say "     That doesn't look like the $name. Please copy it again." 'Yellow'
    }
}

function Save-DigestCopy([string]$tok) {
    # The routing digest and the routine runner's notices send through the same bot (sendMessage only).
    $d = '\\192.168.20.159\Docker\sfl-claude\home\.config\sfl\telegram-bot.env'
    $t = "# Bot @sfl_claude_nas_bot, for routing digests and runner notices (sendMessage only).`n# Written by Set-BotSecrets.ps1 from sfl-telegram-bot/secrets.env. Never print it.`nTELEGRAM_BOT_TOKEN=$tok`n"
    try { [IO.File]::WriteAllText($d, $t, (New-Object Text.UTF8Encoding $false)); Say '     Digest copy updated.' 'Green' }
    catch { Say "     Could not update the digest copy ($d). Tell Claude." 'Yellow' }
}

$tgFind = '\d{6,}:[A-Za-z0-9_\-]{30,}'
$tgSteps = @(
    '  In Chrome, open Telegram and the BotFather chat.',
    '  Right-click BotFather''s LAST message (it ends with the new code) and choose "Copy Text".',
    '  (Copying the whole message is fine: this window picks the code out of it.)'
)

if ($TelegramOnly) {
    Clear-Host
    Say '=== Update the Telegram bot code ===' 'Cyan'
    $tgSteps | ForEach-Object { Say $_ }
    $tgToken = Get-FromClipboard 'Telegram message' '^\d{6,}:[A-Za-z0-9_\-]{30,}$' $tgFind
    $lines = Get-Content $path | ForEach-Object { if ($_ -like 'TELEGRAM_BOT_TOKEN=*') { "TELEGRAM_BOT_TOKEN=$tgToken" } else { $_ } }
    [IO.File]::WriteAllText($path, (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))
    Save-DigestCopy $tgToken
    Set-Clipboard -Value ' '
    Say ''
    Say 'Saved. The clipboard has been cleared.' 'Green'
    Say 'Go back to the Claude chat and say "token updated".' 'Green'
    Wait-Enter 'Press Enter to close this window'
    exit
}

function Find-ClaudeToken {
    try {
        $raw = $Host.UI.RawUI
        $rect = New-Object Management.Automation.Host.Rectangle 0, 0, ($raw.BufferSize.Width - 1), ($raw.CursorPosition.Y)
        $cells = $raw.GetBufferContents($rect)
        $sb = New-Object Text.StringBuilder
        foreach ($cell in $cells) { [void]$sb.Append($cell.Character) }
        $m = [regex]::Matches(($sb.ToString() -replace '\s', ''), 'sk-ant-oat01-[A-Za-z0-9_\-]{20,}')
        if ($m.Count) { return $m[$m.Count - 1].Value }
    } catch { }
    return $null
}

Clear-Host
Say '=== Set up the SFL NAS Telegram bot ===' 'Cyan'
Say 'This collects four things and saves them in a locked file on the NAS.'
Say 'You copy each one; this window picks it up from the clipboard. Nothing needs typing.'
Say 'You can leave this window open and ask Claude in the chat at any point if you get stuck.'
Say ''

# 1. Claude
Say 'STEP 1 of 3 - Claude sign-in' 'Cyan'
Say '  A browser page will open. Sign in with your Claude account and click "Authorize".'
Say '  Then come back to this window.'
Wait-Enter 'Press Enter to open the sign-in page'
& $claude setup-token
$claudeToken = Find-ClaudeToken
if ($claudeToken) {
    Say "  Found the Claude code automatically (ends in $(Tail $claudeToken))." 'Green'
} else {
    Say '  Above is a long code starting with sk-ant-oat01-.'
    Say '  Highlight all of it with the mouse (click at the start, drag to the end), then press Ctrl+C.'
    $claudeToken = Get-FromClipboard 'Claude code' '^sk-ant-oat01-[A-Za-z0-9_\-]{20,}$'
}
Say ''

# 2. Telegram
Say 'STEP 2 of 3 - Telegram bot code' 'Cyan'
$tgSteps | ForEach-Object { Say $_ }
$tgToken = Get-FromClipboard 'Telegram message' '^\d{6,}:[A-Za-z0-9_\-]{30,}$' $tgFind
Say ''

# 3. Smokeball
Say 'STEP 3 of 3 - Smokeball (three values)' 'Cyan'
Say '  In Chrome, sign in to the Smokeball Developer Console (console.smokeball.com)'
Say '  and open the app that used to be called "SFL Cloud Read-only".'
Say '  Not sure where the values are? Ask Claude in the chat - this window will wait.'
Say '  (a) Copy the Client ID.'
$sbId = Get-FromClipboard 'Smokeball Client ID' '^\S{8,}$'
Say '  (b) Copy the Client Secret.'
$sbSecret = Get-FromClipboard 'Smokeball Client Secret' '^\S{8,}$'
Say '  (c) Go to the API page and copy the AU API Key.'
$sbKey = Get-FromClipboard 'Smokeball AU API Key' '^\S{8,}$'

$lines = @(
    '# SFL NAS Telegram bot secrets. Written by Set-BotSecrets.ps1. Never paste these into a chat.',
    "TELEGRAM_BOT_TOKEN=$tgToken",
    'TELEGRAM_ALLOWED_CHAT_ID=8628004600',
    "CLAUDE_CODE_OAUTH_TOKEN=$claudeToken",
    "SMOKEBALL_CLIENT_ID=$sbId",
    "SMOKEBALL_CLIENT_SECRET=$sbSecret",
    "SMOKEBALL_API_KEY=$sbKey"
)
# LF line endings, no BOM: the NAS reads this file in bash.
[IO.File]::WriteAllText($path, (($lines -join "`n") + "`n"), (New-Object Text.UTF8Encoding $false))
Save-DigestCopy $tgToken
Set-Clipboard -Value ' '

Say ''
Say 'All saved. The clipboard has been cleared.' 'Green'
Say 'Go back to the Claude chat and say "secrets done".' 'Green'
Wait-Enter 'Press Enter to close this window'
