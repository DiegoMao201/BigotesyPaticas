"""Reserva pública de peluquería desde la web (bigotesypaticas.com/peluqueria), SIN cuenta.

Diego (28-sep-2026): "lo importante es captar ese clic en un cliente… conectar esa página
al flujo de citas y no poner esa camisa de fuerza de que se logueen". El anuncio de Google
llevaba a /appointments/new del portal, que exige cédula + registro de 5 pasos.

La cita entra al MISMO flujo que las del portal (portal.appointments, status pending,
aviso a los admins, Portal Monitor → Citas), con la misma disponibilidad (compute_slots).
Cliente: si el teléfono ya es de UN cliente, la cita queda a su nombre; si no, se crea un
cliente nuevo sin cédula. La respuesta nunca devuelve datos de clientes existentes.
"""

from __future__ import annotations

import re
import time
from collections import deque
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select

from app.api.v1.portal_appointments import (
    _TZ_CO,
    AvailabilityOut,
    compute_slots,
    ensure_slot_free,
)
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import Appointment, Pet

router = APIRouter(prefix="/public/grooming", tags=["public"])

DURACION = 120
NOTA_WEB = "Reservó en la web (bigotesypaticas.com/peluqueria): 10% de descuento en el servicio."
MAX_DIAS = 30               # hasta un mes adelante
MAX_CITAS_POR_TELEFONO = 2  # citas futuras pendientes/confirmadas por número
MAX_POR_IP_HORA = 20  # por si la IP llega agrupada detrás del proxy de la tienda

_por_ip: dict[str, deque] = {}


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "?"


def _frenar_abuso(ip: str) -> None:
    ahora = time.monotonic()
    q = _por_ip.setdefault(ip, deque())
    while q and ahora - q[0] > 3600:
        q.popleft()
    if len(q) >= MAX_POR_IP_HORA:
        raise HTTPException(status_code=429, detail="Demasiadas reservas seguidas. Escríbenos por WhatsApp, por favor.")
    q.append(ahora)
    if len(_por_ip) > 5000:  # no crecer sin límite
        for k in list(_por_ip)[:1000]:
            _por_ip.pop(k, None)


def _celular(raw: str) -> str:
    """Celular colombiano de 10 dígitos (3xx…). Acepta +57, espacios y guiones."""
    d = re.sub(r"\D", "", raw or "")
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    if not re.fullmatch(r"3\d{9}", d):
        raise HTTPException(status_code=422, detail="Escribe un celular de 10 dígitos, por ejemplo 320 687 6633.")
    return d


def _fecha(raw: str) -> date:
    try:
        f = date.fromisoformat(raw)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="Fecha inválida") from exc
    hoy = datetime.now(_TZ_CO).date()
    if f < hoy or f > hoy + timedelta(days=MAX_DIAS):
        raise HTTPException(status_code=422, detail="Elige una fecha dentro del próximo mes")
    return f


@router.get("/availability", response_model=AvailabilityOut)
async def disponibilidad(db: DBSession, date_str: str = Query(..., alias="date")) -> AvailabilityOut:
    f = _fecha(date_str)
    return AvailabilityOut(date=date_str, service="grooming", slots=await compute_slots(db, f, DURACION))


class ReservaIn(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=20)
    pet_name: str = Field(min_length=1, max_length=60)
    species: str = Field(pattern="^(perro|gato)$")
    date: str
    time: str = Field(pattern=r"^\d{2}:00$")
    notes: str | None = Field(default=None, max_length=500)
    accept_data: bool
    website: str | None = None  # trampa para bots: una persona nunca lo llena


@router.post("/book", status_code=status.HTTP_201_CREATED)
async def reservar(payload: ReservaIn, request: Request, db: DBSession) -> dict:
    if payload.website:  # bot: respondemos "ok" sin guardar nada
        return {"ok": True}
    if not payload.accept_data:
        raise HTTPException(status_code=422, detail="Necesitamos tu autorización de datos para confirmarte la cita.")
    _frenar_abuso(_ip(request))

    tel = _celular(payload.phone)
    f = _fecha(payload.date)
    h = int(payload.time[:2])
    inicio = datetime(f.year, f.month, f.day, h, 0, tzinfo=_TZ_CO)
    await ensure_slot_free(db, inicio, DURACION)

    nombre = re.sub(r"\s+", " ", payload.full_name).strip()
    mascota = re.sub(r"\s+", " ", payload.pet_name).strip()

    # ¿Ya es cliente? Solo si el número pertenece a UN cliente (sin ambigüedad).
    digitos = func.regexp_replace(Customer.phone, r"\D", "", "g")
    candidatos = (
        await db.execute(
            select(Customer).where(
                and_(Customer.deleted_at.is_(None), digitos.in_([tel, "57" + tel]))
            ).limit(2)
        )
    ).scalars().all()
    ahora = datetime.now(_TZ_CO)
    if len(candidatos) == 1:
        cliente = candidatos[0]
        if not cliente.full_name:
            cliente.full_name = nombre
        if cliente.data_consent_at is None:
            cliente.data_consent_at = ahora
        # autorización comercial (ventana de la web): se guarda con fecha y origen
        cliente.extra = {**(cliente.extra or {}), "consent_comercial_at": ahora.isoformat(),
                         "consent_comercial_origen": "reserva_web_peluqueria"}
    else:
        cliente = Customer(
            full_name=nombre,
            phone=tel,
            extra={"origen": "reserva_web_peluqueria", "consent_comercial_at": ahora.isoformat(),
                   "consent_comercial_origen": "reserva_web_peluqueria"},
            data_consent_at=ahora,
            consent_version="1.0",
        )
        db.add(cliente)
        await db.flush()

    futuras = (
        await db.execute(
            select(func.count()).select_from(Appointment).where(
                and_(
                    Appointment.customer_id == cliente.id,
                    Appointment.scheduled_at >= datetime.now(_TZ_CO),
                    Appointment.status.in_(["pending", "confirmed"]),
                )
            )
        )
    ).scalar_one()
    if futuras >= MAX_CITAS_POR_TELEFONO:
        raise HTTPException(
            status_code=409,
            detail="Ya tienes citas pendientes con este número. Escríbenos por WhatsApp y te ayudamos.",
        )

    pet = (
        await db.execute(
            select(Pet).where(
                and_(
                    Pet.customer_id == cliente.id,
                    Pet.deleted_at.is_(None),
                    func.lower(Pet.name) == mascota.lower(),
                )
            ).limit(1)
        )
    ).scalar_one_or_none()
    if pet is None:
        pet = Pet(customer_id=cliente.id, name=mascota, species=payload.species,
                  color_theme="teal", notes="Registrada desde la reserva web de peluquería")
        db.add(pet)
        await db.flush()

    notas = [NOTA_WEB, f"Tel: {tel}", f"{'Perro' if payload.species == 'perro' else 'Gato'}: {mascota}"]
    if payload.notes and payload.notes.strip():
        notas.append(payload.notes.strip())
    appt = Appointment(
        pet_id=pet.id,
        customer_id=cliente.id,
        service_type="grooming",
        scheduled_at=inicio,
        duration_min=DURACION,
        status="pending",
        notes=" · ".join(notas),
    )
    db.add(appt)
    await db.flush()

    fecha_txt = inicio.strftime("%d/%m/%Y a las %H:%M")
    try:
        from app.api.v1.portal_notifications import notify_admins

        await notify_admins(
            db,
            notif_type="new_appointment",
            title="Nueva cita desde la web: peluquería",
            body=f"{nombre} ({tel}) reservó para {mascota} el {fecha_txt}",
            data={"appointment_id": str(appt.id), "customer_id": str(cliente.id), "origen": "web"},
        )
    except Exception:
        pass

    await db.commit()
    return {"ok": True, "fecha": inicio.date().isoformat(), "hora": payload.time, "mascota": mascota}
