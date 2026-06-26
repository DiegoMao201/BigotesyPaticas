"""Portal Pets — CRUD de mascotas + carnet de salud + generación PDF."""
from __future__ import annotations

import io
import uuid
from datetime import date, datetime, timedelta

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import and_, select

from app.api.v1.portal_auth import PortalUser
from app.deps import DBSession
from app.models.crm import Customer
from app.models.portal import HealthRecord, Pet

router = APIRouter(prefix="/portal/pets", tags=["portal"])

COLOR_THEMES = {"teal", "coral", "amber", "purple", "pink", "green"}
RECORD_TYPES = {"vacuna", "desparasitacion", "consulta", "cirugia", "otro"}


# ── schemas ───────────────────────────────────────────────────────────

class PetIn(BaseModel):
    name: str
    species: str
    breed: str | None = None
    birth_date: str | None = None   # YYYY-MM-DD
    weight_kg: float | None = None
    food_brand: str | None = None
    food_freq_days: int | None = None
    color_theme: str = "teal"
    photo_url: str | None = None
    notes: str | None = None


class HealthRecordIn(BaseModel):
    record_type: str
    name: str
    applied_at: str          # YYYY-MM-DD
    next_due_at: str | None = None
    vet_name: str | None = None
    notes: str | None = None


class HealthRecordOut(BaseModel):
    id: str
    record_type: str
    name: str
    applied_at: str
    next_due_at: str | None
    vet_name: str | None
    notes: str | None
    created_at: str
    # helpers calculados
    days_until_due: int | None
    alert_level: str | None  # "ok" | "soon" | "overdue"


class PetOut(BaseModel):
    id: str
    name: str
    species: str
    breed: str | None
    birth_date: str | None
    weight_kg: float | None
    food_brand: str | None
    food_freq_days: int | None
    color_theme: str
    photo_url: str | None
    notes: str | None
    created_at: str
    age_years: int | None
    age_months: int | None
    health_records: list[HealthRecordOut]


def _pet_out(pet: Pet) -> PetOut:
    today = date.today()
    age_y = age_m = None
    if pet.birth_date:
        bd = pet.birth_date if isinstance(pet.birth_date, date) else pet.birth_date.date()
        delta_days = (today - bd).days
        age_y = delta_days // 365
        age_m = (delta_days % 365) // 30

    records = []
    for hr in (pet.health_records or []):
        nd = None
        if hr.next_due_at:
            nd_date = hr.next_due_at if isinstance(hr.next_due_at, date) else hr.next_due_at.date()
            nd = str(nd_date)
            days = (nd_date - today).days
            if days < 0:
                alert = "overdue"
            elif days <= 30:
                alert = "soon"
            else:
                alert = "ok"
            days_until = days
        else:
            days_until = None
            alert = None

        records.append(HealthRecordOut(
            id=str(hr.id),
            record_type=hr.record_type,
            name=hr.name,
            applied_at=str(hr.applied_at if isinstance(hr.applied_at, date) else hr.applied_at.date()),
            next_due_at=nd,
            vet_name=hr.vet_name,
            notes=hr.notes,
            created_at=hr.created_at.isoformat(),
            days_until_due=days_until,
            alert_level=alert,
        ))

    records.sort(key=lambda r: r.applied_at, reverse=True)

    return PetOut(
        id=str(pet.id),
        name=pet.name,
        species=pet.species,
        breed=pet.breed,
        birth_date=str(pet.birth_date) if pet.birth_date else None,
        weight_kg=float(pet.weight_kg) if pet.weight_kg else None,
        food_brand=pet.food_brand,
        food_freq_days=pet.food_freq_days,
        color_theme=pet.color_theme,
        photo_url=pet.photo_url,
        notes=pet.notes,
        created_at=pet.created_at.isoformat(),
        age_years=age_y,
        age_months=age_m,
        health_records=records,
    )


async def _get_own_pet(pet_id: uuid.UUID, customer: Customer, db: DBSession) -> Pet:
    pet = (
        await db.execute(
            select(Pet).where(
                and_(
                    Pet.id == pet_id,
                    Pet.customer_id == customer.id,
                    Pet.deleted_at == None,  # noqa: E711
                )
            )
        )
    ).scalar_one_or_none()
    if not pet:
        raise HTTPException(status_code=404, detail="Mascota no encontrada")
    return pet


# ── endpoints ─────────────────────────────────────────────────────────

@router.get("", response_model=list[PetOut])
async def list_pets(db: DBSession, customer: Customer = PortalUser) -> list[PetOut]:
    pets = (
        await db.execute(
            select(Pet).where(
                and_(Pet.customer_id == customer.id, Pet.deleted_at == None)  # noqa: E711
            ).order_by(Pet.created_at)
        )
    ).scalars().all()
    return [_pet_out(p) for p in pets]


@router.post("", response_model=PetOut, status_code=status.HTTP_201_CREATED)
async def create_pet(
    payload: PetIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> PetOut:
    if payload.color_theme not in COLOR_THEMES:
        raise HTTPException(status_code=422, detail=f"color_theme inválido. Opciones: {COLOR_THEMES}")
    pet = Pet(
        customer_id=customer.id,
        name=payload.name,
        species=payload.species,
        breed=payload.breed,
        birth_date=date.fromisoformat(payload.birth_date) if payload.birth_date else None,
        weight_kg=payload.weight_kg,
        food_brand=payload.food_brand,
        food_freq_days=payload.food_freq_days,
        color_theme=payload.color_theme,
        photo_url=payload.photo_url,
        notes=payload.notes,
    )
    db.add(pet)
    await db.commit()
    await db.refresh(pet)
    return _pet_out(pet)


@router.get("/{pet_id}", response_model=PetOut)
async def get_pet(
    pet_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> PetOut:
    pet = await _get_own_pet(pet_id, customer, db)
    return _pet_out(pet)


@router.patch("/{pet_id}", response_model=PetOut)
async def update_pet(
    pet_id: uuid.UUID,
    payload: PetIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> PetOut:
    pet = await _get_own_pet(pet_id, customer, db)
    if payload.color_theme not in COLOR_THEMES:
        raise HTTPException(status_code=422, detail=f"color_theme inválido. Opciones: {COLOR_THEMES}")
    for field, value in payload.model_dump(exclude_unset=True).items():
        if field == "birth_date" and value:
            setattr(pet, field, date.fromisoformat(value))
        else:
            setattr(pet, field, value)
    await db.commit()
    await db.refresh(pet)
    return _pet_out(pet)


@router.delete("/{pet_id}")
async def delete_pet(
    pet_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> dict:
    pet = await _get_own_pet(pet_id, customer, db)
    pet.deleted_at = datetime.utcnow()
    await db.commit()
    return {"ok": True}


# ── health records ────────────────────────────────────────────────────

@router.post("/{pet_id}/health", response_model=HealthRecordOut, status_code=201)
async def add_health_record(
    pet_id: uuid.UUID,
    payload: HealthRecordIn,
    db: DBSession,
    customer: Customer = PortalUser,
) -> HealthRecordOut:
    pet = await _get_own_pet(pet_id, customer, db)
    hr = HealthRecord(
        pet_id=pet.id,
        record_type=payload.record_type,
        name=payload.name,
        applied_at=date.fromisoformat(payload.applied_at),
        next_due_at=date.fromisoformat(payload.next_due_at) if payload.next_due_at else None,
        vet_name=payload.vet_name,
        notes=payload.notes,
    )
    db.add(hr)
    await db.commit()
    await db.refresh(hr)

    nd = str(hr.next_due_at) if hr.next_due_at else None
    days_until = alert = None
    if hr.next_due_at:
        nd_date = hr.next_due_at if isinstance(hr.next_due_at, date) else hr.next_due_at.date()
        days_until = (nd_date - date.today()).days
        alert = "overdue" if days_until < 0 else ("soon" if days_until <= 30 else "ok")

    return HealthRecordOut(
        id=str(hr.id),
        record_type=hr.record_type,
        name=hr.name,
        applied_at=str(hr.applied_at),
        next_due_at=nd,
        vet_name=hr.vet_name,
        notes=hr.notes,
        created_at=hr.created_at.isoformat(),
        days_until_due=days_until,
        alert_level=alert,
    )


# ── PDF carnet ────────────────────────────────────────────────────────

@router.get("/{pet_id}/carnet.pdf")
async def carnet_pdf(
    pet_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> Response:
    """Genera un PDF A4 con el carnet de vacunación / salud de la mascota."""
    pet = await _get_own_pet(pet_id, customer, db)

    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
        )
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="reportlab no está instalado. Agrega 'reportlab' a requirements.txt",
        )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )

    BRAND = colors.HexColor("#187f77")
    ACCENT = colors.HexColor("#f5a641")
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Heading1"],
        textColor=BRAND, fontSize=22, spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        textColor=colors.HexColor("#262730"), fontSize=11, spaceAfter=2,
    )
    label_style = ParagraphStyle(
        "label", parent=styles["Normal"],
        textColor=BRAND, fontSize=9, fontName="Helvetica-Bold",
    )

    story = []

    # Header
    story.append(Paragraph("🐾 Bigotes y Paticas", title_style))
    story.append(Paragraph("Carnet de Salud", sub_style))
    story.append(Spacer(1, 0.3 * cm))

    # Info mascota
    bd = str(pet.birth_date) if pet.birth_date else "—"
    pet_data = [
        ["Nombre", pet.name, "Especie", pet.species.capitalize()],
        ["Raza", pet.breed or "—", "Fecha nac.", bd],
        ["Peso", f"{pet.weight_kg} kg" if pet.weight_kg else "—", "Alimento", pet.food_brand or "—"],
        ["Dueño", customer.full_name or "—", "Teléfono", customer.phone or "—"],
    ]
    pet_table = Table(pet_data, colWidths=[3 * cm, 6 * cm, 3 * cm, 5 * cm])
    pet_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#edfaf9")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#edfaf9")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c4c8db")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(pet_table)
    story.append(Spacer(1, 0.5 * cm))

    # Registros de salud
    story.append(Paragraph("Historial de Salud", title_style))
    story.append(Spacer(1, 0.2 * cm))

    records = sorted(pet.health_records or [], key=lambda r: str(r.applied_at), reverse=True)
    if records:
        hr_data = [["Tipo", "Nombre / Detalle", "Aplicado", "Próxima dosis", "Veterinario"]]
        for hr in records:
            nd = str(hr.next_due_at) if hr.next_due_at else "—"
            hr_data.append([
                hr.record_type.capitalize(),
                hr.name,
                str(hr.applied_at),
                nd,
                hr.vet_name or "—",
            ])
        hr_table = Table(hr_data, colWidths=[2.5 * cm, 6 * cm, 2.5 * cm, 2.8 * cm, 3.2 * cm])
        hr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f2f9")]),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#c4c8db")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(hr_table)
    else:
        story.append(Paragraph("Sin registros de salud aún.", sub_style))

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(
        f"Generado el {date.today().strftime('%d/%m/%Y')} — mi.bigotesypaticas.com",
        ParagraphStyle("footer", parent=styles["Normal"], fontSize=7,
                       textColor=colors.HexColor("#7a7f99")),
    ))

    doc.build(story)
    buf.seek(0)
    filename = f"carnet_{pet.name.lower().replace(' ', '_')}.pdf"
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
