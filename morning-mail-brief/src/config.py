from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Config:
    gmail_credentials_path: Path
    gmail_token_path: Path
    telegram_bot_token: str
    telegram_chat_id: str
    anthropic_api_key: str | None
    anthropic_model: str
    run_hour: int
    window_minutes: int
    priority_senders: list[str]
    state_dir: Path

    @classmethod
    def load(cls) -> Config:
        priority = os.getenv("PRIORITY_SENDERS", "").strip()
        return cls(
            gmail_credentials_path=Path(
                os.getenv("GMAIL_CREDENTIALS_PATH", "credentials/credentials.json")
            ),
            gmail_token_path=Path(os.getenv("GMAIL_TOKEN_PATH", "credentials/token.json")),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", "").strip(),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip() or None,
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            run_hour=int(os.getenv("RUN_HOUR", "8")),
            window_minutes=int(os.getenv("WINDOW_MINUTES", "120")),
            priority_senders=[s.strip() for s in priority.split(",") if s.strip()],
            state_dir=PROJECT_ROOT / "state",
        )

    def resolve_paths(self) -> Config:
        creds = self.gmail_credentials_path
        token = self.gmail_token_path
        if not creds.is_absolute():
            creds = PROJECT_ROOT / creds
        if not token.is_absolute():
            token = PROJECT_ROOT / token
        return Config(
            gmail_credentials_path=creds,
            gmail_token_path=token,
            telegram_bot_token=self.telegram_bot_token,
            telegram_chat_id=self.telegram_chat_id,
            anthropic_api_key=self.anthropic_api_key,
            anthropic_model=self.anthropic_model,
            run_hour=self.run_hour,
            window_minutes=self.window_minutes,
            priority_senders=self.priority_senders,
            state_dir=self.state_dir,
        )

    def validate(self) -> None:
        missing: list[str] = []
        if not self.telegram_bot_token:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.telegram_chat_id:
            missing.append("TELEGRAM_CHAT_ID")
        if not self.gmail_credentials_path.exists():
            missing.append(f"Gmail credentials file at {self.gmail_credentials_path}")
        if missing:
            raise ValueError("Missing configuration: " + ", ".join(missing))
