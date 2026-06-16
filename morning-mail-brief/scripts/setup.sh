#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — fill in Telegram and optional API keys."
fi

mkdir -p credentials state
chmod +x scripts/run.sh scripts/install-launchd.sh scripts/get-telegram-chat-id.sh

echo ""
echo "Next steps:"
echo "  1. Put Google OAuth credentials.json in credentials/"
echo "  2. Edit .env with TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID"
echo "  3. Authorize Gmail: ./scripts/run.sh --now --dry-run"
echo "  4. Test send: ./scripts/run.sh --now --force"
echo "  5. Schedule daily: ./scripts/install-launchd.sh"
