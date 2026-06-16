#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import date, datetime
from pathlib import Path

from config import Config
from gmail_client import fetch_important_messages, get_gmail_service
from summarizer import summarize
from telegram_client import send_telegram_message


def _already_sent_today(state_file: Path) -> bool:
    if not state_file.exists():
        return False
    try:
        data = json.loads(state_file.read_text())
        return data.get("date") == date.today().isoformat()
    except json.JSONDecodeError:
        return False


def _mark_sent(state_file: Path) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    state_file.write_text(
        json.dumps({"date": date.today().isoformat(), "sent_at": datetime.now().isoformat()}, indent=2)
    )


def wait_for_delivery_window(run_hour: int, window_minutes: int) -> None:
    now = datetime.now()
    if now.hour < run_hour:
        target = now.replace(hour=run_hour, minute=0, second=0, microsecond=0)
        sleep_seconds = (target - now).total_seconds()
        if sleep_seconds > 0:
            time.sleep(sleep_seconds)

    delay = random.randint(0, max(window_minutes, 1) * 60)
    time.sleep(delay)


def run(*, skip_wait: bool = False, dry_run: bool = False, force: bool = False) -> int:
    config = Config.load().resolve_paths()
    config.validate()

    state_file = config.state_dir / "last_sent.json"
    if not force and _already_sent_today(state_file):
        print("Brief already sent today. Use --force to send again.")
        return 0

    if not skip_wait:
        wait_for_delivery_window(config.run_hour, config.window_minutes)

    service = get_gmail_service(config.gmail_credentials_path, config.gmail_token_path)
    messages = fetch_important_messages(service, priority_senders=config.priority_senders)
    brief = summarize(messages, config.anthropic_api_key, config.anthropic_model)

    if dry_run:
        print(brief)
        return 0

    send_telegram_message(config.telegram_bot_token, config.telegram_chat_id, brief)
    _mark_sent(state_file)
    print(f"Sent morning brief with {len(messages)} item(s) to Telegram.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Send a morning Gmail brief to Telegram.")
    parser.add_argument("--now", action="store_true", help="Skip 8–10 AM wait window")
    parser.add_argument("--dry-run", action="store_true", help="Print summary without sending")
    parser.add_argument("--force", action="store_true", help="Send even if already sent today")
    args = parser.parse_args()
    try:
        return run(skip_wait=args.now, dry_run=args.dry_run, force=args.force)
    except Exception as exc:  # noqa: BLE001 - top-level CLI guard
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
