"""Portal Pets — CRUD de mascotas + carnet de salud + generación PDF."""
from __future__ import annotations

import io
import os
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status
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


class PetUpdate(BaseModel):
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    birth_date: str | None = None
    weight_kg: float | None = None
    food_brand: str | None = None
    food_freq_days: int | None = None
    color_theme: str | None = None
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
    thumb_url: str | None = None
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
        thumb_url=getattr(pet, 'thumb_url', None),
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
    payload: PetUpdate,
    db: DBSession,
    customer: Customer = PortalUser,
) -> PetOut:
    pet = await _get_own_pet(pet_id, customer, db)
    if payload.color_theme is not None and payload.color_theme not in COLOR_THEMES:
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


# ── foto de mascota (upload nativo) ──────────────────────────────────

_UPLOAD_DIR = Path(os.getenv("PORTAL_UPLOADS_PATH", "/data/portal-uploads"))
_ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@router.post("/{pet_id}/photo", response_model=PetOut)
async def upload_pet_photo(
    pet_id: uuid.UUID,
    file: UploadFile = File(...),
    db: DBSession = None,
    customer: Customer = PortalUser,
) -> PetOut:
    """Sube una foto para la mascota: valida tipo + tamaño, comprime con Pillow y guarda."""
    pet = await _get_own_pet(pet_id, customer, db)

    if file.content_type not in _ALLOWED_TYPES:
        raise HTTPException(status_code=422, detail="Solo se aceptan imágenes JPEG, PNG o WebP")

    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(status_code=413, detail="La imagen no debe superar 5 MB")

    # Comprimir con Pillow si está disponible; si no, guardar original
    ext = "jpg"
    thumb_data: bytes | None = None
    try:
        from PIL import Image as PILImage

        img = PILImage.open(io.BytesIO(contents)).convert("RGB")

        # Thumbnail 150x150
        thumb = img.copy()
        thumb.thumbnail((150, 150), PILImage.LANCZOS)
        tbuf = io.BytesIO()
        thumb.save(tbuf, format="JPEG", quality=80, optimize=True)
        thumb_data = tbuf.getvalue()

        # Imagen principal 800x800
        img.thumbnail((800, 800), PILImage.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85, optimize=True)
        data = buf.getvalue()
        ext = "jpg"
    except (ImportError, Exception):
        # Pillow no disponible o imagen no válida — guardar original
        thumb_data = None
        data = contents
        ext = (file.filename or "photo.jpg").rsplit(".", 1)[-1].lower()
        if ext not in {"jpg", "jpeg", "png", "webp"}:
            ext = "jpg"
        if ext == "jpeg":
            ext = "jpg"

    # Guardar en disco
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest = _UPLOAD_DIR / f"pets/{pet_id}.{ext}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)

    thumb_url: str | None = None
    if thumb_data:
        thumb_dest = _UPLOAD_DIR / f"pets/{pet_id}_thumb.jpg"
        thumb_dest.write_bytes(thumb_data)
        thumb_url = f"/media/pets/{pet_id}_thumb.jpg"

    # Actualizar URL en DB (servida por StaticFiles bajo /media/pets/)
    pet.photo_url = f"/media/pets/{pet_id}.{ext}"
    if thumb_url:
        pet.thumb_url = thumb_url
    await db.commit()
    await db.refresh(pet)
    return _pet_out(pet)


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


# ── color por tema ────────────────────────────────────────────────────

_THEME_COLORS = {
    "teal":   {"accent": "#187f77", "bg_light": "#edfaf9", "text_dark": "#085041"},
    "coral":  {"accent": "#D85A30", "bg_light": "#FAECE7", "text_dark": "#712B13"},
    "amber":  {"accent": "#BA7517", "bg_light": "#FAEEDA", "text_dark": "#633806"},
    "purple": {"accent": "#534AB7", "bg_light": "#EEEDFE", "text_dark": "#3C3489"},
    "pink":   {"accent": "#D4537E", "bg_light": "#FBEAF0", "text_dark": "#72243E"},
    "green":  {"accent": "#639922", "bg_light": "#EAF3DE", "text_dark": "#27500A"},
}

_SPECIES_EMOJI = {
    "perro": "🐶", "dog": "🐶",
    "gato": "🐱", "cat": "🐱",
    "conejo": "🐰", "rabbit": "🐰",
    "hamster": "🐹", "conejillo": "🐹",
    "ave": "🐦", "bird": "🐦",
    "pez": "🐟", "fish": "🐟",
}


# ── PDF carnet ────────────────────────────────────────────────────────

@router.get("/{pet_id}/carnet.pdf")
async def carnet_pdf(
    pet_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> Response:
    """Genera un PDF A5 horizontal con el carnet de salud de la mascota."""
    pet = await _get_own_pet(pet_id, customer, db)

    # Intentar WeasyPrint primero (mejor diseño), fallback a reportlab
    try:
        return await _carnet_weasyprint(pet, customer)
    except Exception:
        return _carnet_reportlab(pet, customer)


async def _carnet_weasyprint(pet: Pet, customer: Customer) -> Response:
    from jinja2 import Environment, FileSystemLoader
    from weasyprint import HTML  # type: ignore[import]

    templates_dir = Path(__file__).parent.parent.parent.parent / "templates"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    tmpl = env.get_template("carnet_pet.html")

    theme = _THEME_COLORS.get(pet.color_theme, _THEME_COLORS["teal"])
    today = date.today()

    records = sorted(pet.health_records or [], key=lambda r: str(r.applied_at), reverse=True)
    has_action_required = any(
        getattr(r, "next_due_at", None) and
        (r.next_due_at if isinstance(r.next_due_at, date) else r.next_due_at.date()) <= today + timedelta(days=7)
        for r in records
    )

    # Construir lista de records con alert_level calculado
    record_list = []
    for hr in records[:8]:
        nd = hr.next_due_at
        if nd:
            nd_date = nd if isinstance(nd, date) else nd.date()
            days = (nd_date - today).days
            alert = "overdue" if days < 0 else ("soon" if days <= 30 else "ok")
        else:
            alert = None
        record_list.append({
            "record_type": hr.record_type,
            "name": hr.name,
            "applied_at": str(hr.applied_at if isinstance(hr.applied_at, date) else hr.applied_at.date()),
            "next_due_at": str(nd if isinstance(nd, date) else nd.date()) if nd else None,
            "vet_name": hr.vet_name,
            "alert_level": alert,
        })

    class _PetCtx:
        pass

    pet_ctx = _PetCtx()
    pet_ctx.id = str(pet.id)
    pet_ctx.name = pet.name
    pet_ctx.species = pet.species
    pet_ctx.breed = pet.breed
    pet_ctx.birth_date = str(pet.birth_date) if pet.birth_date else None
    pet_ctx.weight_kg = float(pet.weight_kg) if pet.weight_kg else None
    pet_ctx.food_brand = pet.food_brand
    pet_ctx.food_freq_days = pet.food_freq_days
    pet_ctx.photo_url = pet.photo_url
    pet_ctx.age_years = None
    if pet.birth_date:
        bd = pet.birth_date if isinstance(pet.birth_date, date) else pet.birth_date.date()
        pet_ctx.age_years = (today - bd).days // 365

    html_str = tmpl.render(
        pet=pet_ctx,
        owner=customer,
        records=record_list,
        emoji=_SPECIES_EMOJI.get(pet.species.lower(), "🐾"),
        today=today.strftime("%d/%m/%Y"),
        has_action_required=has_action_required,
        accent=theme["accent"],
        bg_light=theme["bg_light"],
        text_dark=theme["text_dark"],
    )

    pdf_bytes = HTML(string=html_str).write_pdf()
    filename = f"carnet_{pet.name.lower().replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


def _carnet_reportlab(pet: Pet, customer: Customer) -> Response:
    """Fallback PDF con reportlab cuando WeasyPrint no está disponible."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A5, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    theme = _THEME_COLORS.get(pet.color_theme, _THEME_COLORS["teal"])
    BRAND = colors.HexColor(theme["accent"])
    BG = colors.HexColor(theme["bg_light"])

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A5),
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.2 * cm, bottomMargin=1.2 * cm,
    )
    styles = getSampleStyleSheet()
    title_st = ParagraphStyle("t", parent=styles["Heading1"], textColor=BRAND, fontSize=18, spaceAfter=3)
    sub_st = ParagraphStyle("s", parent=styles["Normal"], fontSize=9, spaceAfter=2)
    foot_st = ParagraphStyle("f", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#9ca3af"))

    story = []
    story.append(Paragraph(f"🐾 {pet.name} — Carnet de Salud", title_st))
    story.append(Paragraph(f"Bigotes y Paticas · {pet.species.capitalize()}", sub_st))
    story.append(Spacer(1, 0.3 * cm))

    bd = str(pet.birth_date) if pet.birth_date else "—"
    data = [
        ["Raza", pet.breed or "—", "Nacimiento", bd],
        ["Peso", f"{pet.weight_kg} kg" if pet.weight_kg else "—", "Alimento", pet.food_brand or "—"],
        ["Dueño", customer.full_name or "—", "Teléfono", customer.phone or "—"],
    ]
    t = Table(data, colWidths=[2.5 * cm, 5 * cm, 2.5 * cm, 5 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), BG),
        ("BACKGROUND", (2, 0), (2, -1), BG),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#e5e7eb")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.4 * cm))

    records = sorted(pet.health_records or [], key=lambda r: str(r.applied_at), reverse=True)
    if records:
        story.append(Paragraph("Historial de Salud", title_st))
        hr_data = [["Tipo", "Detalle", "Aplicado", "Próxima dosis", "Vet."]]
        for hr in records[:6]:
            nd = str(hr.next_due_at) if hr.next_due_at else "—"
            hr_data.append([hr.record_type.capitalize(), hr.name, str(hr.applied_at), nd, hr.vet_name or "—"])
        ht = Table(hr_data, colWidths=[2 * cm, 5.5 * cm, 2.2 * cm, 2.5 * cm, 2.8 * cm])
        ht.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), BRAND),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, BG]),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e5e7eb")),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(ht)

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        f"Generado el {date.today().strftime('%d/%m/%Y')} · mi.bigotesypaticas.com", foot_st,
    ))

    doc.build(story)
    buf.seek(0)
    filename = f"carnet_{pet.name.lower().replace(' ', '_')}.pdf"
    return Response(
        content=buf.read(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )
