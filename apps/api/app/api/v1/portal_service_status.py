"""Portal Service Status — horarios y disponibilidad de despacho."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter

router = APIRouter(prefix="/portal/service-status", tags=["portal"])

_TZ = ZoneInfo("America/Bogota")
_DAY_NAMES = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


@router.get("")
async def service_status() -> dict:
    """Retorna el estado del servicio de despacho según horario y día configurados."""
    now_co = datetime.now(_TZ)

    delivery_days = os.getenv(
        "PORTAL_DELIVERY_DAYS",
        "monday,tuesday,wednesday,thursday,friday,saturday",
    ).split(",")
    current_day = _DAY_NAMES[now_co.weekday()]

    hours_start = int(os.getenv("PORTAL_DELIVERY_HOURS_START", "9"))
    hours_end = int(os.getenv("PORTAL_DELIVERY_HOURS_END", "19"))
    min_order = int(os.getenv("PORTAL_MIN_ORDER_AMOUNT", "25000"))
    cities = os.getenv("PORTAL_DELIVERY_CITIES", "Pereira,Dosquebradas").split(",")

    is_delivery_day = current_day in delivery_days
    is_delivery_hour = hours_start <= now_co.hour < hours_end

    # Mensaje contextual
    message: str | None = None
    if now_co.weekday() == 6:  # Domingo
        message = (
            "Hoy domingo no hacemos entregas. "
            "Haz tu pedido y lo despachamos el lunes a primera hora 🐾"
        )
    elif not is_delivery_day:
        message = (
            "Hoy no es día de despacho. " "Recibimos tu pedido y lo enviamos el próximo día hábil."
        )
    elif not is_delivery_hour:
        if now_co.hour >= hours_end:
            message = (
                "Estamos fuera de horario. "
                f"Recibimos tu pedido y lo enviamos mañana entre las {hours_start}am y {hours_end - 12}pm."
            )
        else:
            message = (
                f"Aún no hemos iniciado despachos. "
                f"Tu pedido saldrá hoy a partir de las {hours_start}am."
            )

    # Estimado de entrega
    if is_delivery_day and is_delivery_hour:
        next_delivery = "hoy mismo" if now_co.hour < 16 else "hoy en la tarde o mañana temprano"
    elif now_co.weekday() == 6:
        next_delivery = "lunes en la mañana"
    else:
        next_delivery = "mañana en el día"

    return {
        "now_co": now_co.isoformat(),
        "is_delivery_day": is_delivery_day,
        "is_delivery_hour": is_delivery_hour,
        "next_delivery_window": next_delivery,
        "min_order_amount": min_order,
        "delivery_cities": cities,
        "message": message,
    }
