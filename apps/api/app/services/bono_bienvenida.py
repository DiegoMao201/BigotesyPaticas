"""Bono de bienvenida PRIMERAPATA: las reglas y el canje (30-oct-2026).

Diego: *"una persona se registró y le llegó el bono al correo... yo ese bono
tendría que registrarlo en la venta para que el sistema admin le calcule el
descuento y que se diferencie claramente que es bono por registrarse"*.

Hasta hoy el cupón solo existía como texto dentro del correo de bienvenida del
newsletter (`contact.py`): ninguna tabla lo conocía, nadie podía validarlo, no
quedaba marcado como usado y en la venta se perdía entre los descuentos de línea.

Aquí viven las reglas, las mismas que promete el correo:

- **$5.000** de descuento, en compras **desde $30.000**.
- **30 días** desde que llegó el correo de bienvenida.
- **Un uso por correo**, y solo en la **primera compra** del cliente.

La identidad del bono es el **correo del suscriptor**: el código es el mismo para
todos, así que se canjea diciendo el correo, no el código. Queda escrito en
`crm.newsletter_subscribers` (cuándo se usó, en qué venta y para qué cliente) y
en la venta (`metadata.bono`), para que el comprobante y el admin lo muestren
aparte de cualquier otro descuento.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import text

CODIGO = "PRIMERAPATA"
VALOR = Decimal("5000")
MINIMO = Decimal("30000")
DIAS_VIGENCIA = 30

_COLUMNAS = """
    s.id, s.email, s.subscribed_at, s.coupon_sent_at, s.coupon_redeemed_at,
    s.coupon_order_id, s.coupon_customer_id,
    o.order_number AS canjeado_orden, c.full_name AS cliente
"""
_DESDE = """
    FROM crm.newsletter_subscribers s
    LEFT JOIN sales.orders o ON o.id = s.coupon_order_id
    LEFT JOIN crm.customers c ON c.id = s.coupon_customer_id
"""


def _pesos(valor: Decimal | float) -> str:
    return f"${int(valor):,}".replace(",", ".")


def vence_en(fila: Mapping) -> datetime:
    enviado = fila["coupon_sent_at"] or fila["subscribed_at"]
    return enviado + timedelta(days=DIAS_VIGENCIA)


def estado(fila: Mapping, ahora: datetime | None = None) -> str:
    """'canjeado', 'vencido' o 'pendiente'. Función pura para poder probarla."""
    if fila.get("coupon_redeemed_at"):
        return "canjeado"
    if vence_en(fila) < (ahora or datetime.now(UTC)):
        return "vencido"
    return "pendiente"


def _salida(fila: Mapping) -> dict:
    return {
        "id": str(fila["id"]),
        "email": fila["email"],
        "codigo": CODIGO,
        "valor": int(VALOR),
        "minimo": int(MINIMO),
        "suscrito_en": fila["subscribed_at"].isoformat(),
        "vence_en": vence_en(fila).isoformat(),
        "estado": estado(fila),
        "canjeado_en": fila["coupon_redeemed_at"].isoformat()
        if fila["coupon_redeemed_at"]
        else None,
        "canjeado_orden": fila["canjeado_orden"],
        "cliente": fila["cliente"],
    }


async def listar(db, q: str | None = None) -> list[dict]:
    """Todos los bonos, pendientes primero y los más recientes arriba."""
    filas = (
        (
            await db.execute(
                text(
                    f"SELECT {_COLUMNAS} {_DESDE}"
                    " WHERE (:pat IS NULL OR s.email ILIKE :pat)"
                    " ORDER BY (s.coupon_redeemed_at IS NULL) DESC, s.subscribed_at DESC"
                ),
                {"pat": f"%{q.strip()}%" if q and q.strip() else None},
            )
        )
        .mappings()
        .all()
    )
    return [_salida(f) for f in filas]


async def validar(db, email: str, base: Decimal, customer_id: uuid.UUID | None) -> Mapping:
    """Devuelve la fila del suscriptor si el bono se puede usar; si no, explica por qué."""
    email = email.strip().lower()
    fila = (
        (
            await db.execute(
                text(f"SELECT {_COLUMNAS} {_DESDE} WHERE s.email = :e FOR UPDATE OF s"),
                {"e": email},
            )
        )
        .mappings()
        .first()
    )
    if fila is None:
        raise HTTPException(
            status_code=400,
            detail=f"{email} no tiene bono de bienvenida: no está suscrito al club.",
        )
    est = estado(fila)
    if est == "canjeado":
        cuando = fila["coupon_redeemed_at"].strftime("%d-%m-%Y")
        raise HTTPException(
            status_code=400,
            detail=f"El bono de {email} ya se usó en la venta {fila['canjeado_orden']} el {cuando}.",
        )
    if est == "vencido":
        raise HTTPException(
            status_code=400,
            detail=(
                f"El bono de {email} venció el {vence_en(fila).strftime('%d-%m-%Y')}: "
                f"dura {DIAS_VIGENCIA} días desde el correo de bienvenida."
            ),
        )
    if base < MINIMO:
        raise HTTPException(
            status_code=400,
            detail=(
                f"El bono aplica en compras desde {_pesos(MINIMO)} y esta va en "
                f"{_pesos(base)}: faltan {_pesos(MINIMO - base)}."
            ),
        )
    if customer_id is not None:
        previas = (
            await db.execute(
                text(
                    "SELECT count(*) FROM sales.orders"
                    " WHERE customer_id = :c AND status <> 'cancelled'"
                ),
                {"c": str(customer_id)},
            )
        ).scalar_one()
        if previas:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"El bono es para la primera compra y este cliente ya tiene "
                    f"{previas} venta(s) registradas."
                ),
            )
    return fila


async def canjear(db, subscriber_id, order_id, customer_id) -> None:
    """Marca el bono como usado. Si otro lo usó un instante antes, no se aplica dos veces."""
    res = await db.execute(
        text(
            "UPDATE crm.newsletter_subscribers"
            " SET coupon_redeemed_at = now(), coupon_order_id = :o, coupon_customer_id = :c"
            " WHERE id = :id AND coupon_redeemed_at IS NULL"
        ),
        {
            "id": str(subscriber_id),
            "o": str(order_id),
            "c": str(customer_id) if customer_id else None,
        },
    )
    if res.rowcount != 1:
        raise HTTPException(status_code=409, detail="Ese bono acaba de usarse en otra venta.")


async def liberar(db, order_id) -> None:
    """Al anular la venta el bono vuelve a quedar disponible: la persona no lo gastó."""
    await db.execute(
        text(
            "UPDATE crm.newsletter_subscribers"
            " SET coupon_redeemed_at = NULL, coupon_order_id = NULL, coupon_customer_id = NULL"
            " WHERE coupon_order_id = :o"
        ),
        {"o": str(order_id)},
    )
