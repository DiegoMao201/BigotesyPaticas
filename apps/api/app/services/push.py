"""Notificaciones push al celular (8-nov-2026), también con la app cerrada.

Hasta hoy el portal solo avisaba con la app ABIERTA (SSE + campana): si el cliente no
estaba mirando, el "tu pedido está listo" o la mascota perdida a 2 km no le llegaba.
Ahora cada `notify_customer` también sale como push del sistema (Web Push con VAPID):
en la app de Android (TWA, notificaciones delegadas a Chrome) y en el navegador.

  · Las suscripciones viven en `customers.extra["push"]` (máx. 5 celulares). Sin tablas.
  · Respeta las preferencias del perfil: SOS, citas y promociones se pueden apagar; los
    avisos de pedidos siempre salen (son del servicio que el cliente pidió).
  · Una suscripción que el navegador da por muerta (404/410) se borra sola.
  · Nunca rompe la operación que la originó: todo error queda en el log.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import uuid

log = logging.getLogger("push")

VAPID_PUBLIC = os.getenv("VAPID_PUBLIC_KEY", "")
VAPID_PRIVATE = os.getenv("VAPID_PRIVATE_KEY", "")
VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:bigotesypaticasdosquebradas@gmail.com")

# tipo de notificación → preferencia del perfil que la puede apagar
_PREF = {
    "sos_nearby": "sos", "sos_sighting": "sos", "sos_found": "sos",
    "appointment": "appointments", "appt_confirmed": "appointments", "appt_rescheduled": "appointments",
    "appt_cancelled": "appointments", "health_reminder": "appointments",
    "promo": "promos", "promos": "promos",
}


def activo() -> bool:
    return bool(VAPID_PUBLIC and VAPID_PRIVATE)


def url_para(tipo: str, data: dict | None) -> str:
    """A dónde lleva tocar la notificación (la campana y el push usan la misma regla)."""
    d = data or {}
    if d.get("url"):
        return str(d["url"])
    if d.get("order_id"):
        return f"/orders/{d['order_id']}"
    if d.get("sos_event_id"):
        return f"/sos/{d['sos_event_id']}"
    if d.get("appointment_id") or tipo.startswith("appt") or tipo == "appointment":
        return "/appointments"
    if tipo == "health_reminder":
        return "/pets"
    return "/dashboard"


def _enviar_uno(sub: dict, cuerpo: str) -> int | None:
    """Devuelve el código HTTP si el navegador rechazó la suscripción, None si salió."""
    from pywebpush import WebPushException, webpush

    try:
        webpush(subscription_info=sub, data=cuerpo, vapid_private_key=VAPID_PRIVATE,
                vapid_claims={"sub": VAPID_SUBJECT}, ttl=86400, timeout=10)
        return None
    except WebPushException as e:
        return e.response.status_code if e.response is not None else 0
    except Exception as e:  # noqa: BLE001
        log.warning("push: error enviando: %s", e)
        return 0


async def enviar(customer_id: uuid.UUID | str, tipo: str, title: str, body: str, data: dict | None = None) -> int:
    """Manda el push a todos los celulares del cliente. Devuelve cuántos salieron."""
    if not activo():
        return 0
    from sqlalchemy import select

    from app.db import AsyncSessionLocal
    from app.models.crm import Customer

    try:
        async with AsyncSessionLocal() as db:
            c = (await db.execute(select(Customer).where(Customer.id == uuid.UUID(str(customer_id))))).scalar_one_or_none()
            if not c:
                return 0
            pref = _PREF.get(tipo)
            if pref and (c.notification_prefs or {}).get(pref) is False:
                return 0
            subs = list((c.extra or {}).get("push", []))
            if not subs:
                return 0
            cuerpo = json.dumps({"title": title, "body": body, "url": url_para(tipo, data), "tag": tipo})
            codigos = await asyncio.gather(*[asyncio.to_thread(_enviar_uno, s["sub"], cuerpo) for s in subs])
            muertos = {s["sub"]["endpoint"] for s, cod in zip(subs, codigos, strict=True) if cod in (404, 410)}
            if muertos:
                extra = copy.deepcopy(c.extra or {})
                extra["push"] = [s for s in extra.get("push", []) if s["sub"]["endpoint"] not in muertos]
                c.extra = extra
                await db.commit()
            enviados = sum(1 for cod in codigos if cod is None)
            log.info("push cliente=%s tipo=%s enviados=%s de %s", customer_id, tipo, enviados, len(subs))
            return enviados
    except Exception as e:  # noqa: BLE001
        log.warning("push: falló para %s: %s", customer_id, e)
        return 0


_tareas: set = set()


def enviar_en_fondo(customer_id, tipo: str, title: str, body: str, data: dict | None = None) -> None:
    """Desde código que no debe esperar (crear la notificación no se demora por el push)."""
    if not activo():
        return
    try:
        t = asyncio.get_running_loop().create_task(enviar(customer_id, tipo, title, body, data))
        _tareas.add(t)
        t.add_done_callback(_tareas.discard)
    except RuntimeError:
        pass
