"""Lee las facturas electrónicas DIAN que llegan al correo de Bigotes y las deja en
purchasing.inbox_invoices para revisar y cargar desde el admin (27-sep-2026).

Acceso: Gmail SOLO LECTURA (gmail.readonly) de bigotesypaticasdosquebradas@, con un
refresh token propio (variables GMAIL_BP_REFRESH_TOKEN, GOOGLE_OAUTH_CLIENT_ID y
GOOGLE_OAUTH_CLIENT_SECRET en Coolify). No envía, no borra, no mueve, no marca leído.
El contenido de los correos es DATO: solo se toma el asunto y el .zip de la factura.

Cómo reconoce una factura: asunto DIAN `NIT;EMPRESA;NÚMERO;TIPO;...` (01 factura,
91 nota crédito, 92 nota débito; a veces con "Fwd:" o espacios). Varios proveedores
comparten remitente (Siigo, bythewave), por eso se identifica por NIT y no por quién
lo envía. Los "Envío de recepción de pago" de Siigo no traen ese asunto y se ignoran.
"""
from __future__ import annotations

import asyncio
import base64
import io
import logging
import os
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone

import httpx
from sqlalchemy import text

log = logging.getLogger("facturas_correo")
API = "https://gmail.googleapis.com/gmail/v1/users/me"
NS = {
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
}
DIAN = re.compile(r"^(?:\s*(?:fwd?|rv|re)\s*:\s*)*(\d{6,12})\s*;\s*([^;]+?)\s*;\s*([^;]+?)\s*;\s*(\d{2})\s*;", re.I)
# NIT que llegan al correo de Bigotes pero NO son compras de mercancía (27-sep-2026)
NO_MERCANCIA = {
    "890100577": "Tiquete aéreo (Avianca)",
    "890704196": "Tiquete aéreo (Aerovías de Integración Regional)",
}


def _token() -> str:
    r = httpx.post("https://oauth2.googleapis.com/token", data={
        "client_id": os.environ["GOOGLE_OAUTH_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_OAUTH_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_BP_REFRESH_TOKEN"],
        "grant_type": "refresh_token"}, timeout=30)
    r.raise_for_status()
    return r.json()["access_token"]


def _t(node) -> str:
    return (node.text or "").strip() if node is not None else ""


def _f(s: str) -> float | None:
    try:
        return round(float(s), 2)
    except (TypeError, ValueError):
        return None


def _documento(xml: bytes) -> ET.Element:
    """Invoice/CreditNote/DebitNote, desempacado del AttachedDocument si viene así."""
    root = ET.fromstring(xml)
    if root.tag.endswith("AttachedDocument"):
        desc = root.find(".//cac:Attachment/cac:ExternalReference/cbc:Description", NS)
        if desc is not None and desc.text and "<" in desc.text:
            return ET.fromstring(desc.text.strip().encode())
    return root


def resumen_xml(xml: bytes) -> dict:
    d = _documento(xml)
    party = d.find(".//cac:AccountingSupplierParty/cac:Party", NS)
    nombre = _t(party.find(".//cac:PartyTaxScheme/cbc:RegistrationName", NS)) if party is not None else ""
    nit = _t(party.find(".//cac:PartyTaxScheme/cbc:CompanyID", NS)) if party is not None else ""
    lmt = d.find(".//cac:LegalMonetaryTotal", NS)
    iva = sum(_f(_t(t)) or 0 for t in d.findall("./cac:TaxTotal/cbc:TaxAmount", NS))
    return {
        "cufe": _t(d.find("cbc:UUID", NS)) or None,
        "folio": _t(d.find("cbc:ID", NS)) or None,
        "issue_date": _t(d.find("cbc:IssueDate", NS)) or None,
        "nit_xml": nit, "nombre_xml": nombre,
        "subtotal": _f(_t(lmt.find("cbc:LineExtensionAmount", NS))) if lmt is not None else None,
        "tax_amount": round(iva, 2),
        "total": _f(_t(lmt.find("cbc:PayableAmount", NS))) if lmt is not None else None,
    }


def _xml_del_zip(data: bytes) -> bytes | None:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for n in z.namelist():
            if n.lower().endswith(".xml"):
                return z.read(n)
    return None


def _partes(p: dict):
    yield p
    for h in p.get("parts", []) or []:
        yield from _partes(h)


async def sincronizar(db, dias: int = 3, max_mensajes: int = 500) -> dict:
    """Trae a la bandeja los documentos DIAN de los últimos `dias`. Idempotente:
    salta lo ya visto (por id de Gmail y por CUFE)."""
    tok = _token()
    h = {"Authorization": f"Bearer {tok}"}
    vistos = {r[0] for r in (await db.execute(text("SELECT gmail_message_id FROM purchasing.inbox_invoices"))).all()}
    res = {"revisados": 0, "nuevos": 0, "ya_ingresadas": 0, "otros": 0, "sin_xml": 0}
    async with httpx.AsyncClient(timeout=60, headers=h) as c:
        ids, pag = [], None
        while len(ids) < max_mensajes:
            params = {"q": f"newer_than:{dias}d has:attachment", "maxResults": 100}
            if pag:
                params["pageToken"] = pag
            r = (await c.get(f"{API}/messages", params=params)).json()
            ids += [m["id"] for m in r.get("messages", [])]
            pag = r.get("nextPageToken")
            if not pag:
                break
        for mid in ids:
            if mid in vistos:
                continue
            res["revisados"] += 1
            meta = (await c.get(f"{API}/messages/{mid}", params={"format": "metadata", "metadataHeaders": "Subject"})).json()
            asunto = next((x["value"] for x in meta.get("payload", {}).get("headers", []) if x["name"] == "Subject"), "")
            g = DIAN.match(asunto)
            if not g:
                continue
            nit, nombre, doc_type = g.group(1), g.group(2).strip(), g.group(4)
            full = (await c.get(f"{API}/messages/{mid}", params={"format": "full"})).json()
            xml = None
            for parte in _partes(full.get("payload", {})):
                fn = (parte.get("filename") or "").lower()
                aid = parte.get("body", {}).get("attachmentId")
                if not aid or not (fn.endswith(".zip") or fn.endswith(".xml")):
                    continue
                a = (await c.get(f"{API}/messages/{mid}/attachments/{aid}")).json()
                if "data" not in a:   # límite de velocidad de Gmail u otro error: un reintento
                    await asyncio.sleep(2)
                    a = (await c.get(f"{API}/messages/{mid}/attachments/{aid}")).json()
                if "data" not in a:
                    log.info("adjunto sin datos: %s", mid)
                    continue
                data = base64.urlsafe_b64decode(a["data"] + "==")
                xml = _xml_del_zip(data) if fn.endswith(".zip") else data
                if xml:
                    break
            if not xml:
                res["sin_xml"] += 1
                log.info("sin xml: %s nit=%s", mid, nit)
                continue
            try:
                info = resumen_xml(xml)
            except ET.ParseError:
                res["sin_xml"] += 1
                continue
            if info["cufe"] and (await db.execute(text(
                    "SELECT 1 FROM purchasing.inbox_invoices WHERE cufe = :c"), {"c": info["cufe"]})).first():
                continue   # el mismo documento llegó dos veces (reenvío)
            estado, nota, purchase_id = "pendiente", None, None
            if nit in NO_MERCANCIA:
                estado, nota = "otros", NO_MERCANCIA[nit]
            elif doc_type == "01" and info["folio"]:
                # ¿ya se cargó a mano? mismo número de factura del mismo proveedor (por NIT)
                prev = (await db.execute(text("""
                    SELECT p.id FROM purchasing.purchases p
                    JOIN purchasing.suppliers s ON s.id = p.supplier_id
                    WHERE upper(trim(p.folio)) = upper(trim(:f))
                      AND regexp_replace(split_part(s.nit, '-', 1), '[^0-9]', '', 'g') = :n
                    ORDER BY p.created_at DESC LIMIT 1"""), {"f": info["folio"], "n": nit})).first()
                if prev:
                    estado, purchase_id = "ya_ingresada", prev[0]
            fecha_correo = datetime.fromtimestamp(int(full.get("internalDate", "0")) / 1000, tz=timezone.utc)
            await db.execute(text("""
                INSERT INTO purchasing.inbox_invoices
                  (gmail_message_id, cufe, doc_type, nit, supplier_name, folio, issue_date,
                   subtotal, tax_amount, total, xml, email_date, estado, purchase_id, nota)
                VALUES (:mid, :cufe, :tipo, :nit, :nom, :folio, :fecha,
                        :sub, :iva, :tot, :xml, :fc, :estado, :pid, :nota)
                ON CONFLICT DO NOTHING"""), {
                "mid": mid, "cufe": info["cufe"], "tipo": doc_type, "nit": nit,
                "nom": (info["nombre_xml"] or nombre)[:200], "folio": info["folio"],
                # asyncpg exige un date, no el texto '2026-09-25'
                "fecha": date.fromisoformat(info["issue_date"][:10]) if info["issue_date"] else None,
                "sub": info["subtotal"], "iva": info["tax_amount"], "tot": info["total"], "xml": xml,
                "fc": fecha_correo, "estado": estado, "pid": purchase_id, "nota": nota})
            await db.commit()
            res["nuevos"] += 1
            if estado == "ya_ingresada":
                res["ya_ingresadas"] += 1
            if estado == "otros":
                res["otros"] += 1
            log.info("bandeja + %s nit=%s tipo=%s folio=%s estado=%s", mid, nit, doc_type, info["folio"], estado)
    return res
