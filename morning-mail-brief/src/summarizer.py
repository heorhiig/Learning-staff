from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime

import requests

from gmail_client import EmailMessage

CATEGORY_ORDER = ("action", "work", "invitations", "today", "updates")

CATEGORY_META = {
    "action": ("🔴", "Action needed"),
    "work": ("💼", "Work"),
    "invitations": ("📨", "Invitations"),
    "today": ("📅", "Today"),
    "updates": ("📬", "Updates"),
}


def _escape(text: str) -> str:
    return html.escape(text or "", quote=False)


def _normalize_subject(subject: str) -> str:
    value = subject.strip()
    while value.lower().startswith("re:"):
        value = value[3:].strip()
    return value.lower()


def _clean_snippet(snippet: str, max_len: int = 120) -> str:
    text = re.sub(r"\s+", " ", snippet or "").strip()
    text = html.unescape(text)
    if len(text) > max_len:
        return text[: max_len - 1] + "…"
    return text


def _sender_label(message: EmailMessage) -> str:
    email = message.sender_email or message.sender
    if "@" in email:
        return email.split("@")[0]
    return email


def _categorize(message: EmailMessage) -> str:
    subject = message.subject.lower()
    sender = (message.sender_email or message.sender).lower()
    combined = f"{subject} {sender}"

    if any(k in subject for k in ("action required", "urgent", "approval", "asap", "deadline")):
        return "action"
    if any(k in combined for k in ("gitlab", "merge request", "jenkins", "ci.int", "github")):
        return "work"
    if any(k in combined for k in ("invitation", "invited", "join team")):
        return "invitations"
    if any(k in combined for k in ("reservation", "check-in", "appspace", "calendar")):
        return "today"
    return "updates"


def _group_messages(messages: list[EmailMessage]) -> list[tuple[EmailMessage, int]]:
    buckets: dict[str, list[EmailMessage]] = defaultdict(list)
    for message in messages:
        buckets[_normalize_subject(message.subject)].append(message)

    grouped: list[tuple[EmailMessage, int]] = []
    for items in buckets.values():
        items.sort(key=lambda m: m.importance_score, reverse=True)
        grouped.append((items[0], len(items)))

    grouped.sort(key=lambda pair: pair[0].importance_score, reverse=True)
    return grouped[:12]


def _format_item(message: EmailMessage, count: int) -> str:
    title = _normalize_subject(message.subject)
    title = title[:1].upper() + title[1:] if title else "(no subject)"
    sender = _sender_label(message)
    snippet = _clean_snippet(message.snippet)

    lines = [
        f"▫️ <b>{_escape(title)}</b>",
        f"   👤 <i>{_escape(sender)}</i>",
    ]
    if count > 1:
        lines.append(f"   🔁 <i>{count} related updates</i>")
    if snippet:
        lines.append(f"   💬 {_escape(snippet)}")
    return "\n".join(lines)


def build_rules_summary(messages: list[EmailMessage]) -> str:
    today = datetime.now().strftime("%A, %d %b %Y")
    if not messages:
        return (
            f"<b>☀️ Morning Brief</b>\n"
            f"<i>{_escape(today)}</i>\n\n"
            f"✅ Your inbox looks quiet — no important mail in the last 24 hours."
        )

    grouped = _group_messages(messages)
    by_category: dict[str, list[tuple[EmailMessage, int]]] = defaultdict(list)
    for item in grouped:
        by_category[_categorize(item[0])].append(item)

    total_threads = len(grouped)
    total_raw = len(messages)

    parts = [
        "<b>☀️ Morning Brief</b>",
        f"<i>{_escape(today)}</i>",
        f"📊 <b>{total_threads}</b> thread{'s' if total_threads != 1 else ''}"
        + (f" · <i>{total_raw} messages scanned</i>" if total_raw != total_threads else ""),
        "",
    ]

    for category in CATEGORY_ORDER:
        items = by_category.get(category)
        if not items:
            continue
        emoji, label = CATEGORY_META[category]
        parts.append(f"<b>{emoji} {label}</b>")
        parts.append("─" * 18)
        for message, count in items:
            parts.append(_format_item(message, count))
            parts.append("")
        parts.append("")

    parts.append("<i>morning-mail-brief · rule-based</i>")
    return "\n".join(parts).strip()


def polish_with_ai(messages: list[EmailMessage], api_key: str, model: str) -> str:
    if not messages:
        return build_rules_summary(messages)

    digest_lines = []
    for message, count in _group_messages(messages):
        digest_lines.append(
            f"- Subject: {message.subject}\n"
            f"  From: {message.sender_email or message.sender}\n"
            f"  Category: {_categorize(message)}\n"
            f"  Count: {count}\n"
            f"  Snippet: {message.snippet[:300]}"
        )
    digest = "\n".join(digest_lines)

    prompt = f"""Write a morning email brief for Telegram using HTML (parse_mode HTML).
Rules:
- Use only these tags: <b>, <i>, <code>
- Escape & < > in content or avoid special chars in subjects
- Max 3200 characters
- Structure:
  <b>☀️ Morning Brief</b>
  <i>date line</i>
  one-line overview with counts
  blank line
  sections with <b>emoji Section name</b> and separator line ──────────
  each item:
    ▫️ <b>subject</b>
       👤 <i>sender</i>
       💬 short snippet
- Max 8 items total, grouped by: Action needed, Work, Invitations, Today, Updates
- End with <i>morning-mail-brief · AI summary</i>
- Be concise, scannable, no walls of text

Emails:
{digest}
"""

    response = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": model,
            "max_tokens": 900,
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    text_blocks = [block["text"] for block in payload.get("content", []) if block.get("type") == "text"]
    if not text_blocks:
        return build_rules_summary(messages)
    return text_blocks[0].strip()


def summarize(messages: list[EmailMessage], anthropic_api_key: str | None, anthropic_model: str) -> str:
    if anthropic_api_key:
        try:
            return polish_with_ai(messages, anthropic_api_key, anthropic_model)
        except Exception:
            return build_rules_summary(messages) + "\n\n<i>AI polish unavailable — rule-based summary shown.</i>"
    return build_rules_summary(messages)
