from __future__ import annotations

import re

import requests


def _split_message(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    sections = re.split(r"\n(?=<b>[🔴💼📨📅📬☀️])", text)
    current = ""
    for section in sections:
        candidate = f"{current}\n{section}".strip() if current else section
        if len(candidate) <= limit:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(section) <= limit:
                current = section
            else:
                for i in range(0, len(section), limit):
                    chunks.append(section[i : i + limit])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def send_telegram_message(bot_token: str, chat_id: str, text: str) -> None:
    chunks = _split_message(text)

    for index, chunk in enumerate(chunks):
        if index > 0 and not chunk.startswith("<b>"):
            chunk = f"<b>☀️ Morning Brief</b> <i>(continued)</i>\n\n{chunk}"

        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=30,
        )
        if not response.ok:
            # Fallback if HTML parsing fails
            response = requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": chunk.replace("<b>", "").replace("</b>", "").replace("<i>", "").replace("</i>", ""),
                    "disable_web_page_preview": True,
                },
                timeout=30,
            )
        response.raise_for_status()
        payload = response.json()
        if not payload.get("ok"):
            raise RuntimeError(f"Telegram API error: {payload}")
