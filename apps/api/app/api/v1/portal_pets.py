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

_TEMPLATES_DIR = Path(__file__).parent.parent.parent / "templates"

# Jinja2 env con base_url para que WeasyPrint resuelva fonts/ y assets/
def _make_jinja_env():
    from jinja2 import Environment, FileSystemLoader

    def _fmt_date(d: object) -> str:
        if not d:
            return "—"
        if isinstance(d, str):
            try:
                from datetime import datetime as _dt
                d = _dt.fromisoformat(d).date()
            except Exception:
                return str(d)
        try:
            return d.strftime("%d/%m/%Y")  # type: ignore[attr-defined]
        except Exception:
            return str(d)

    env = Environment(loader=FileSystemLoader(str(_TEMPLATES_DIR)), autoescape=False)
    env.filters["format_date"] = _fmt_date
    return env


@router.get("/{pet_id}/carnet.pdf")
async def carnet_pdf(
    pet_id: uuid.UUID,
    db: DBSession,
    customer: Customer = PortalUser,
) -> Response:
    """Genera carnet de salud en PDF A5 vertical con WeasyPrint + Jinja2."""
    import base64
    from weasyprint import HTML  # type: ignore[import]

    pet = await _get_own_pet(pet_id, customer, db)
    today = date.today()

    # ── Logo: usar el archivo local en templates/assets/ ─────────────────
    logo_b64 = ""
    logo_path = _TEMPLATES_DIR / "assets" / "logo.png"
    if logo_path.exists():
        logo_b64 = base64.b64encode(logo_path.read_bytes()).decode()

    # ── Foto mascota ──────────────────────────────────────────────────────
    photo_b64 = ""
    if pet.photo_url:
        if pet.photo_url.startswith("http"):
            # Foto en CDN/Spaces
            try:
                import httpx
                async with httpx.AsyncClient(timeout=8) as client:
                    resp = await client.get(pet.photo_url)
                if resp.status_code == 200:
                    photo_b64 = base64.b64encode(resp.content).decode()
            except Exception:
                pass
        else:
            # Foto local en /data/portal-uploads
            try:
                local_photo = _UPLOAD_DIR / pet.photo_url.lstrip("/media/")
                if local_photo.exists():
                    photo_b64 = base64.b64encode(local_photo.read_bytes()).decode()
            except Exception:
                pass

    # ── QR code ───────────────────────────────────────────────────────────
    qr_b64 = ""
    try:
        import qrcode
        qr_img = qrcode.make(
            f"https://mi.bigotesypaticas.com/pets/{pet.id}",
            box_size=8,
            border=1,
        )
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        qr_b64 = base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass

    # ── Edad humanizada ───────────────────────────────────────────────────
    age_display = ""
    if pet.birth_date:
        try:
            from dateutil.relativedelta import relativedelta
            bd = pet.birth_date if isinstance(pet.birth_date, date) else pet.birth_date.date()
            diff = relativedelta(today, bd)
            parts: list[str] = []
            if diff.years:
                parts.append(f"{diff.years} año{'s' if diff.years != 1 else ''}")
            if diff.months:
                parts.append(f"{diff.months} mes{'es' if diff.months != 1 else ''}")
            age_display = " y ".join(parts) if parts else "< 1 mes"
        except Exception:
            pass

    # ── Contexto mascota (namespace limpio para el template) ──────────────
    class _P:
        pass

    p = _P()
    p.name = pet.name
    p.species = pet.species
    p.breed = pet.breed
    p.birth_date = pet.birth_date
    p.weight_kg = float(pet.weight_kg) if pet.weight_kg else None
    p.food_brand = pet.food_brand
    p.food_freq_days = pet.food_freq_days
    p.age_display = age_display

    # ── Registros de salud ────────────────────────────────────────────────
    class _R:
        pass

    def _rec(hr: object) -> _R:
        r = _R()
        r.name = hr.name  # type: ignore[attr-defined]
        r.applied_at = hr.applied_at  # type: ignore[attr-defined]
        r.record_type = hr.record_type  # type: ignore[attr-defined]
        nd = getattr(hr, "next_due_at", None)
        r.next_due_at = nd
        if nd:
            nd_date = nd.date() if hasattr(nd, "date") else nd
            r.is_due_soon = 0 <= (nd_date - today).days <= 30
        else:
            r.is_due_soon = False
        return r

    all_records = sorted(pet.health_records or [], key=lambda h: str(h.applied_at), reverse=True)
    vaccines = [_rec(h) for h in all_records if h.record_type == "vacuna"]
    dewormings = [_rec(h) for h in all_records if h.record_type == "desparasitacion"]

    # ── Render HTML → PDF ─────────────────────────────────────────────────
    env = _make_jinja_env()
    html_str = env.get_template("carnet_pet.html").render(
        pet=p,
        customer=customer,
        vaccines=vaccines,
        dewormings=dewormings,
        emoji=_SPECIES_EMOJI.get(pet.species.lower(), "🐾"),
        today=today.strftime("%d/%m/%Y"),
        logo_b64=logo_b64,
        photo_b64=photo_b64,
        qr_b64=qr_b64,
    )

    # base_url permite que las rutas relativas fonts/ y assets/ funcionen
    pdf_bytes = HTML(string=html_str, base_url=str(_TEMPLATES_DIR)).write_pdf()

    safe_name = pet.name.lower().replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="carnet-{safe_name}.pdf"',
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )
