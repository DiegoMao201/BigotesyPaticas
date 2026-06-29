"""Meta Conversion API — server-side event tracking."""
from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime

import requests

log = logging.getLogger(__name__)

_PIXEL_ID     = os.environ.get("META_PIXEL_ID", "")
_ACCESS_TOKEN = os.environ.get("META_ACCESS_TOKEN", "")
_TEST_CODE    = os.environ.get("META_TEST_EVENT_CODE", "")
_BASE         = "https://graph.facebook.com/v18.0"


def _hash(value: str | None) -> str | None:
    if not value:
        return None
    return hashlib.sha256(value.lower().strip().encode()).hexdigest()


def _is_active() -> bool:
    return bool(_PIXEL_ID and _PIXEL_ID != "PENDIENTE_DIEGO_CREA_BM" and _ACCESS_TOKEN)


def send_event(
    event_name: str,
    *,
    user_data: dict | None = None,
    custom_data: dict | None = None,
    event_id: str | None = None,
    event_source_url: str | None = None,
) -> dict | None:
    """Envía un evento al Meta Conversion API.

    user_data keys aceptados: email, phone, external_id, first_name, city
    custom_data: value, currency, content_ids, content_type, num_items, etc.
    """
    if not _is_active():
        log.debug("CAPI inactivo — Pixel ID no configurado")
        return None

    hashed: dict = {}
    if user_data:
        if user_data.get("email"):
            hashed["em"] = _hash(user_data["email"])
        if user_data.get("phone"):
            phone = user_data["phone"].replace("+", "").replace(" ", "")
            hashed["ph"] = _hash(phone)
        if user_data.get("external_id"):
            hashed["external_id"] = _hash(str(user_data["external_id"]))
        if user_data.get("first_name"):
            hashed["fn"] = _hash(user_data["first_name"])
        if user_data.get("city"):
            hashed["ct"] = _hash(user_data["city"])

    payload_event: dict = {
        "event_name": event_name,
        "event_time": int(datetime.utcnow().timestamp()),
        "action_source": "website",
        "user_data": hashed,
        "custom_data": custom_data or {},
    }
    if event_id:
        payload_event["event_id"] = event_id
    if event_source_url:
        payload_event["event_source_url"] = event_source_url

    payload: dict = {
        "data": [payload_event],
        "access_token": _ACCESS_TOKEN,
    }
    if _TEST_CODE:
        payload["test_event_code"] = _TEST_CODE

    try:
        r = requests.post(
            f"{_BASE}/{_PIXEL_ID}/events",
            json=payload,
            timeout=8,
        )
        if r.status_code == 200:
            log.info("CAPI ✓ %s event_id=%s", event_name, event_id)
            return r.json()
        log.warning("CAPI ✗ %s: %s", event_name, r.text[:200])
        return None
    except Exception as exc:
        log.warning("CAPI exception %s: %s", event_name, exc)
        return None
