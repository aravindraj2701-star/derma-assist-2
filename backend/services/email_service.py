"""
Transactional Email Service for DermaAssist.
Supports SMTP integration (SendGrid, Mailgun, Amazon SES, Resend, Brevo)
with background task execution and local development fallback.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from pathlib import Path
from typing import Optional, Any
from fastapi import BackgroundTasks

from backend.config import settings

logger = logging.getLogger("derma_assist.email")
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates" / "email"


def _render_template(template_name: str, context: dict) -> str:
    """Reads HTML email template and replaces {{ key }} placeholder variables."""
    filepath = TEMPLATE_DIR / template_name
    if not filepath.exists():
        logger.warning(f"[EMAIL] Template file {filepath} not found. Using fallback text.")
        return f"<html><body><p>{context}</p></body></html>"

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    for key, val in context.items():
        placeholder = "{{" + f" {key} " + "}}"
        placeholder_tight = "{{" + f"{key}" + "}}"
        content = content.replace(placeholder, str(val))
        content = content.replace(placeholder_tight, str(val))

    return content


def send_email(to_email: str, subject: str, html_body: str) -> bool:
    """
    Sends a transactional HTML email via configured SMTP service.
    If SMTP credentials are not configured, logs the email details to console.
    Never throws unhandled exceptions to avoid breaking user flows.
    """
    try:
        # Check if SMTP credentials are provided
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.info("=" * 70)
            logger.info("  [TRANSACTIONAL EMAIL DISPATCH — LOCAL DEV MODE]")
            logger.info(f"  To:       {to_email}")
            logger.info(f"  From:     {settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>")
            logger.info(f"  Subject:  {subject}")
            logger.info("  Notice:   SMTP credentials not set in .env. Email body logged below.")
            logger.info("=" * 70)
            return True

        # Build MIME Message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email

        # Attach HTML part
        part = MIMEText(html_body, "html", "utf-8")
        msg.attach(part)

        # Connect to SMTP Host
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"[EMAIL] Successfully sent '{subject}' to {to_email}")
        return True

    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email to {to_email}: {str(e)}", exc_info=True)
        return False


def send_account_created_email(user: Any, background_tasks: Optional[BackgroundTasks] = None):
    """Dispatches the welcome/account confirmation email."""
    context = {
        "name": getattr(user, "name", "Doctor / Clinician"),
        "email": getattr(user, "email", ""),
        "dashboard_url": f"{settings.FRONTEND_URL}/dashboard",
        "year": datetime.utcnow().year,
    }
    subject = "Welcome to DermaAssist — Account Created"
    html_body = _render_template("welcome.html", context)

    if background_tasks:
        background_tasks.add_task(send_email, user.email, subject, html_body)
    else:
        send_email(user.email, subject, html_body)


def send_password_reset_email(user: Any, reset_link: str, background_tasks: Optional[BackgroundTasks] = None):
    """Dispatches the password reset link email."""
    context = {
        "name": getattr(user, "name", "Doctor / Clinician"),
        "email": getattr(user, "email", ""),
        "reset_link": reset_link,
        "expiry_minutes": settings.RESET_TOKEN_EXPIRY_MINUTES,
        "year": datetime.utcnow().year,
    }
    subject = "Reset your DermaAssist password"
    html_body = _render_template("password_reset.html", context)

    if background_tasks:
        background_tasks.add_task(send_email, user.email, subject, html_body)
    else:
        send_email(user.email, subject, html_body)


def send_password_changed_email(user: Any, background_tasks: Optional[BackgroundTasks] = None):
    """Dispatches security confirmation email following a password reset/change."""
    context = {
        "name": getattr(user, "name", "Doctor / Clinician"),
        "email": getattr(user, "email", ""),
        "timestamp": datetime.utcnow().strftime("%B %d, %Y at %H:%M"),
        "login_url": f"{settings.FRONTEND_URL}/login",
        "support_url": f"mailto:{settings.SMTP_FROM_EMAIL}",
        "year": datetime.utcnow().year,
    }
    subject = "Your DermaAssist password was changed"
    html_body = _render_template("password_changed.html", context)

    if background_tasks:
        background_tasks.add_task(send_email, user.email, subject, html_body)
    else:
        send_email(user.email, subject, html_body)


def send_follow_up_reminder_email(
    user_email: str,
    user_name: str,
    case_id: int,
    predicted_disease: str,
    reminder_notes: str,
    background_tasks: Optional[BackgroundTasks] = None,
):
    """Dispatches clinical interval re-check reminder email."""
    context = {
        "user_name": user_name or "Patient / Clinician",
        "case_id": case_id,
        "predicted_disease": predicted_disease,
        "reminder_notes": reminder_notes,
        "action_url": f"{settings.FRONTEND_URL}/analyze",
        "year": datetime.utcnow().year,
    }
    subject = f"Clinical Reminder: Follow-up re-check for Case #{case_id} ({predicted_disease})"
    html_body = _render_template("follow_up_reminder.html", context)

    if background_tasks:
        background_tasks.add_task(send_email, user_email, subject, html_body)
    else:
        send_email(user_email, subject, html_body)

