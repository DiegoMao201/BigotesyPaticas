"""Portal Intelligence — Smart Cards + Profile Completion para el portal de clientes."""
from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import and_, desc, select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import Appointment, HealthRecord, Pet, PortalOrder

router = APIRouter(prefix="/portal/me", tags=["portal"])


# ── smart cards ──────────────────────────────────────────────────────────────

class SmartCard(BaseModel):
    type: str          # reorder | vaccine_due | appointment | birthday | loyalty
    pet_id: str | None = None
    pet_name: str | None = None
    color_theme: str = "teal"
    title: str
    subtitle: str
    cta: str
    action_url: str
    urgency: str       # high | medium | low
    badge: str | None = None   # "Atención" para high


@router.get("/smart-cards", response_model=list[SmartCard])
async def get_smart_cards(
    db: DBSession,
    customer: Customer = PortalUser,
) -> list[SmartCard]:
    today = date.today()
    now = datetime.now(UTC)
    cards: list[dict[str, Any]] = []

    # ── Mascotas activas ─────────────────────────────────────────────────
    pets = (
        await db.execute(
            select(Pet).where(
                and_(Pet.customer_id == customer.id, Pet.deleted_at == None)  # noqa: E711
            )
        )
    ).scalars().all()

    # ── Último pedido por producto (para recompra) ───────────────────────
    last_orders = (
        await db.execute(
            select(PortalOrder)
            .where(
                and_(
                    PortalOrder.customer_id == customer.id,
                    PortalOrder.status.notin_(["cancelled"]),
                )
            )
            .order_by(desc(PortalOrder.created_at))
            .limit(20)
        )
    ).scalars().all()

    last_order_by_pet: dict[str, PortalOrder] = {}
    for o in last_orders:
        pid = str(o.pet_id) if o.pet_id else "__general__"
        if pid not in last_order_by_pet:
            last_order_by_pet[pid] = o

    # ── Próximas citas ───────────────────────────────────────────────────
    upcoming_appts = (
        await db.execute(
            select(Appointment)
            .where(
                and_(
                    Appointment.customer_id == customer.id,
                    Appointment.scheduled_at >= now,
                    Appointment.scheduled_at <= now + timedelta(days=7),
                    Appointment.status.notin_(["cancelled", "completed"]),
                )
            )
            .order_by(Appointment.scheduled_at)
            .limit(3)
        )
    ).scalars().all()

    # ── Calcular cards ───────────────────────────────────────────────────
    for pet in pets:
        # 1. Recompra de comida
        if pet.food_freq_days:
            last = last_order_by_pet.get(str(pet.id))
            if last:
                dias_desde = (today - last.created_at.date()).days
                dias_restantes = pet.food_freq_days - dias_desde
                if dias_restantes <= 7:
                    urgency = "high" if dias_restantes <= 2 else "medium"
                    cards.append({
                        "type": "reorder",
                        "pet_id": str(pet.id),
                        "pet_name": pet.name,
                        "color_theme": pet.color_theme,
                        "title": f"{pet.name} necesita comida",
                        "subtitle": (
                            "¡Ya se acabó!" if dias_restantes <= 0
                            else f"Se acaba en {dias_restantes} día{'s' if dias_restantes != 1 else ''}"
                        ),
                        "cta": "Pedir ahora",
                        "action_url": f"/orders/new",
                        "urgency": urgency,
                        "badge": "Atención" if urgency == "high" else None,
                        "_sort": 10 if urgency == "high" else 20,
                    })

        # 2. Vacunas / salud próximas
        if pet.health_records:
            for hr in pet.health_records:
                if hr.next_due_at:
                    nd = hr.next_due_at if isinstance(hr.next_due_at, date) else hr.next_due_at.date()
                    dias = (nd - today).days
                    if dias <= 30:
                        urgency = "high" if dias <= 7 else "medium"
                        tipo = hr.record_type.capitalize() if hr.record_type else "Vacuna"
                        cards.append({
                            "type": "vaccine_due",
                            "pet_id": str(pet.id),
                            "pet_name": pet.name,
                            "color_theme": pet.color_theme,
                            "title": f"{tipo}: {hr.name}",
                            "subtitle": (
                                "Vencida" if dias < 0
                                else f"Vence en {dias} día{'s' if dias != 1 else ''}"
                            ),
                            "cta": "Agendar",
                            "action_url": "/appointments/new",
                            "urgency": urgency,
                            "badge": "Atención" if dias <= 7 else None,
                            "_sort": 5 if dias < 0 else (12 if urgency == "high" else 25),
                        })

        # 3. Cumpleaños (próximos 7 días)
        if pet.birth_date:
            bd = pet.birth_date if isinstance(pet.birth_date, date) else pet.birth_date.date()
            # Calcular próximo cumpleaños
            next_bd = bd.replace(year=today.year)
            if next_bd < today:
                next_bd = bd.replace(year=today.year + 1)
            dias_bd = (next_bd - today).days
            if dias_bd <= 7:
                age = next_bd.year - bd.year
                cards.append({
                    "type": "birthday",
                    "pet_id": str(pet.id),
                    "pet_name": pet.name,
                    "color_theme": pet.color_theme,
                    "title": f"🎂 {pet.name} cumple {age} años",
                    "subtitle": (
                        "¡Hoy es su día!" if dias_bd == 0
                        else f"En {dias_bd} día{'s' if dias_bd != 1 else ''}"
                    ),
                    "cta": "Ver mascota",
                    "action_url": f"/pets/{pet.id}",
                    "urgency": "medium",
                    "badge": "🎂 Cumpleaños" if dias_bd == 0 else None,
                    "_sort": 30,
                })

    # 4. Citas próximas
    for appt in upcoming_appts:
        # Buscar la mascota
        pet_obj = next((p for p in pets if p.id == appt.pet_id), None)
        pet_name = pet_obj.name if pet_obj else "Tu mascota"
        color_theme = pet_obj.color_theme if pet_obj else "teal"
        fecha = appt.scheduled_at
        dias = (fecha.date() - today).days
        fecha_str = (
            "Hoy" if dias == 0
            else "Mañana" if dias == 1
            else fecha.strftime("%A %d, %I:%M %p")
        )
        service = appt.service_type.capitalize()
        cards.append({
            "type": "appointment",
            "pet_id": str(appt.pet_id) if appt.pet_id else None,
            "pet_name": pet_name,
            "color_theme": color_theme,
            "title": f"{service} · {pet_name}",
            "subtitle": fecha_str,
            "cta": "Ver detalles",
            "action_url": f"/appointments",
            "urgency": "high" if dias == 0 else "medium",
            "badge": "Hoy" if dias == 0 else None,
            "_sort": 8 if dias == 0 else 22,
        })

    # Ordenar por prioridad y devolver máximo 6
    cards.sort(key=lambda c: c.get("_sort", 50))
    for c in cards:
        c.pop("_sort", None)

    return [SmartCard(**c) for c in cards[:6]]


# ── profile completion ────────────────────────────────────────────────────────

class MissingField(BaseModel):
    entity: str       # "customer" | "pet"
    entity_id: str | None = None
    field: str
    label: str
    reason: str
    points_reward: int
    priority: int


class CompletionResponse(BaseModel):
    percentage: int
    missing_fields: list[MissingField]


@router.get("/completion", response_model=CompletionResponse)
async def get_completion(
    db: DBSession,
    customer: Customer = PortalUser,
) -> CompletionResponse:
    fields: list[dict] = []
    total = 0
    completed = 0
    priority = 1

    # Customer fields
    customer_checks = [
        ("address", "Tu dirección", "para entregar tus pedidos", 30),
        ("email", "Tu correo", "para enviarte tu carnet en PDF", 20),
        ("city", "Tu ciudad", "para personalizar el servicio", 10),
    ]
    for field, label, reason, pts in customer_checks:
        total += 1
        val = getattr(customer, field, None)
        if val:
            completed += 1
        else:
            fields.append({
                "entity": "customer",
                "entity_id": None,
                "field": field,
                "label": label,
                "reason": reason,
                "points_reward": pts,
                "priority": priority,
            })
        priority += 1

    # Pet fields (primera mascota activa)
    pets = (
        await db.execute(
            select(Pet).where(
                and_(Pet.customer_id == customer.id, Pet.deleted_at == None)  # noqa: E711
            ).order_by(Pet.created_at).limit(3)
        )
    ).scalars().all()

    pet_checks = [
        ("birth_date", "Cumpleaños de {name}", "para recordarte sus vacunas y celebrar su cumple 🎂", 50),
        ("weight_kg", "Peso de {name}", "para sugerir la porción correcta", 20),
        ("breed", "Raza de {name}", "para personalizar nuestras recomendaciones", 15),
        ("photo_url", "Foto de {name}", "para que se vea hermosa en su perfil 📸", 25),
        ("food_brand", "Alimento de {name}", "para recordarte cuando se acabe", 20),
    ]

    for pet in pets[:2]:  # máximo 2 mascotas
        for field, label_tmpl, reason, pts in pet_checks:
            total += 1
            val = getattr(pet, field, None)
            label = label_tmpl.format(name=pet.name)
            if val:
                completed += 1
            else:
                fields.append({
                    "entity": "pet",
                    "entity_id": str(pet.id),
                    "field": field,
                    "label": label,
                    "reason": reason,
                    "points_reward": pts,
                    "priority": priority,
                })
            priority += 1

    pct = int((completed / max(total, 1)) * 100)

    return CompletionResponse(
        percentage=pct,
        missing_fields=[MissingField(**f) for f in fields[:5]],
    )
