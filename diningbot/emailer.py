"""Email helpers for sending menu summaries."""
from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional
import time
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

PERIOD_KEYS = ("breakfast", "lunch", "dinner")

SUPABASE_URL = os.environ["SUPABASE_URL"]
BASE_URL = os.environ["BASE_URL"]
SUPABASE_SERVICE_ROLE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

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

def store_daily_html(date: str, html: str) -> None:
    supabase.table("email_format").upsert({"date": date, "html": html}).execute()

def load_cached_email_html(date: str) -> Optional[str]:
    """Return cached HTML content for a given date."""
    res = (
        supabase.table("email_format")
        .select("html")
        .eq("date", date)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return None
    html_value = rows[0].get("html")
    if not html_value:
        return None
    return html_value

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
    return settings


def build_plain_text(subject: str, periods: dict[str, dine_api.Period]) -> str:  # type: ignore[attr-defined]
    """Generate a plaintext companion for the email."""

    lines = [subject, ""]
    for key in PERIOD_KEYS:
        period = periods.get(key)
        if not period:
            continue
        lines.append(period.name or key.title())
        for category in period.categories:
            if not category.items:
                continue
            item_names = ", ".join(item.name for item in category.items if item.name)
            if item_names:
                label = category.name or "Misc"
                lines.append(f"  {label}: {item_names}")
        lines.append("")
    return "\n".join(lines).strip()

def send_email_helper(settings: EmailSettings, subject: str, html_body: str, text_body: str) -> None:
    """Send an email with HTML + plain-text parts."""

    # fetch active subscribers
    res = supabase.table("subscribers").select("email, token").eq("active", True).execute()
    rows = res.data or []

    with smtplib.SMTP(settings.host, settings.port, timeout=20) as client:
        if settings.use_tls:
            client.starttls()
        if settings.username and settings.password:
            client.login(settings.username, settings.password)

        for row in rows:
            rcpt = row["email"]
            token = row["token"]

            unsubscribe_url = f"{BASE_URL}/unsubscribe?token={token}"

            footer_html = f"""
            <tr>
            <td style="padding:10px;background:#1B1A19;border-top:1px solid #6B5E4B;text-align:center;">
            <p style="margin:0;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:18px;color:#D9D4C7;">
                You're receiving this because you subscribed to the SFU Dining menu newsletter.
            </p>
            <p style="margin:0;margin-top:6px;font-family:Helvetica,Arial,sans-serif;font-size:12px;line-height:18px;">
                <a href="{unsubscribe_url}" style="color:#D7B47E;text-decoration:underline;">
                Unsubscribe
                </a>
            </p>
            </td>
            </tr>
            """

            html_final = html_body.replace("</table>", footer_html + "</table>", 1)

            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"SFU Dining Menu <{settings.sender}>"
            message["To"] = rcpt

            message.attach(MIMEText(text_body, "plain", "utf-8"))
            message.attach(MIMEText(html_final, "html", "utf-8"))

            client.sendmail(settings.sender, [rcpt], message.as_string())
            time.sleep(1)

def send_email_to_one(recipient: str, html_body: str, date: str) -> None:
    """Send cached HTML content to a single recipient."""
    try:
        settings = load_email_settings()
    except ValueError as exc:
        raise RuntimeError(f"Invalid email settings: {exc}") from exc

    subject = f"Dining Menu - {date}"
    text_body = f"Dining menu for {date}. Please view the HTML version for full details."

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"SFU Dining Menu <{settings.sender}>"
    message["To"] = recipient

    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(settings.host, settings.port, timeout=20) as client:
        if settings.use_tls:
            client.starttls()
        if settings.username and settings.password:
            client.login(settings.username, settings.password)
        client.sendmail(settings.sender, [recipient], message.as_string())

def send_email(date: str, html_output: str, periods: dict[str, dine_api.Period]) -> None:  # type: ignore[attr-defined]
    """Load email settings and dispatch the menu email."""
    store_daily_html(date, html_output)
    try:
        settings = load_email_settings()
    except ValueError as exc:
        raise RuntimeError(f"Invalid email settings: {exc}") from exc

    subject = f"Dining Menu - {date}"
    plain_text = build_plain_text(subject, periods)
    send_email_helper(settings, subject, html_output, plain_text)