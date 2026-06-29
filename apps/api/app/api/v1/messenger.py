"""Messenger webhook — auto-respuestas con detección de intent."""
from __future__ import annotations

import logging
import os

import requests
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1/webhooks/messenger", tags=["messenger"])

_TOKEN        = lambda: os.environ.get("META_MESSENGER_TOKEN") or os.environ.get("META_ACCESS_TOKEN", "")
_VERIFY_TOKEN = os.environ.get("MESSENGER_WEBHOOK_VERIFY_TOKEN", "bigotesypaticas_verify")
_META_BASE    = "https://graph.facebook.com/v18.0"

_INTENTS: list[tuple[list[str], str]] = [
    (
        ["precio", "cuánto", "cuanto", "cuesta", "vale", "valor", "costo"],
        "💰 Para precios específicos visita bigotesypaticas.com o dime qué producto buscas y te cuento el precio al instante.",
    ),
    (
        ["domicilio", "envio", "envío", "delivery", "mandarlo", "despacho"],
        "🛵 ¡Domicilio GRATIS en Pereira y Dosquebradas para pedidos desde $30.000! Pedidos menores: $5.000 de envío. ¿Quieres pedir algo?",
    ),
    (
        ["horario", "abren", "cierran", "atienden", "abierto", "abiert"],
        "🕐 Atendemos Lunes a Sábado de 10:00 AM a 7:00 PM. Domicilios en el mismo horario. ¿En qué te ayudo?",
    ),
    (
        ["donde", "dónde", "ubicacion", "ubicación", "direccion", "dirección", "local", "tienda"],
        "📍 Estamos en Mall Zamara Plaza, Cl. 15 #3A-07 Local 2, Dosquebradas. También hacemos domicilios en toda Pereira y Dosquebradas 🛵",
    ),
    (
        ["grooming", "baño", "bano", "peluqueria", "peluquería", "corte"],
        "🛁 ¡Tenemos servicio de grooming completo! Baño + peluquería + corte de uñas + limpieza de oídos. Agenda tu cita en mi.bigotesypaticas.com 📅",
    ),
    (
        ["veterinario", "veterinaria", "vet", "consulta", "médico", "medico"],
        "🩺 Tenemos consulta veterinaria disponible. Agenda tu cita en mi.bigotesypaticas.com o escríbenos al +57 320 687 6633 para más info.",
    ),
    (
        ["vacuna", "vacunacion", "vacunación"],
        "💉 Aplicamos vacunas para perros y gatos con carnet incluido. Agenda en mi.bigotesypaticas.com o al +57 320 687 6633.",
    ),
    (
        ["perro", "gato", "mascota", "cachorro", "felino", "canino"],
        "🐾 Tenemos TODO para tu mascota: alimento premium, accesorios, juguetes, higiene, vacunas y grooming. Cuéntame qué necesitas y te ayudo.",
    ),
    (
        ["portal", "cuenta", "puntos", "fidelidad", "registro"],
        "✨ Tienes un portal exclusivo en mi.bigotesypaticas.com donde puedes acumular puntos, agendar citas y pedir a domicilio. ¡Regístrate gratis!",
    ),
]

_DEFAULT_REPLY = (
    "¡Hola! 🐾 Gracias por escribir a Bigotes y Paticas. "
    "En breve un asesor te atiende. Mientras tanto, visita bigotesypaticas.com o "
    "llámanos al +57 320 687 6633."
)


def _detect_intent(text: str) -> str:
    text_lower = text.lower()
    for keywords, reply in _INTENTS:
        if any(k in text_lower for k in keywords):
            return reply
    return _DEFAULT_REPLY


def _send_message(recipient_id: str, text: str) -> None:
    try:
        requests.post(
            f"{_META_BASE}/me/messages",
            params={"access_token": _TOKEN()},
            json={"recipient": {"id": recipient_id}, "message": {"text": text}},
            timeout=8,
        )
    except Exception as exc:
        log.warning("Messenger send error: %s", exc)


def _handle_postback(sender_id: str, payload: str) -> None:
    if payload == "GET_STARTED":
        _send_message(
            sender_id,
            "¡Bienvenido a Bigotes y Paticas! 🐾\n\n"
            "Somos tu tienda de mascotas en Pereira y Dosquebradas.\n\n"
            "• 🛍️ Tienda: bigotesypaticas.com\n"
            "• 📱 Portal cliente: mi.bigotesypaticas.com\n"
            "• 📍 Mall Zamara Plaza, Local 2, Dosquebradas\n"
            "• 🕐 Lun–Sáb 10am–7pm\n\n"
            "¿En qué te puedo ayudar?",
        )
    elif payload == "VIEW_PRODUCTS":
        _send_message(sender_id, "🛍️ Explora nuestro catálogo completo en bigotesypaticas.com — más de 400 productos para tu mascota.")
    elif payload == "DELIVERY_INFO":
        _send_message(sender_id, "🛵 Domicilio GRATIS en Pereira y Dosquebradas para pedidos desde $30.000.\nHorario: Lun–Sáb 10am–7pm.\n¿Quieres hacer un pedido?")
    elif payload == "CONTACT_HUMAN":
        _send_message(sender_id, "👋 ¡Claro! Te conectamos con un asesor. Escríbenos al WhatsApp +57 320 687 6633 o espera unos minutos que alguien te atiende aquí.")


@router.get("")
async def verify_webhook(request: Request):
    """Verificación de webhook por Meta."""
    params = dict(request.query_params)
    if (
        params.get("hub.mode") == "subscribe"
        and params.get("hub.verify_token") == _VERIFY_TOKEN
    ):
        return PlainTextResponse(content=params["hub.challenge"])
    raise HTTPException(status_code=403, detail="Verificación fallida")


@router.post("")
async def receive_message(request: Request):
    """Recibe eventos de Messenger y responde automáticamente."""
    data = await request.json()

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                continue

            if "message" in event and not event["message"].get("is_echo"):
                text = event["message"].get("text", "")
                if text:
                    reply = _detect_intent(text)
                    _send_message(sender_id, reply)

            elif "postback" in event:
                _handle_postback(sender_id, event["postback"].get("payload", ""))

    return {"status": "ok"}
