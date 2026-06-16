#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing .env — run ./scripts/setup.sh first"
  exit 1
fi

# shellcheck disable=SC1091
source .env

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  echo "Set TELEGRAM_BOT_TOKEN in .env first"
  exit 1
fi

echo "1) Open Telegram and send any message to your bot"
echo "2) Press Enter here after sending"
read -r _

curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates" | python3 -c '
import json, sys
data = json.load(sys.stdin)
results = data.get("result", [])
if not results:
    print("No messages found. Send a message to your bot and try again.")
    sys.exit(1)
chat = results[-1]["message"]["chat"]
chat_id = chat["id"]
title = chat.get("username") or chat.get("first_name") or "chat"
print(f"\nYour chat id: {chat_id} ({title})")
print(f"Add to .env: TELEGRAM_CHAT_ID={chat_id}")
'
