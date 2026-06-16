from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from email.utils import parseaddr
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

NEWSLETTER_HINTS = re.compile(
    r"(unsubscribe|newsletter|no-?reply|marketing|promo|digest|mailing list)",
    re.IGNORECASE,
)


@dataclass
class EmailMessage:
    message_id: str
    subject: str
    sender: str
    sender_email: str
    snippet: str
    date: str
    labels: list[str]
    importance_score: int
    reasons: list[str]


def get_gmail_service(credentials_path: Path, token_path: Path):
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _header(headers: list[dict], name: str) -> str:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def _score_message(
    labels: list[str],
    subject: str,
    sender_email: str,
    priority_senders: list[str],
) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    label_set = set(labels)

    if "IMPORTANT" in label_set:
        score += 4
        reasons.append("Gmail Important")
    if "STARRED" in label_set:
        score += 4
        reasons.append("Starred")
    if "CATEGORY_PERSONAL" in label_set:
        score += 2
        reasons.append("Personal")
    if "CATEGORY_UPDATES" in label_set:
        score += 1
        reasons.append("Updates")

    sender_lower = sender_email.lower()
    for priority in priority_senders:
        if priority.lower() in sender_lower:
            score += 5
            reasons.append(f"Priority sender ({priority})")
            break

    combined = f"{subject} {sender_email}"
    if NEWSLETTER_HINTS.search(combined):
        score -= 3
        reasons.append("Likely newsletter/noise")

    calendar_keywords = ("invitation", "accepted:", "declined:", "updated invitation", "calendar")
    if any(k in subject.lower() for k in calendar_keywords):
        score += 3
        reasons.append("Calendar-related")

    action_keywords = ("action required", "urgent", "deadline", "approval", "review", "asap")
    if any(k in subject.lower() for k in action_keywords):
        score += 2
        reasons.append("Action keyword in subject")

    return score, reasons


def fetch_important_messages(
    service,
    *,
    priority_senders: list[str],
    max_results: int = 40,
    min_score: int = 2,
) -> list[EmailMessage]:
    query_parts = [
        "newer_than:1d",
        "in:inbox",
        "(",
        "is:important OR is:starred OR is:unread",
    ]
    for sender in priority_senders:
        query_parts.append(f"OR from:{sender}")
    query_parts.append(")")
    query = " ".join(query_parts)

    response = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    message_refs = response.get("messages", [])
    results: list[EmailMessage] = []

    for ref in message_refs:
        msg = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="metadata", metadataHeaders=["From", "Subject", "Date"])
            .execute()
        )
        headers = msg.get("payload", {}).get("headers", [])
        subject = _header(headers, "Subject") or "(no subject)"
        sender = _header(headers, "From")
        _, sender_email = parseaddr(sender)
        labels = msg.get("labelIds", [])
        score, reasons = _score_message(labels, subject, sender_email, priority_senders)

        if score < min_score:
            continue

        results.append(
            EmailMessage(
                message_id=msg["id"],
                subject=subject,
                sender=sender,
                sender_email=sender_email,
                snippet=msg.get("snippet", ""),
                date=_header(headers, "Date"),
                labels=labels,
                importance_score=score,
                reasons=reasons,
            )
        )

    results.sort(key=lambda item: item.importance_score, reverse=True)
    return results[:15]


def decode_body_part(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")
