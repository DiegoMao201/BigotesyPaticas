"""Parser de facturas electrónicas UBL/XML DIAN (Colombia).

Acepta archivo .xml plano (Invoice) o AttachedDocument con CDATA.
Devuelve estructura normalizada lista para revisión + auto-match con productos
internos via memoria SupplierSkuMap + fuzzy match.
"""
from __future__ import annotations

import re
import unicodedata
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime
from difflib import SequenceMatcher
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select

from app.deps import CurrentUser, DBSession, require_permission
from app.models.catalog import Product
from app.models.purchasing import Supplier, SupplierSkuMap

router = APIRouter(prefix="/purchases/xml", tags=["purchases-xml"])

NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}


# ─── Schemas ────────────────────────────────────────────────────────

class ParsedItem(BaseModel):
    sku_proveedor: str
    descripcion: str
    cantidad: float
    costo_base_unitario: float
    iva_pct: float
    descuento: float = 0
    total_linea: float
    # Match suggestion
    suggested_product_id: str | None = None
    suggested_product_name: str | None = None
    suggested_product_sku: str | None = None
    match_reason: str | None = None  # "memoria_proveedor", "sku_exacto", "nombre_exacto", "fuzzy_85"
    match_score: float = 0


class ParsedInvoice(BaseModel):
    proveedor_nombre: str
    proveedor_nit: str
    proveedor_email: str | None = None
    folio: str
    fecha_emision: str | None = None
    total: float
    moneda: str = "COP"
    # Si encontramos el supplier en BD, devolvemos su id
    supplier_id: str | None = None
    items: list[ParsedItem]


# ─── Helpers ────────────────────────────────────────────────────────

def _txt(node, default=""):
    return node.text.strip() if node is not None and node.text else default


def _f(s, default=0.0):
    try:
        return float(s)
    except (TypeError, ValueError):
        return default


def _normalize(s: str) -> str:
    """Normaliza nombre para fuzzy match: lowercase, sin acentos, sin puntuación."""
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(sorted(s.split()))


def _extract_invoice_root(content: bytes) -> ET.Element:
    """Detecta si es Invoice plano o AttachedDocument y devuelve el Invoice root."""
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise HTTPException(400, f"XML inválido: {e}")

    if root.tag.endswith("AttachedDocument"):
        # Buscar el CDATA con el Invoice anidado
        desc = root.find(".//cac:Attachment/cac:ExternalReference/cbc:Description", NS)
        if desc is None or not desc.text:
            raise HTTPException(400, "AttachedDocument sin Invoice anidado")
        try:
            inner = ET.fromstring(desc.text.encode())
            return inner
        except ET.ParseError as e:
            raise HTTPException(400, f"Invoice anidado inválido: {e}")
    return root


def _parse_supplier(root: ET.Element) -> tuple[str, str, str | None]:
    party = root.find(".//cac:AccountingSupplierParty/cac:Party", NS)
    if party is None:
        return "Desconocido", "", None
    nombre = _txt(party.find(".//cac:PartyTaxScheme/cbc:RegistrationName", NS))
    if not nombre:
        nombre = _txt(party.find(".//cac:PartyName/cbc:Name", NS), "Desconocido")
    nit = _txt(party.find(".//cac:PartyTaxScheme/cbc:CompanyID", NS))
    if not nit:
        nit = _txt(party.find(".//cac:PartyIdentification/cbc:ID", NS))
    email = _txt(root.find(".//cac:AccountingSupplierParty//cbc:ElectronicMail", NS)) or None
    return nombre, nit, email


def _resolver_costo_unitario(qty, price_amount, base_qty, line_extension, discount_amount):
    """Reconcilia costo unitario cuando PriceAmount no es claro.

    Lógica portada de Streamlit Compras.py.
    """
    qty = max(_f(qty), 1e-9)
    base_qty = max(_f(base_qty, 1), 1e-9)
    pa = _f(price_amount)
    le = _f(line_extension)
    disc = _f(discount_amount)
    # PriceAmount es por base_qty unidades
    if pa > 0 and base_qty > 0:
        return pa / base_qty
    # Fallback: line_extension / qty
    if le > 0 and qty > 0:
        return (le + disc) / qty
    return 0.0


def _parse_items(root: ET.Element) -> list[dict]:
    items: list[dict] = []
    for line in root.findall(".//cac:InvoiceLine", NS):
        qty_node = line.find("cbc:InvoicedQuantity", NS)
        qty = _f(_txt(qty_node, "0"))
        if qty <= 0:
            continue

        price_node = line.find(".//cac:Price/cbc:PriceAmount", NS)
        base_qty_node = line.find(".//cac:Price/cbc:BaseQuantity", NS)
        line_ext = _f(_txt(line.find("cbc:LineExtensionAmount", NS)))

        # SKU: StandardItem > SellersItem > LineID
        sku_prov = (
            _txt(line.find(".//cac:StandardItemIdentification/cbc:ID", NS))
            or _txt(line.find(".//cac:SellersItemIdentification/cbc:ID", NS))
            or _txt(line.find("cbc:ID", NS))
        )

        desc = _txt(line.find("cac:Item/cbc:Description", NS))
        if not desc:
            desc = _txt(line.find("cac:Item/cbc:Name", NS), "Sin descripción")

        # IVA
        iva_pct = _f(_txt(line.find(".//cac:TaxCategory/cbc:Percent", NS)))

        # Allowance/Charge: ChargeIndicator=false → descuento
        descuento_total = 0.0
        for ac in line.findall("cac:AllowanceCharge", NS):
            ind = _txt(ac.find("cbc:ChargeIndicator", NS), "false").lower()
            amt = _f(_txt(ac.find("cbc:Amount", NS)))
            if ind == "false":
                descuento_total += amt

        costo_unit = _resolver_costo_unitario(
            qty,
            _txt(price_node, "0"),
            _txt(base_qty_node, "1"),
            line_ext,
            descuento_total,
        )

        items.append({
            "sku_proveedor": sku_prov,
            "descripcion": desc,
            "cantidad": qty,
            "costo_base_unitario": round(costo_unit, 2),
            "iva_pct": iva_pct,
            "descuento": round(descuento_total, 2),
            "total_linea": round(line_ext, 2),
        })
    return items


def _score_match(s1: str, s2: str) -> float:
    """Similitud combinada: SequenceMatcher + Jaccard de tokens."""
    n1, n2 = _normalize(s1), _normalize(s2)
    if not n1 or not n2:
        return 0.0
    seq = SequenceMatcher(None, n1, n2).ratio()
    t1, t2 = set(n1.split()), set(n2.split())
    jac = len(t1 & t2) / max(1, len(t1 | t2))
    return 0.6 * seq + 0.4 * jac


async def _suggest_match(
    db, item: dict, supplier_id_db: uuid.UUID | None, productos: list[Product]
) -> dict:
    """Devuelve {suggested_*, match_reason, match_score} para un ítem parseado."""
    sku_prov = (item.get("sku_proveedor") or "").strip()
    desc = item.get("descripcion") or ""

    # 1) Memoria proveedor
    if supplier_id_db and sku_prov:
        row = (await db.execute(
            select(SupplierSkuMap, Product)
            .join(Product, Product.id == SupplierSkuMap.product_id)
            .where(SupplierSkuMap.supplier_id == supplier_id_db, SupplierSkuMap.sku_proveedor == sku_prov)
        )).first()
        if row:
            mp, prod = row
            return {
                "suggested_product_id": str(prod.id),
                "suggested_product_name": prod.name,
                "suggested_product_sku": prod.sku,
                "match_reason": "memoria_proveedor",
                "match_score": 1.0,
            }

    # 2) SKU exacto contra catálogo (sku interno = sku proveedor)
    if sku_prov:
        for p in productos:
            if (p.sku or "").strip().lower() == sku_prov.lower():
                return {
                    "suggested_product_id": str(p.id),
                    "suggested_product_name": p.name,
                    "suggested_product_sku": p.sku,
                    "match_reason": "sku_exacto",
                    "match_score": 0.99,
                }

    # 3) Nombre exacto normalizado
    desc_n = _normalize(desc)
    if desc_n:
        for p in productos:
            if _normalize(p.name) == desc_n:
                return {
                    "suggested_product_id": str(p.id),
                    "suggested_product_name": p.name,
                    "suggested_product_sku": p.sku,
                    "match_reason": "nombre_exacto",
                    "match_score": 0.95,
                }

    # 4) Fuzzy match (umbral 0.62)
    best = (None, 0.0)
    for p in productos:
        sc = _score_match(desc, p.name)
        if sc > best[1]:
            best = (p, sc)
    if best[0] and best[1] >= 0.62:
        return {
            "suggested_product_id": str(best[0].id),
            "suggested_product_name": best[0].name,
            "suggested_product_sku": best[0].sku,
            "match_reason": f"fuzzy_{int(best[1] * 100)}",
            "match_score": round(best[1], 2),
        }

    return {
        "suggested_product_id": None,
        "suggested_product_name": None,
        "suggested_product_sku": None,
        "match_reason": None,
        "match_score": 0,
    }


# ─── Endpoints ──────────────────────────────────────────────────────

@router.post(
    "/parse",
    response_model=ParsedInvoice,
    dependencies=[Depends(require_permission("purchasing:write"))],
)
async def parse_invoice_xml(
    db: DBSession,
    user: CurrentUser,
    file: UploadFile = File(...),
):
    """Parsea factura XML DIAN y devuelve datos + sugerencias de match.

    NO persiste nada — solo devuelve la data normalizada para que el frontend
    la muestre en una grilla editable y el usuario la valide antes de POST /purchases.
    """
    content = await file.read()
    if not content:
        raise HTTPException(400, "Archivo vacío")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Archivo > 10MB")

    invoice = _extract_invoice_root(content)

    proveedor, nit, email = _parse_supplier(invoice)
    folio = _txt(invoice.find("cbc:ID", NS), "SIN-FOLIO")
    fecha = _txt(invoice.find("cbc:IssueDate", NS)) or None
    total = _f(_txt(invoice.find(".//cac:LegalMonetaryTotal/cbc:PayableAmount", NS)))

    # Buscar supplier en BD por NIT
    supplier_id_db: uuid.UUID | None = None
    if nit:
        s = (await db.execute(select(Supplier).where(Supplier.nit == nit))).scalar_one_or_none()
        if s is not None:
            supplier_id_db = s.id

    # Cargar catálogo (limit razonable; en escala futura, optimizar)
    productos = (await db.execute(select(Product).where(Product.is_active == True))).scalars().all()  # noqa: E712

    raw_items = _parse_items(invoice)
    items_out: list[ParsedItem] = []
    for it in raw_items:
        match = await _suggest_match(db, it, supplier_id_db, productos)
        items_out.append(ParsedItem(**it, **match))

    return ParsedInvoice(
        proveedor_nombre=proveedor,
        proveedor_nit=nit,
        proveedor_email=email,
        folio=folio,
        fecha_emision=fecha,
        total=total,
        supplier_id=str(supplier_id_db) if supplier_id_db else None,
        items=items_out,
    )
