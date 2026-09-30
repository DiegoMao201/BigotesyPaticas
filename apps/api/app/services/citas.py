"""Cliente y mascota de una cita, a partir de nombre + teléfono (29-sep-2026).

Lo comparten la reserva pública de la web (/v1/public/grooming) y el agendamiento del
admin (en tienda o por llamada), para que las dos entradas traten igual a las personas:
si el teléfono es de UN solo cliente se usa ese (sin cambiarle el nombre); si no existe
o es ambiguo, se crea uno nuevo sin cédula. La mascota se reutiliza por nombre.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import and_, func, select

from app.models.crm import Customer
from app.models.portal import Pet


def limpiar(texto: str) -> str:
    return re.sub(r"\s+", " ", texto or "").strip()


def digitos_telefono(raw: str) -> str | None:
    """Celular colombiano → 10 dígitos (3xx…); otro país con + → '+<dígitos>'. None si no sirve."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    if re.fullmatch(r"3\d{9}", d):
        return d
    if (raw or "").strip().startswith("+") and 8 <= len(d) <= 15:
        return "+" + d
    return None


async def cliente_por_telefono(
    db, nombre: str, tel: str, origen: str, ahora: datetime, consentimiento: bool
) -> Customer:
    digitos = func.regexp_replace(Customer.phone, r"\D", "", "g")
    claves = [tel.lstrip("+")] + ([] if tel.startswith("+") else ["57" + tel])
    candidatos = (
        await db.execute(
            select(Customer).where(and_(Customer.deleted_at.is_(None), digitos.in_(claves))).limit(2)
        )
    ).scalars().all()
    if len(candidatos) == 1:
        cliente = candidatos[0]
        if not cliente.full_name:
            cliente.full_name = nombre
        if consentimiento:
            if cliente.data_consent_at is None:
                cliente.data_consent_at = ahora
            cliente.extra = {**(cliente.extra or {}), "consent_comercial_at": ahora.isoformat(),
                             "consent_comercial_origen": origen}
        return cliente
    extra: dict = {"origen": origen}
    if consentimiento:
        extra.update({"consent_comercial_at": ahora.isoformat(), "consent_comercial_origen": origen})
    cliente = Customer(
        full_name=nombre,
        phone=tel,
        extra=extra,
        data_consent_at=ahora if consentimiento else None,
        consent_version="1.0" if consentimiento else None,
    )
    db.add(cliente)
    await db.flush()
    return cliente


async def mascota_de(db, cliente: Customer, nombre: str, especie: str, nota: str) -> Pet:
    pet = (
        await db.execute(
            select(Pet).where(
                and_(
                    Pet.customer_id == cliente.id,
                    Pet.deleted_at.is_(None),
                    func.lower(Pet.name) == nombre.lower(),
                )
            ).limit(1)
        )
    ).scalar_one_or_none()
    if pet is None:
        pet = Pet(customer_id=cliente.id, name=nombre, species=especie, color_theme="teal", notes=nota)
        db.add(pet)
        await db.flush()
    return pet
