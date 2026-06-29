"""Email service — Resend API (HTTPS) con fallback SMTP."""
from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import structlog

log = structlog.get_logger()

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
SMTP_SERVER    = os.getenv("SMTP_SERVER",   "smtp.gmail.com")
SMTP_PORT      = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER      = os.getenv("SMTP_USER",     "")
SMTP_PASSWORD  = os.getenv("SMTP_PASSWORD", "")
FROM_NAME      = "Bigotes y Paticas"
FROM_EMAIL     = os.getenv("RESEND_FROM", "hola@bigotesypaticas.com")
STORE_EMAIL    = os.getenv("SMTP_USER", "bigotesypaticasdosquebradas@gmail.com")


def _send_resend(to: str, subject: str, html: str) -> bool:
    """Envía via Resend API (HTTPS — funciona aunque SMTP esté bloqueado)."""
    import urllib.request, urllib.error, json
    payload = json.dumps({
        "from": f"{FROM_NAME} <{FROM_EMAIL}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }).encode()
    req = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("email.sent_resend", to=to, subject=subject, status=resp.status)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log.error("email.resend_failed", to=to, subject=subject, status=e.code, body=body)
        return False
    except Exception as exc:
        log.error("email.resend_error", to=to, subject=subject, error=str(exc))
        return False


def _send_smtp(to: str, subject: str, html: str, text: str = "") -> bool:
    """Fallback SMTP (solo funciona si el puerto 587 está abierto)."""
    if not SMTP_USER or not SMTP_PASSWORD:
        log.warning("email.skipped", reason="no_smtp_credentials", to=to)
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
        log.info("email.sent_smtp", to=to, subject=subject)
        return True
    except Exception as exc:
        log.error("email.smtp_failed", to=to, subject=subject, error=str(exc))
        return False


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    """Envía email: Resend si hay API key, SMTP como fallback."""
    if RESEND_API_KEY:
        return _send_resend(to, subject, html)
    return _send_smtp(to, subject, html, text)
