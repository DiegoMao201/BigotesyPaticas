"""Email service — Gmail SMTP."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

log = structlog.get_logger()

SMTP_SERVER   = os.getenv("SMTP_SERVER",   "smtp.gmail.com")
SMTP_PORT     = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER     = os.getenv("SMTP_USER",     "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_NAME     = "Bigotes y Paticas"
STORE_EMAIL   = os.getenv("SMTP_USER", "bigotesypaticasdosquebradas@gmail.com")


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    """Send a single email; returns False instead of raising if credentials are missing."""
    if not SMTP_USER or not SMTP_PASSWORD:
        log.warning("email.skipped", reason="no_credentials", to=to)
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"]      = to
        msg["Subject"] = subject
        if text:
            msg.attach(MIMEText(text, "plain", "utf-8"))
        msg.attach(MIMEText(html, "html", "utf-8"))
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to, msg.as_string())
        log.info("email.sent", to=to, subject=subject)
        return True
    except Exception as exc:
        log.error("email.failed", to=to, subject=subject, error=str(exc))
        return False
