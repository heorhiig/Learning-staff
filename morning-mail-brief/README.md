# Morning Mail Brief

Daily Gmail → Telegram summary between **8:00 and 10:00 AM** (local time).

- **Rules:** Gmail Important, Starred, Unread, priority senders, calendar/action signals
- **Optional AI:** Set `ANTHROPIC_API_KEY` for a polished brief
- **Scheduler:** macOS `launchd` (Mac must be awake; runs at 8 AM + random delay)

## Quick setup

```bash
cd ~/morning-mail-brief
./scripts/setup.sh
```

### 1. Google Gmail API

1. Open [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → **APIs & Services** → enable **Gmail API**
3. **OAuth consent screen** → External (or Internal if Workspace allows) → add scope `gmail.readonly`
4. **Credentials** → Create **OAuth client ID** → Desktop app
5. Download JSON → save as `credentials/credentials.json`

First run opens a browser to authorize Gmail:

```bash
./scripts/run.sh --now --dry-run
```

Token is saved to `credentials/token.json`.

### 2. Telegram bot

1. Message [@BotFather](https://t.me/BotFather) → `/newbot` → copy token
2. Add to `.env`: `TELEGRAM_BOT_TOKEN=...`
3. Message your bot in Telegram, then:

```bash
./scripts/get-telegram-chat-id.sh
```

4. Add `TELEGRAM_CHAT_ID=...` to `.env`

### 3. Optional: AI summary

```bash
# in .env
ANTHROPIC_API_KEY=sk-ant-...
```

### 4. Optional: priority senders

```bash
PRIORITY_SENDERS=tdarby@redhat.com,calendar-notification@google.com
```

### 5. Test

```bash
./scripts/run.sh --now --force          # send now
./scripts/run.sh --now --dry-run        # print only
```

### 6. Schedule daily

```bash
./scripts/install-launchd.sh
```

Uninstall:

```bash
launchctl bootout gui/$(id -u)/com.hchurhul.morning-mail-brief
rm ~/Library/LaunchAgents/com.hchurhul.morning-mail-brief.plist
```

## How timing works

- `launchd` starts the job at **8:00 AM**
- Script waits a **random 0–120 minutes** (`WINDOW_MINUTES`) → delivery between 8–10 AM
- `state/last_sent.json` prevents duplicate sends the same day

## Commands

| Command | Purpose |
|---------|---------|
| `./scripts/run.sh` | Normal scheduled run (wait + send) |
| `./scripts/run.sh --now` | Skip wait window |
| `./scripts/run.sh --dry-run` | Preview without Telegram |
| `./scripts/run.sh --force` | Send even if already sent today |
