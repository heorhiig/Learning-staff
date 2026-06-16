#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

export PYTHONPATH="$ROOT/src"
python3 - <<'PY'
from config import Config
from gmail_client import get_gmail_service

config = Config.load().resolve_paths()
if not config.gmail_credentials_path.exists():
    raise SystemExit(f"Missing {config.gmail_credentials_path}")

print("Opening browser for Gmail authorization...")
service = get_gmail_service(config.gmail_credentials_path, config.gmail_token_path)
profile = service.users().getProfile(userId="me").execute()
print(f"Authorized as: {profile.get('emailAddress')}")
print(f"Token saved to: {config.gmail_token_path}")
PY
