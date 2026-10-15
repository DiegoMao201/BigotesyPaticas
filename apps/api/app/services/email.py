"""Email service — SendGrid API (HTTPS) con fallback SMTP."""

from __future__ import annotations

import base64
import json
import os
import smtplib
import urllib.error
import urllib.request
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

#: Un adjunto: (nombre de archivo, bytes, tipo MIME).
Attachment = tuple[str, bytes, str]

import structlog

log = structlog.get_logger()

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY", "")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
FROM_NAME = "Bigotes y Paticas"
FROM_EMAIL = os.getenv("FROM_EMAIL", "hola@bigotesypaticas.com")
STORE_EMAIL = os.getenv(
    "STORE_EMAIL", os.getenv("SMTP_USER", "bigotesypaticasdosquebradas@gmail.com")
)


def _send_sendgrid(
    to: str,
    subject: str,
    html: str,
    attachments: list[Attachment] | None = None,
    cc: list[str] | None = None,
) -> bool:
    """Envía via SendGrid Web API v3 (HTTPS — no requiere puerto SMTP abierto)."""
    # Reply-To al Gmail real para que las respuestas lleguen a la bandeja
    reply_to = STORE_EMAIL if STORE_EMAIL != FROM_EMAIL else None
    personalization: dict = {"to": [{"email": to}]}
    # SendGrid rechaza un cc igual al destinatario; se filtra.
    cc_clean = [c for c in (cc or []) if c and c.lower() != to.lower()]
    if cc_clean:
        personalization["cc"] = [{"email": c} for c in cc_clean]
    payload_dict: dict = {
        "personalizations": [personalization],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "subject": subject,
        "content": [{"type": "text/html", "value": html}],
    }
    if reply_to:
        payload_dict["reply_to"] = {"email": reply_to, "name": FROM_NAME}
    if attachments:
        payload_dict["attachments"] = [
            {
                "content": base64.b64encode(data).decode(),
                "filename": name,
                "type": mime,
                "disposition": "attachment",
            }
            for name, data, mime in attachments
        ]
    payload = json.dumps(payload_dict).encode()
    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=payload,
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            log.info("email.sent_sendgrid", to=to, subject=subject, status=resp.status)
            return True
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        log.error("email.sendgrid_failed", to=to, subject=subject, status=e.code, body=body)
        return False
    except Exception as exc:
        log.error("email.sendgrid_error", to=to, subject=subject, error=str(exc))
        return False


def _send_smtp(
    to: str,
    subject: str,
    html: str,
    text: str = "",
    attachments: list[Attachment] | None = None,
    cc: list[str] | None = None,
) -> bool:
    """Fallback SMTP."""
    if not SMTP_USER or not SMTP_PASSWORD:
        log.warning("email.skipped", reason="no_credentials", to=to)
        return False
    try:
        body = MIMEMultipart("alternative")
        if text:
            body.attach(MIMEText(text, "plain", "utf-8"))
        body.attach(MIMEText(html, "html", "utf-8"))
        if attachments:
            msg = MIMEMultipart("mixed")
            msg.attach(body)
            for name, data, mime in attachments:
                maintype, _, subtype = mime.partition("/")
                part = MIMEApplication(data, _subtype=subtype or "octet-stream")
                part.add_header("Content-Disposition", "attachment", filename=name)
                msg.attach(part)
        else:
            msg = body
        cc_clean = [c for c in (cc or []) if c and c.lower() != to.lower()]
        msg["From"] = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"] = to
        if cc_clean:
            msg["Cc"] = ", ".join(cc_clean)
        msg["Subject"] = subject
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to, *cc_clean], msg.as_string())
        log.info("email.sent_smtp", to=to, subject=subject)
        return True
    except Exception as exc:
        log.error("email.smtp_failed", to=to, subject=subject, error=str(exc))
        return False


def send_email(
    to: str,
    subject: str,
    html: str,
    text: str = "",
    attachments: list[Attachment] | None = None,
    cc: list[str] | None = None,
) -> bool:
    """Envía email: SendGrid si hay API key, SMTP como fallback.

    `attachments` son tuplas (nombre, bytes, mime); `cc` manda copia (p. ej. al
    correo de la tienda para dejar constancia de un desprendible o un contrato).
    """
    if SENDGRID_API_KEY:
        return _send_sendgrid(to, subject, html, attachments, cc)
    return _send_smtp(to, subject, html, text, attachments, cc)
