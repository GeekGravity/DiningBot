"""Email helpers for sending menu summaries."""

from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterable, List, Optional


@dataclass
class EmailSettings:
    host: str
    port: int = 587
    sender: str = ""
    recipients: List[str] = field(default_factory=list)
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: bool = True


def _split_list(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_email_settings() -> EmailSettings:
    """Load SMTP settings from environment variables."""
    settings = EmailSettings(
        host=os.environ.get("DININGBOT_SMTP_HOST", ""),
        port=int(os.environ.get("DININGBOT_SMTP_PORT", "587")),
        sender=os.environ.get("DININGBOT_EMAIL_SENDER", ""),
        recipients=_split_list(os.environ.get("DININGBOT_EMAIL_RECIPIENTS")),
        username=os.environ.get("DININGBOT_SMTP_USER"),
        password=os.environ.get("DININGBOT_SMTP_PASSWORD"),
        use_tls=os.environ.get("DININGBOT_SMTP_USE_TLS", "true").lower() != "false",
    )

    if not settings.host:
        raise ValueError("DININGBOT_SMTP_HOST must be set.")
    if not settings.sender:
        raise ValueError("DININGBOT_EMAIL_SENDER must be set.")
    if not settings.recipients:
        raise ValueError("DININGBOT_EMAIL_RECIPIENTS must list at least one address.")
    return settings


def send_email(settings: EmailSettings, subject: str, html_body: str, text_body: str) -> None:
    """Send an email with HTML + plain-text parts."""
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.sender
    message["To"] = ", ".join(settings.recipients)

    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.host, settings.port, timeout=20) as client:
        if settings.use_tls:
            client.starttls()
        if settings.username and settings.password:
            client.login(settings.username, settings.password)
        client.sendmail(settings.sender, settings.recipients, message.as_string())
