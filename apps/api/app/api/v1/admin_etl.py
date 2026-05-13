"""
Admin ETL — migración Google Sheets → PostgreSQL.
Endpoint protegido, sólo superadmin.
Corre dentro del contenedor API donde tiene acceso a la DB interna de Coolify.

Variables de entorno requeridas (ya están en el contenedor):
  GOOGLE_SERVICE_ACCOUNT_JSON  — JSON completo de la service account (string)
  DATABASE_URL_SYNC             — postgresql+psycopg://user:pass@host:5432/db
  GOOGLE_SHEET_ID               — ID del Sheet (default = producción)
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.deps import require_superadmin

router = APIRouter(prefix="/admin/etl", tags=["admin-etl"])

DEFAULT_SHEET_ID = "12ay8_vug1yYXoGhHCIjKy1_NL5oqz6QBQ537283iGEo"


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class ETLRequest(BaseModel):
    sheet_id: str = DEFAULT_SHEET_ID
    tabs: list[str] | None = None  # None = todas; o lista: ["Inventario","Clientes"]


class TabReport(BaseModel):
    rows_read: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_rejected: int = 0
    sample_errors: list[str] = []


class ETLResponse(BaseModel):
    started_at: str
    completed_at: str
    duration_seconds: float
    reports: dict[str, TabReport]
    global_errors: list[str] = []


# ── Helpers ──────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "_", s.lower().strip()).strip("_")


def _money(val: Any) -> float:
    if val is None or str(val).strip() in ("", "-", "N/A", "n/a", "#N/A"):
        return 0.0
    cleaned = re.sub(r"[^\d\.]", "", str(val).replace(",", ""))
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _int_val(val: Any) -> int:
    try:
        return max(0, int(float(str(val).replace(",", "").strip())))
    except (ValueError, TypeError):
        return 0


def _slug(name: str) -> str:
    n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", n.lower().strip()).strip("-") or "producto"


def _parse_dt(val: Any) -> datetime | None:
    if not val or str(val).strip() in ("", "-", "N/A"):
        return None
    raw = str(val).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y", "%d/%m/%Y %H:%M:%S"):
        try:
            return datetime.strptime(raw[: len(fmt)], fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _now() -> datetime:
    return datetime.now(UTC)


# ── Sync ETL (se ejecuta en thread separado) ─────────────────────────────────

def _run_etl_sync(sheet_id: str, creds_json_str: str, tabs_filter: list[str] | None) -> dict[str, Any]:
    import base64 as _b64
    import gspread
    import psycopg
    from google.oauth2.service_account import Credentials

    # GOOGLE_SA_B64 tiene prioridad: base64 evita todos los problemas de escaping de Coolify.
    sa_b64 = os.environ.get("GOOGLE_SA_B64", "").strip()
    if sa_b64:
        sa_info = json.loads(_b64.b64decode(sa_b64).decode("utf-8"))
    else:
        # Fallback: limpiar el JSON crudo que Coolify puede haber escapado
        raw = creds_json_str.strip()
        if raw.startswith("'") and raw.endswith("'"):
            raw = raw[1:-1]
        raw = raw.replace('\\"', '"')
        # Si no empieza con '{', puede ser base64 (usuario pegó el b64 en GOOGLE_SERVICE_ACCOUNT_JSON)
        if not raw.startswith('{'):
            try:
                raw = _b64.b64decode(raw).decode("utf-8")
            except Exception:
                pass  # si no es base64 válido, dejar como está y que json.loads falle con mensaje claro
        sa_info = json.loads(raw)
        # Coolify double-escapa \n en private_key → convertir a newlines reales
        pk = sa_info.get("private_key", "")
        if pk and "\n" not in pk and "\\n" in pk:
            sa_info["private_key"] = pk.replace("\\n", "\n")
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    gc_creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    gc = gspread.authorize(gc_creds)
    sh = gc.open_by_key(sheet_id)

    def get_rows(tab_name: str) -> list[dict]:
        try:
            ws = sh.worksheet(tab_name)
            records = ws.get_all_records(empty2zero=False, head=1, default_blank="")
            # Filtrar filas completamente vacías
            return [r for r in records if any(str(v).strip() for v in list(r.values())[:4])]
        except Exception as exc:
            return []

    # DB connection: psycopg (sync, v3)
    raw_url = os.environ.get("DATABASE_URL_SYNC", "")
    conn_str = (
        raw_url
        .replace("postgresql+psycopg://", "postgresql://")
        .replace("postgresql+asyncpg://", "postgresql://")
    )

    reports: dict[str, dict] = {}
    global_errors: list[str] = []

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:

            # ── 1. CATEGORÍAS ────────────────────────────────────────────
            if not tabs_filter or "Inventario" in tabs_filter:
                rep: dict[str, Any] = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    inv_rows = get_rows("Inventario")
                    cats = sorted({
                        str(r.get("Categoria", "") or "").strip()
                        for r in inv_rows
                        if str(r.get("Categoria", "") or "").strip() not in ("", "-", "N/A")
                    })
                    rep["rows_read"] = len(cats)
                    for cat_name in cats:
                        cat_slug = _slug(cat_name)
                        cur.execute("SELECT id FROM catalog.categories WHERE slug = %s", (cat_slug,))
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                        else:
                            cur.execute(
                                """INSERT INTO catalog.categories
                                   (id, name, slug, is_active, sort_order, created_at, updated_at)
                                   VALUES (%s,%s,%s,true,0,%s,%s)""",
                                (str(uuid.uuid4()), cat_name, cat_slug, _now(), _now()),
                            )
                            rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"categorias: {exc}")
                reports["categorias"] = rep

            # ── 2. PRODUCTOS ──────────────────────────────────────────────
            if not tabs_filter or "Inventario" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    inv_rows = get_rows("Inventario")
                    rep["rows_read"] = len(inv_rows)
                    for r in inv_rows:
                        # SKU: Producto_UID (hash del sistema viejo) o ID_Producto_Norm
                        sku = str(r.get("Producto_UID") or r.get("ID_Producto_Norm") or r.get("ID_Producto") or "").strip()
                        name = str(r.get("Nombre") or "").strip()
                        if not sku or not name:
                            rep["rows_rejected"] += 1
                            if len(rep["sample_errors"]) < 5:
                                rep["sample_errors"].append(f"Sin sku/nombre: {r}")
                            continue

                        price = _money(r.get("Precio"))
                        cost = _money(r.get("Costo"))
                        iva = _money(r.get("Iva"))
                        cat_name = str(r.get("Categoria") or "").strip()
                        cat_slug = _slug(cat_name) if cat_name else None

                        # Buscar category_id
                        cat_id = None
                        if cat_slug:
                            cur.execute("SELECT id FROM catalog.categories WHERE slug = %s", (cat_slug,))
                            crow = cur.fetchone()
                            if crow:
                                cat_id = crow[0]

                        # Margin: clamp a rango válido NUMERIC(5,4) = [-9.9999, 9.9999]
                        margin_raw = round((price - cost) / price, 4) if price > 0 else 0.20
                        margin = max(-9.9999, min(9.9999, margin_raw))

                        cur.execute("SELECT id FROM catalog.products WHERE sku = %s", (sku,))
                        existing = cur.fetchone()
                        try:
                            cur.execute("SAVEPOINT sp_product")
                            if existing:
                                cur.execute(
                                    """UPDATE catalog.products
                                       SET name=%s, price=%s, cost=%s, margin_pct=%s,
                                           category_id=%s, is_active=true, is_published=true,
                                           attributes=%s, updated_at=%s
                                       WHERE sku=%s""",
                                    (name, price, cost, margin, cat_id,
                                     json.dumps({"iva": iva}), _now(), sku),
                                )
                                rep["rows_updated"] += 1
                            else:
                                # Slug único
                                base_slug = _slug(name)
                                slug = base_slug
                                suffix = 0
                                while True:
                                    cur.execute("SELECT id FROM catalog.products WHERE slug = %s", (slug,))
                                    if not cur.fetchone():
                                        break
                                    suffix += 1
                                    slug = f"{base_slug}-{suffix}"

                                cur.execute(
                                    """INSERT INTO catalog.products
                                       (id, sku, slug, name, price, cost, margin_pct, category_id,
                                        is_active, is_published, attributes, tags, images,
                                        created_at, updated_at)
                                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
                                               true,true,%s,'[]','[]',%s,%s)""",
                                    (str(uuid.uuid4()), sku, slug, name, price, cost, margin, cat_id,
                                     json.dumps({"iva": iva}), _now(), _now()),
                                )
                                rep["rows_inserted"] += 1
                            cur.execute("RELEASE SAVEPOINT sp_product")
                        except Exception as row_exc:
                            cur.execute("ROLLBACK TO SAVEPOINT sp_product")
                            rep["rows_rejected"] += 1
                            if len(rep["sample_errors"]) < 5:
                                rep["sample_errors"].append(f"sku={sku}: {row_exc}")
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"productos: {exc}")
                reports["productos"] = rep

            # ── 3. STOCK ─────────────────────────────────────────────────
            if not tabs_filter or "Inventario" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    # Obtener o crear ubicación por defecto
                    cur.execute("SELECT id FROM inventory.stock_locations WHERE is_default = 1 LIMIT 1")
                    loc_row = cur.fetchone()
                    if not loc_row:
                        loc_id = str(uuid.uuid4())
                        cur.execute(
                            """INSERT INTO inventory.stock_locations
                               (id, code, name, is_default, created_at, updated_at)
                               VALUES (%s,'MAIN','Tienda Principal',1,%s,%s)""",
                            (loc_id, _now(), _now()),
                        )
                        conn.commit()
                    else:
                        loc_id = str(loc_row[0])

                    inv_rows = get_rows("Inventario")
                    rep["rows_read"] = len(inv_rows)
                    for r in inv_rows:
                        sku = str(r.get("Producto_UID") or r.get("ID_Producto_Norm") or r.get("ID_Producto") or "").strip()
                        qty = _int_val(r.get("Stock") or 0)
                        if not sku:
                            rep["rows_rejected"] += 1
                            continue
                        cur.execute("SELECT id FROM catalog.products WHERE sku = %s", (sku,))
                        prod_row = cur.fetchone()
                        if not prod_row:
                            rep["rows_skipped"] += 1
                            continue
                        prod_id = str(prod_row[0])
                        cur.execute(
                            "SELECT id FROM inventory.stock WHERE product_id = %s AND location_id = %s",
                            (prod_id, loc_id),
                        )
                        stock_row = cur.fetchone()
                        if stock_row:
                            cur.execute(
                                "UPDATE inventory.stock SET quantity=%s, updated_at=%s WHERE id=%s",
                                (qty, _now(), str(stock_row[0])),
                            )
                            rep["rows_updated"] += 1
                        else:
                            cur.execute(
                                """INSERT INTO inventory.stock
                                   (id, product_id, location_id, quantity, reserved, reorder_point, created_at, updated_at)
                                   VALUES (%s,%s,%s,%s,0,0,%s,%s)""",
                                (str(uuid.uuid4()), prod_id, loc_id, qty, _now(), _now()),
                            )
                            rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"stock: {exc}")
                reports["stock"] = rep

            # ── 4. CLIENTES ───────────────────────────────────────────────
            if not tabs_filter or "Clientes" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    cli_rows = get_rows("Clientes")
                    rep["rows_read"] = len(cli_rows)
                    for r in cli_rows:
                        name = str(r.get("Nombre") or "").strip()
                        if not name:
                            rep["rows_rejected"] += 1
                            continue
                        doc = str(r.get("Cedula") or "").strip() or None
                        email_raw = str(r.get("Email") or "").strip()
                        email = email_raw if "@" in email_raw else None
                        phone = str(r.get("Telefono") or "").strip() or None
                        address = str(r.get("Direccion") or "").strip() or None
                        mascota = str(r.get("Mascota") or "").strip() or None
                        tipo_m = str(r.get("Tipo_Mascota") or "").strip() or None
                        cumple = str(r.get("Cumpleaños_mascota") or "").strip() or None
                        registro = _parse_dt(r.get("Registro"))
                        extra: dict = {}
                        if mascota:
                            extra["mascota_nombre"] = mascota
                        if tipo_m:
                            extra["mascota_tipo"] = tipo_m
                        if cumple:
                            extra["mascota_cumple"] = cumple

                        # Dedup: doc → email → nombre+telefono
                        existing_id = None
                        if doc:
                            cur.execute("SELECT id FROM crm.customers WHERE document_id = %s", (doc,))
                            row = cur.fetchone()
                            if row:
                                existing_id = str(row[0])
                        if not existing_id and email:
                            cur.execute("SELECT id FROM crm.customers WHERE email = %s", (email,))
                            row = cur.fetchone()
                            if row:
                                existing_id = str(row[0])

                        ts = registro or _now()
                        if existing_id:
                            cur.execute(
                                """UPDATE crm.customers
                                   SET full_name=%s, phone=%s, address=%s,
                                       extra=%s, updated_at=%s
                                   WHERE id=%s""",
                                (name, phone, address, json.dumps(extra), _now(), existing_id),
                            )
                            rep["rows_updated"] += 1
                        else:
                            cur.execute(
                                """INSERT INTO crm.customers
                                   (id, full_name, document_id, email, phone, address,
                                    extra, created_at, updated_at)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                (str(uuid.uuid4()), name, doc, email, phone, address,
                                 json.dumps(extra), ts, _now()),
                            )
                            rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"clientes: {exc}")
                reports["clientes"] = rep

            # ── 5. VENTAS (historial legacy) ──────────────────────────────
            if not tabs_filter or "Ventas" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    vta_rows = get_rows("Ventas")
                    rep["rows_read"] = len(vta_rows)
                    for r in vta_rows:
                        id_venta = str(r.get("ID_Venta") or "").strip()
                        if not id_venta:
                            rep["rows_rejected"] += 1
                            continue
                        order_num = f"LEG-{id_venta}"
                        cur.execute("SELECT id FROM sales.orders WHERE order_number = %s", (order_num,))
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                            continue

                        fecha = _parse_dt(r.get("Fecha")) or _now()
                        total = _money(r.get("Total"))
                        metodo = str(r.get("Metodo_Pago") or "Efectivo").strip()
                        tipo_entrega = str(r.get("Tipo_Entrega") or "").strip()
                        channel = "POS_LEGACY" if "venta" in tipo_entrega.lower() else "STORE_LEGACY"
                        items_text = str(r.get("Items") or "").strip()
                        cedula = str(r.get("Cedula_Cliente") or "").strip()
                        nombre_cli = str(r.get("Nombre_Cliente") or "").strip()
                        estado_pago = str(r.get("Estado_Pago") or "Pagado").strip() or "Pagado"
                        abono = _money(r.get("Abono_Recibido"))
                        saldo = _money(r.get("Saldo_Pendiente"))
                        paid = abono if abono > 0 else total
                        balance = saldo if saldo > 0 else 0.0

                        # Buscar cliente por cédula
                        customer_id = None
                        if cedula:
                            cur.execute("SELECT id FROM crm.customers WHERE document_id = %s", (cedula,))
                            row = cur.fetchone()
                            if row:
                                customer_id = str(row[0])

                        meta = {
                            "cliente_nombre": nombre_cli,
                            "id_venta_legacy": id_venta,
                            "banco_destino": str(r.get("Banco_Destino") or ""),
                            "estado_envio": str(r.get("Estado_Envio") or ""),
                        }
                        cur.execute(
                            """INSERT INTO sales.orders
                               (id, order_number, channel, status, customer_id,
                                subtotal, discount_total, tax_total, shipping_total, grand_total,
                                paid_amount, balance_due, payment_status, payment_method,
                                occurred_at, notes, metadata, created_at, updated_at)
                               VALUES
                               (%s,%s,%s,'confirmed',%s,
                                %s,0,0,0,%s,
                                %s,%s,%s,%s,
                                %s,%s,%s,%s,%s)""",
                            (
                                str(uuid.uuid4()), order_num, channel, customer_id,
                                total, total,
                                paid, balance,
                                "Pagado" if balance == 0 else "Parcial",
                                metodo,
                                fecha, items_text, json.dumps(meta), fecha, _now(),
                            ),
                        )
                        rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"ventas: {exc}")
                reports["ventas"] = rep

            # ── 6. GASTOS → ops.legacy_id_map (raw store) ────────────────
            if not tabs_filter or "Gastos" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    gasto_rows = get_rows("Gastos")
                    rep["rows_read"] = len(gasto_rows)
                    for r in gasto_rows:
                        legacy_id = str(r.get("ID_Gasto") or "").strip()
                        if not legacy_id:
                            rep["rows_rejected"] += 1
                            continue
                        cur.execute(
                            "SELECT id FROM ops.legacy_id_map WHERE entity='gasto' AND legacy_id=%s",
                            (legacy_id,),
                        )
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                            continue
                        payload = {
                            "fecha": str(r.get("Fecha") or ""),
                            "tipo": str(r.get("Tipo_Gasto") or ""),
                            "categoria": str(r.get("Categoria") or ""),
                            "descripcion": str(r.get("Descripcion") or ""),
                            "monto": _money(r.get("Monto")),
                            "metodo_pago": str(r.get("Metodo_Pago") or ""),
                            "banco": str(r.get("Banco_Origen") or ""),
                        }
                        cur.execute(
                            """INSERT INTO ops.legacy_id_map
                               (id, entity, legacy_id, new_id, extra, created_at, updated_at)
                               VALUES (%s,'gasto',%s,%s,%s,%s,%s)""",
                            (str(uuid.uuid4()), legacy_id, str(uuid.uuid4()),
                             json.dumps(payload), _now(), _now()),
                        )
                        rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"gastos: {exc}")
                reports["gastos"] = rep

            # ── 7. CIERRES → ops.legacy_id_map ───────────────────────────
            if not tabs_filter or "Cierres" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    cierres_rows = get_rows("Cierres")
                    rep["rows_read"] = len(cierres_rows)
                    for r in cierres_rows:
                        fecha = str(r.get("Fecha") or "").strip()
                        hora = str(r.get("Hora") or "").strip()
                        legacy_id = f"{fecha}T{hora}"
                        if not fecha:
                            rep["rows_rejected"] += 1
                            continue
                        cur.execute(
                            "SELECT id FROM ops.legacy_id_map WHERE entity='cierre_caja' AND legacy_id=%s",
                            (legacy_id,),
                        )
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                            continue
                        payload = {
                            "fecha": fecha, "hora": hora,
                            "base_inicial": _money(r.get("Base_Inicial")),
                            "ventas_efectivo": _money(r.get("Ventas_Efectivo")),
                            "ventas_electronico": _money(r.get("ventas_electronico") or r.get("Ventas_Electronico")),
                            "gastos_efectivo": _money(r.get("Gastos_Efectivo")),
                            "dinero_a_bancos": _money(r.get("Dinero_A_Bancos")),
                            "saldo_teorico": _money(r.get("Saldo_Teorico")),
                            "saldo_real": _money(r.get("Saldo_Real")),
                            "diferencia": _money(r.get("Diferencia")),
                            "notas": str(r.get("Notas") or ""),
                        }
                        cur.execute(
                            """INSERT INTO ops.legacy_id_map
                               (id, entity, legacy_id, new_id, extra, created_at, updated_at)
                               VALUES (%s,'cierre_caja',%s,%s,%s,%s,%s)""",
                            (str(uuid.uuid4()), legacy_id, str(uuid.uuid4()),
                             json.dumps(payload), _now(), _now()),
                        )
                        rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"cierres: {exc}")
                reports["cierres"] = rep

            # ── 8. MAESTRO PROVEEDORES → ops.legacy_id_map ───────────────
            if not tabs_filter or "Maestro_Proveedores" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    prov_rows = get_rows("Maestro_Proveedores")
                    rep["rows_read"] = len(prov_rows)
                    for r in prov_rows:
                        sku_prov = str(r.get("SKU_Proveedor") or "").strip()
                        id_prov = str(r.get("ID_Proveedor") or "").strip()
                        legacy_id = f"{id_prov}-{sku_prov}"
                        if not sku_prov and not id_prov:
                            rep["rows_rejected"] += 1
                            continue
                        cur.execute(
                            "SELECT id FROM ops.legacy_id_map WHERE entity='proveedor_sku' AND legacy_id=%s",
                            (legacy_id,),
                        )
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                            continue
                        # Link to product if SKU_Interno exists
                        sku_interno = str(r.get("SKU_Interno") or "").strip()
                        payload = {
                            "id_proveedor": id_prov,
                            "nombre_proveedor": str(r.get("Nombre_Proveedor") or ""),
                            "sku_proveedor": sku_prov,
                            "sku_interno": sku_interno,
                            "factor_pack": _int_val(r.get("Factor_Pack") or 1),
                            "ultima_actualizacion": str(r.get("Ultima_Actualizacion") or ""),
                        }
                        cur.execute(
                            """INSERT INTO ops.legacy_id_map
                               (id, entity, legacy_id, new_id, extra, created_at, updated_at)
                               VALUES (%s,'proveedor_sku',%s,%s,%s,%s,%s)""",
                            (str(uuid.uuid4()), legacy_id, str(uuid.uuid4()),
                             json.dumps(payload), _now(), _now()),
                        )
                        rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"maestro_proveedores: {exc}")
                reports["maestro_proveedores"] = rep

            # ── 9. HISTORIAL ÓRDENES DE COMPRA → ops.legacy_id_map ───────
            if not tabs_filter or "Historial_Ordenes" in tabs_filter:
                rep = dict(rows_read=0, rows_inserted=0, rows_updated=0, rows_skipped=0, rows_rejected=0, sample_errors=[])
                try:
                    ord_rows = get_rows("Historial_Ordenes")
                    rep["rows_read"] = len(ord_rows)
                    for r in ord_rows:
                        id_orden = str(r.get("ID_Orden") or "").strip()
                        if not id_orden:
                            rep["rows_rejected"] += 1
                            continue
                        cur.execute(
                            "SELECT id FROM ops.legacy_id_map WHERE entity='orden_compra' AND legacy_id=%s",
                            (id_orden,),
                        )
                        if cur.fetchone():
                            rep["rows_skipped"] += 1
                            continue
                        payload = {
                            "id_orden": id_orden,
                            "proveedor": str(r.get("Proveedor") or ""),
                            "fecha_orden": str(r.get("Fecha_Orden") or ""),
                            "items_json": str(r.get("Items_JSON") or ""),
                            "total": _money(r.get("Total_Dinero")),
                            "estado": str(r.get("Estado") or ""),
                        }
                        cur.execute(
                            """INSERT INTO ops.legacy_id_map
                               (id, entity, legacy_id, new_id, extra, created_at, updated_at)
                               VALUES (%s,'orden_compra',%s,%s,%s,%s,%s)""",
                            (str(uuid.uuid4()), id_orden, str(uuid.uuid4()),
                             json.dumps(payload), _now(), _now()),
                        )
                        rep["rows_inserted"] += 1
                    conn.commit()
                except Exception as exc:
                    conn.rollback()
                    global_errors.append(f"historial_ordenes: {exc}")
                reports["historial_ordenes"] = rep

    return {"reports": reports, "global_errors": global_errors}


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.get(
    "/debug-env",
    summary="Diagnóstico seguro de la env var del SA",
    description="Solo superadmin. No expone secretos — solo metadatos.",
)
async def debug_env(_current_user=Depends(require_superadmin)):
    raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not raw:
        return {"status": "NOT_SET"}

    preview_start = raw[:8]
    preview_end = raw[-8:]
    length = len(raw)

    # Intentar parsear
    try:
        stripped = raw.strip()
        if stripped.startswith("'") and stripped.endswith("'"):
            stripped = stripped[1:-1]
        stripped = stripped.replace('\\"', '"')
        # Auto-detectar base64
        is_b64 = False
        if not stripped.startswith('{'):
            import base64 as _b64_debug
            try:
                stripped = _b64_debug.b64decode(stripped).decode("utf-8")
                is_b64 = True
            except Exception:
                pass
        sa = json.loads(stripped)
        pk = sa.get("private_key", "")
        pk_first8 = repr(pk[:8])
        has_newlines = "\n" in pk
        has_literal_slash_n = "\\n" in pk
        return {
            "status": "PARSED_OK",
            "raw_length": length,
            "raw_start": repr(preview_start),
            "raw_end": repr(preview_end),
            "was_base64": is_b64,
            "private_key_first8": pk_first8,
            "private_key_has_real_newlines": has_newlines,
            "private_key_has_literal_slash_n": has_literal_slash_n,
            "client_email": sa.get("client_email", "?"),
        }
    except Exception as exc:
        return {
            "status": "PARSE_FAILED",
            "error": str(exc),
            "raw_length": length,
            "raw_start": repr(preview_start),
            "raw_end": repr(preview_end),
        }


@router.post(
    "/sheets",
    response_model=ETLResponse,
    summary="Migrar Google Sheets → PostgreSQL",
    description="Migra las hojas del Sheet de producción al DB. Solo superadmin.",
)
async def run_sheets_etl(
    body: ETLRequest,
    _current_user=Depends(require_superadmin),
):
    # Credenciales: env var tiene prioridad, luego body
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GOOGLE_SERVICE_ACCOUNT_JSON no configurada en el servidor. "
                   "Configúrala en Coolify → Variables de entorno de bp-api.",
        )

    started = datetime.now(UTC)

    try:
        result = await asyncio.to_thread(
            _run_etl_sync, body.sheet_id, creds_json, body.tabs
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ETL falló: {exc}",
        )

    completed = datetime.now(UTC)
    duration = (completed - started).total_seconds()

    reports_out = {
        k: TabReport(**v) for k, v in result["reports"].items()
    }

    return ETLResponse(
        started_at=started.isoformat(),
        completed_at=completed.isoformat(),
        duration_seconds=duration,
        reports=reports_out,
        global_errors=result.get("global_errors", []),
    )


@router.get("/status", summary="Estado del ETL — conteo actual de registros")
async def etl_status(_current_user=Depends(require_superadmin)):
    """Cuenta los registros actuales en cada tabla migrada."""
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy import text

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise HTTPException(503, "DATABASE_URL no disponible")

    engine = create_async_engine(db_url)
    async with engine.connect() as conn:
        counts = {}
        queries = {
            "categorias": "SELECT COUNT(*) FROM catalog.categories",
            "productos": "SELECT COUNT(*) FROM catalog.products",
            "stock_items": "SELECT COUNT(*) FROM inventory.stock",
            "stock_total_units": "SELECT COALESCE(SUM(quantity),0) FROM inventory.stock",
            "clientes": "SELECT COUNT(*) FROM crm.customers",
            "ventas_legacy": "SELECT COUNT(*) FROM sales.orders WHERE channel LIKE '%LEGACY%'",
            "ventas_nuevas": "SELECT COUNT(*) FROM sales.orders WHERE channel NOT LIKE '%LEGACY%'",
            "gastos": "SELECT COUNT(*) FROM ops.legacy_id_map WHERE entity='gasto'",
            "cierres_caja": "SELECT COUNT(*) FROM ops.legacy_id_map WHERE entity='cierre_caja'",
            "maestro_proveedores": "SELECT COUNT(*) FROM ops.legacy_id_map WHERE entity='proveedor_sku'",
            "purchasing_suppliers": "SELECT COUNT(*) FROM purchasing.suppliers",
        }
        for key, sql in queries.items():
            result = await conn.execute(text(sql))
            counts[key] = result.scalar()
    await engine.dispose()
    return counts


# ── Fix sales dates — re-reads Ventas tab and updates occurred_at ─────────

class FixDatesRequest(BaseModel):
    sheet_id: str = DEFAULT_SHEET_ID
    dry_run: bool = False


class FixDatesResponse(BaseModel):
    total_orders: int
    updated: int
    skipped_no_date: int
    skipped_already_ok: int
    errors: list[str]
    sample_fixed: list[dict]


def _fix_dates_sync(sheet_id: str, creds_json_str: str, dry_run: bool) -> dict[str, Any]:
    import base64 as _b64
    import gspread
    import psycopg
    from google.oauth2.service_account import Credentials

    sa_b64 = os.environ.get("GOOGLE_SA_B64", "").strip()
    if sa_b64:
        sa_info = json.loads(_b64.b64decode(sa_b64).decode("utf-8"))
    else:
        raw = creds_json_str.strip()
        if not raw.startswith("{"):
            try:
                raw = _b64.b64decode(raw).decode("utf-8")
            except Exception:
                pass
        sa_info = json.loads(raw)
        pk = sa_info.get("private_key", "")
        if pk and "\n" not in pk and "\\n" in pk:
            sa_info["private_key"] = pk.replace("\\n", "\n")

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    gc_creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    gc = gspread.authorize(gc_creds)
    sh = gc.open_by_key(sheet_id)

    try:
        ws = sh.worksheet("Ventas")
        records = ws.get_all_records(empty2zero=False, head=1, default_blank="")
        vta_rows = [r for r in records if any(str(v).strip() for v in list(r.values())[:4])]
    except Exception as exc:
        return {"total_orders": 0, "updated": 0, "skipped_no_date": 0, "skipped_already_ok": 0, "errors": [str(exc)], "sample_fixed": []}

    raw_url = os.environ.get("DATABASE_URL_SYNC", "")
    conn_str = raw_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")

    updated = 0
    skipped_no_date = 0
    skipped_ok = 0
    errors: list[str] = []
    sample: list[dict] = []

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            for r in vta_rows:
                id_venta = str(r.get("ID_Venta") or "").strip()
                if not id_venta:
                    continue
                fecha = _parse_dt(r.get("Fecha"))
                if not fecha:
                    skipped_no_date += 1
                    continue

                order_num = f"LEG-{id_venta}"
                cur.execute("SELECT id, occurred_at FROM sales.orders WHERE order_number = %s", (order_num,))
                row = cur.fetchone()
                if not row:
                    continue
                order_id, current_dt = row
                # Only update if currently on 2026-05-10 (migration default) or significantly wrong
                if current_dt and abs((current_dt.replace(tzinfo=UTC) - fecha).days) < 1:
                    skipped_ok += 1
                    continue

                if len(sample) < 10:
                    sample.append({"order_number": order_num, "from": str(current_dt)[:10], "to": str(fecha)[:10]})

                if not dry_run:
                    try:
                        cur.execute(
                            "UPDATE sales.orders SET occurred_at = %s, created_at = %s WHERE id = %s",
                            (fecha, fecha, str(order_id)),
                        )
                        updated += 1
                    except Exception as exc:
                        errors.append(f"{order_num}: {exc}")
            if not dry_run:
                conn.commit()

    return {
        "total_orders": len(vta_rows),
        "updated": updated,
        "skipped_no_date": skipped_no_date,
        "skipped_already_ok": skipped_ok,
        "errors": errors[:20],
        "sample_fixed": sample,
    }


@router.post(
    "/fix-sales-dates",
    response_model=FixDatesResponse,
    summary="Corregir fechas de ventas legadas desde Google Sheets",
)
async def fix_sales_dates(
    body: FixDatesRequest,
    _current_user=Depends(require_superadmin),
):
    creds_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not creds_json:
        raise HTTPException(503, "GOOGLE_SERVICE_ACCOUNT_JSON no configurada")
    try:
        result = await asyncio.to_thread(_fix_dates_sync, body.sheet_id, creds_json, body.dry_run)
    except Exception as exc:
        raise HTTPException(500, f"Error: {exc}")
    return FixDatesResponse(**result)


# ── Bootstrap suppliers — crea purchasing.suppliers desde legado ──────────

class BootstrapSuppliersResponse(BaseModel):
    total_legacy: int
    created: int
    skipped: int
    errors: list[str]


def _bootstrap_suppliers_sync() -> dict[str, Any]:
    import psycopg

    raw_url = os.environ.get("DATABASE_URL_SYNC", "")
    conn_str = raw_url.replace("postgresql+psycopg://", "postgresql://").replace("postgresql+asyncpg://", "postgresql://")

    created = 0
    skipped = 0
    total_legacy = 0
    errors: list[str] = []

    with psycopg.connect(conn_str) as conn:
        with conn.cursor() as cur:
            # Recopilar nombres únicos de proveedores del legado
            cur.execute(
                "SELECT extra->>'nombre_proveedor', extra->>'id_proveedor' FROM ops.legacy_id_map WHERE entity='proveedor_sku'"
            )
            legacy_rows = cur.fetchall()
            total_legacy = len(legacy_rows)

            seen: set[str] = set()
            for (nombre, id_prov) in legacy_rows:
                name = (nombre or id_prov or "").strip()
                if not name or name.upper() in ("N/A", "-", ""):
                    continue
                name_key = name.lower()
                if name_key in seen:
                    continue
                seen.add(name_key)

                cur.execute("SELECT id FROM purchasing.suppliers WHERE LOWER(name) = %s", (name_key,))
                if cur.fetchone():
                    skipped += 1
                    continue

                # NIT: usar id_proveedor si parece un número, si no generar placeholder
                nit = (id_prov or "").strip()
                if not nit or not any(c.isdigit() for c in nit):
                    # Generar NIT placeholder único
                    nit = f"LEGADO-{len(seen):04d}"

                try:
                    cur.execute("SAVEPOINT sp_sup")
                    cur.execute(
                        """INSERT INTO purchasing.suppliers
                           (id, nit, name, is_active, payment_terms_days, created_at, updated_at)
                           VALUES (%s, %s, %s, true, 0, %s, %s)""",
                        (str(uuid.uuid4()), nit, name, _now(), _now()),
                    )
                    cur.execute("RELEASE SAVEPOINT sp_sup")
                    created += 1
                except Exception as exc:
                    cur.execute("ROLLBACK TO SAVEPOINT sp_sup")
                    errors.append(f"{name}: {exc}")

            conn.commit()

    return {"total_legacy": total_legacy, "created": created, "skipped": skipped, "errors": errors[:20]}


@router.post(
    "/bootstrap-suppliers",
    response_model=BootstrapSuppliersResponse,
    summary="Crear proveedores en purchasing.suppliers desde datos legados",
)
async def bootstrap_suppliers(_current_user=Depends(require_superadmin)):
    try:
        result = await asyncio.to_thread(_bootstrap_suppliers_sync)
    except Exception as exc:
        raise HTTPException(500, f"Error: {exc}")
    return BootstrapSuppliersResponse(**result)
