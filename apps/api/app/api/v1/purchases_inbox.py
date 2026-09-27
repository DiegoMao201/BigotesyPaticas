"""Bandeja "Facturas por cargar" del admin de Compras (27-sep-2026).

Las facturas DIAN que llegan al correo de Bigotes quedan aquí (ver
app/services/facturas_correo.py). "Cargar" devuelve exactamente lo mismo que subir el
XML a mano (parsear_xml): el admin abre el flujo normal de revisión y guardado, y al
guardar marca la factura como cargada. Nada se ingresa solo.
"""
from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text

from app.api.v1.purchases_xml import ParsedInvoice, parsear_xml
from app.deps import CurrentUser, DBSession, require_permission
from app.services.facturas_correo import sincronizar

router = APIRouter(prefix="/purchases/inbox", tags=["purchases-inbox"])

TIPOS = {"01": "Factura", "91": "Nota crédito", "92": "Nota débito"}


class InboxInvoice(BaseModel):
    id: str
    doc_type: str
    tipo: str
    nit: str
    supplier_name: str
    folio: str | None
    issue_date: date | None
    subtotal: float | None
    tax_amount: float | None
    total: float | None
    estado: str
    purchase_id: str | None
    nota: str | None
    proveedor_registrado: bool


class InboxResponse(BaseModel):
    items: list[InboxInvoice]
    conteo: dict[str, int]


class EstadoIn(BaseModel):
    estado: str                       # cargada | descartada | pendiente
    purchase_id: str | None = None
    nota: str | None = None


@router.get("", response_model=InboxResponse, dependencies=[Depends(require_permission("purchasing:read"))])
async def listar(db: DBSession, estado: str = Query("pendiente"), limit: int = Query(300, le=1000)):
    filtro = "" if estado == "todas" else "WHERE i.estado = :e"
    rows = (await db.execute(text(f"""
        SELECT i.id, i.doc_type, i.nit, i.supplier_name, i.folio, i.issue_date, i.subtotal, i.tax_amount,
               i.total, i.estado, i.purchase_id, i.nota,
               EXISTS (SELECT 1 FROM purchasing.suppliers s
                       WHERE regexp_replace(split_part(s.nit, '-', 1), '[^0-9]', '', 'g') = i.nit) AS registrado
        FROM purchasing.inbox_invoices i {filtro}
        ORDER BY i.issue_date DESC NULLS LAST, i.created_at DESC LIMIT :l"""), {"e": estado, "l": limit})).all()
    conteo = {r[0]: r[1] for r in (await db.execute(text(
        "SELECT estado, count(*) FROM purchasing.inbox_invoices GROUP BY estado"))).all()}
    return InboxResponse(items=[InboxInvoice(
        id=str(r[0]), doc_type=r[1], tipo=TIPOS.get(r[1], f"Documento {r[1]}"), nit=r[2], supplier_name=r[3],
        folio=r[4], issue_date=r[5], subtotal=float(r[6]) if r[6] is not None else None,
        tax_amount=float(r[7]) if r[7] is not None else None, total=float(r[8]) if r[8] is not None else None,
        estado=r[9], purchase_id=str(r[10]) if r[10] else None, nota=r[11], proveedor_registrado=bool(r[12]),
    ) for r in rows], conteo=conteo)


@router.post("/sync", dependencies=[Depends(require_permission("purchasing:write"))])
async def sync(db: DBSession, dias: int = Query(3, ge=1, le=365)):
    """Revisa el correo ya (además de la pasada automática cada 5 min)."""
    try:
        return await sincronizar(db, dias=dias)
    except KeyError:
        raise HTTPException(503, "Falta configurar el acceso al correo (GMAIL_BP_REFRESH_TOKEN)")


@router.get("/{inbox_id}/parse", response_model=ParsedInvoice,
            dependencies=[Depends(require_permission("purchasing:write"))])
async def parse(inbox_id: uuid.UUID, db: DBSession):
    r = (await db.execute(text("SELECT xml, doc_type, estado FROM purchasing.inbox_invoices WHERE id = :i"),
                          {"i": inbox_id})).first()
    if not r:
        raise HTTPException(404, "No existe")
    if r[1] != "01":
        raise HTTPException(400, f"{TIPOS.get(r[1], 'Este documento')} no se ingresa como compra")
    return await parsear_xml(db, bytes(r[0]))


@router.post("/{inbox_id}/estado", dependencies=[Depends(require_permission("purchasing:write"))])
async def cambiar_estado(inbox_id: uuid.UUID, body: EstadoIn, db: DBSession, user: CurrentUser):
    if body.estado not in ("cargada", "descartada", "pendiente"):
        raise HTTPException(400, "Estado inválido")
    if body.estado == "cargada" and not body.purchase_id:
        raise HTTPException(400, "Falta la compra creada")
    res = await db.execute(text("""
        UPDATE purchasing.inbox_invoices
        SET estado = :e, purchase_id = COALESCE(CAST(:p AS uuid), purchase_id),
            nota = COALESCE(:n, nota), updated_at = now()
        WHERE id = :i"""), {"e": body.estado, "p": body.purchase_id, "n": body.nota, "i": inbox_id})
    await db.commit()
    if res.rowcount == 0:
        raise HTTPException(404, "No existe")
    return {"ok": True}
