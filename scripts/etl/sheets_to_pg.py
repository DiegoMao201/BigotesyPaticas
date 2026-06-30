"""
ETL Sheets → PostgreSQL para Bigotes y Paticas.

Estrategia:
  - Lee cada tab del Google Sheet de origen.
  - Mapea cada fila a su modelo SQLAlchemy en `apps/api/app/models/`.
  - Idempotente vía tabla `ops.legacy_id_map(legacy_source, legacy_id, target_table, target_id)`.
  - Reporta conteos, integridad y filas rechazadas a `etl_logs/`.

Uso típico:
    python scripts/etl/sheets_to_pg.py --tab products --dry-run
    python scripts/etl/sheets_to_pg.py --tab products
    python scripts/etl/sheets_to_pg.py --all

Requiere:
    GOOGLE_SHEETS_CREDENTIALS_JSON  (path a service account JSON)
    GOOGLE_SHEET_ID                 (ID del sheet origen)
    DATABASE_URL_SYNC               (Postgres del API)

NOTA: Este script es el SCAFFOLD inicial. Cada handler `_handle_<tab>` debe
implementarse según el shape real de cada tab. Hasta que el usuario confirme
estructuras, este script lista los tabs existentes y produce un mapeo dry.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


# --- Lazy imports (algunos no son obligatorios en dry-run) ---
def _lazy_gspread():
    try:
        import gspread  # type: ignore
        from google.oauth2.service_account import Credentials  # type: ignore

        return gspread, Credentials
    except ImportError as e:
        print(f"Faltan deps: pip install gspread google-auth\n{e}", file=sys.stderr)
        raise


def _lazy_sa():
    try:
        from sqlalchemy import create_engine, text  # type: ignore

        return create_engine, text
    except ImportError as e:
        print(f"Faltan deps: pip install sqlalchemy psycopg[binary]\n{e}", file=sys.stderr)
        raise


@dataclass
class TabReport:
    name: str
    rows_read: int = 0
    rows_inserted: int = 0
    rows_updated: int = 0
    rows_skipped: int = 0
    rows_rejected: int = 0
    rejections: list[dict[str, Any]] = field(default_factory=list)


# Mapa de handlers: tab_name → fn(rows, conn, dry_run) -> TabReport
HANDLERS: dict[str, Callable[..., TabReport]] = {}


def handler(tab_name: str):
    def deco(fn):
        HANDLERS[tab_name] = fn
        return fn

    return deco


# ---------- Handlers (esqueleto, completar cuando conozcamos las tabs) ----------


@handler("products")
def _h_products(rows: list[dict], conn, dry_run: bool) -> TabReport:
    """
    Tab: Inventario (o Maestro_Productos)
    Columnas esperadas (normalizadas con _norm_col):
      sku / codigo → catalog.products.sku
      nombre / name → products.name
      marca → catalog.brands.name
      categoria → catalog.categories.name
      precio / precio_venta → products.price (COP)
      costo / precio_costo → products.cost (COP)
      descripcion → products.description
      stock / cantidad → inventory.stock.quantity
      imagen / url_imagen → products.primary_image_url
      activo (bool/int) → products.is_active
    """
    import re
    import unicodedata
    from datetime import UTC, datetime

    rep = TabReport(name="products", rows_read=len(rows))
    if not rows:
        return rep

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]", "_", s.lower().strip()).strip("_")

    def _money(val) -> int | None:
        if val is None or str(val).strip() in ("", "-"):
            return None
        cleaned = re.sub(r"[^\d,\.]", "", str(val)).replace(",", "")
        try:
            return int(float(cleaned))
        except ValueError:
            return None

    def _bool(val) -> bool:
        if isinstance(val, bool):
            return val
        return str(val).strip().lower() in ("1", "si", "sí", "yes", "true", "activo", "x")

    def _slug(name: str) -> str:
        n = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]+", "-", n.lower().strip()).strip("-")

    if dry_run or conn is None:
        # dry-run: solo validar sin escribir
        for r in rows:
            nr = {_norm(k): v for k, v in r.items()}
            sku = (nr.get("sku") or nr.get("codigo") or "").strip()
            if not sku:
                rep.rows_rejected += 1
                rep.rejections.append({"reason": "sku/codigo vacío", "raw": r})
            else:
                rep.rows_skipped += 1
        return rep

    now = datetime.now(UTC)
    for r in rows:
        nr = {_norm(k): v for k, v in r.items()}
        sku = (nr.get("sku") or nr.get("codigo") or "").strip()
        if not sku:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": "sku vacío", "raw": r})
            continue
        name = (nr.get("nombre") or nr.get("name") or nr.get("producto") or sku).strip()
        price = _money(nr.get("precio") or nr.get("precio_venta") or nr.get("pvp"))
        cost = _money(nr.get("costo") or nr.get("precio_costo") or nr.get("costo_unitario"))
        is_active = _bool(nr.get("activo", True))
        image = (nr.get("imagen") or nr.get("url_imagen") or "").strip() or None
        desc = (nr.get("descripcion") or nr.get("description") or "").strip() or None

        # Upsert via raw SQL for simplicity (no SQLAlchemy models available in scripts)
        res = conn.execute(
            "SELECT id FROM catalog.products WHERE sku = :sku",
            {"sku": sku},
        ).fetchone()
        if res:
            conn.execute(
                """UPDATE catalog.products SET name=:name, price=:price, cost=:cost,
                   is_active=:active, primary_image_url=:img, updated_at=:now
                   WHERE sku=:sku""",
                {
                    "name": name,
                    "price": price,
                    "cost": cost,
                    "active": is_active,
                    "img": image,
                    "now": now,
                    "sku": sku,
                },
            )
            rep.rows_updated += 1
        else:
            conn.execute(
                """INSERT INTO catalog.products
                   (sku, slug, name, short_description, price, cost, is_active, primary_image_url, created_at, updated_at)
                   VALUES (:sku, :slug, :name, :desc, :price, :cost, :active, :img, :now, :now)""",
                {
                    "sku": sku,
                    "slug": _slug(name),
                    "name": name,
                    "desc": desc,
                    "price": price,
                    "cost": cost,
                    "active": is_active,
                    "img": image,
                    "now": now,
                },
            )
            rep.rows_inserted += 1
    return rep


@handler("inventory")
def _h_inventory(rows: list[dict], conn, dry_run: bool) -> TabReport:
    """
    Tab: Inventario
    Columnas:
      sku / codigo → referencia a catalog.products
      cantidad / stock / qty → inventory.stock.quantity
      ubicacion / location → inventory.stock_locations.name
    """
    import re
    import unicodedata

    rep = TabReport(name="inventory", rows_read=len(rows))

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]", "_", s.lower().strip()).strip("_")

    def _int(v) -> int:
        try:
            return max(0, int(float(str(v).replace(",", "").strip())))
        except (ValueError, TypeError):
            return 0

    for r in rows:
        nr = {_norm(k): v for k, v in r.items()}
        sku = (nr.get("sku") or nr.get("codigo") or "").strip()
        qty = _int(nr.get("cantidad") or nr.get("stock") or nr.get("qty") or 0)
        if not sku:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": "sku vacío", "raw": r})
            continue
        if dry_run or conn is None:
            rep.rows_skipped += 1
            continue
        prod = conn.execute(
            "SELECT id FROM catalog.products WHERE sku = :sku", {"sku": sku}
        ).fetchone()
        if not prod:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": f"producto no encontrado sku={sku}", "raw": r})
            continue
        existing = conn.execute(
            "SELECT id FROM inventory.stock WHERE product_id = :pid LIMIT 1",
            {"pid": prod[0]},
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE inventory.stock SET quantity=:q WHERE id=:id",
                {"q": qty, "id": existing[0]},
            )
            rep.rows_updated += 1
        else:
            conn.execute(
                "INSERT INTO inventory.stock (product_id, quantity, reserved) VALUES (:pid, :q, 0)",
                {"pid": prod[0], "q": qty},
            )
            rep.rows_inserted += 1
    return rep


@handler("customers")
def _h_customers(rows: list[dict], conn, dry_run: bool) -> TabReport:
    """
    Tab: Clientes
    Columnas:
      nombre / nombre_completo → crm.customers.full_name
      cedula / documento / nit → document_id
      email / correo → email
      telefono / celular → phone
      ciudad / municipio → city
      direccion → address
    """
    import re
    import unicodedata
    from datetime import UTC, datetime

    rep = TabReport(name="customers", rows_read=len(rows))

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]", "_", s.lower().strip()).strip("_")

    now = datetime.now(UTC)
    for r in rows:
        nr = {_norm(k): v for k, v in r.items()}
        full_name = (
            nr.get("nombre") or nr.get("nombre_completo") or nr.get("cliente") or ""
        ).strip()
        if not full_name:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": "nombre vacío", "raw": r})
            continue
        doc = (nr.get("cedula") or nr.get("documento") or nr.get("nit") or "").strip() or None
        email = (nr.get("email") or nr.get("correo") or "").strip().lower() or None
        phone = (nr.get("telefono") or nr.get("celular") or "").strip() or None
        city = (nr.get("ciudad") or nr.get("municipio") or "").strip() or None
        address = (nr.get("direccion") or nr.get("address") or "").strip() or None

        if dry_run or conn is None:
            rep.rows_skipped += 1
            continue

        # Deduplication by document_id then email
        existing = None
        if doc:
            existing = conn.execute(
                "SELECT id FROM crm.customers WHERE document_id = :d AND deleted_at IS NULL",
                {"d": doc},
            ).fetchone()
        if not existing and email:
            existing = conn.execute(
                "SELECT id FROM crm.customers WHERE email = :e AND deleted_at IS NULL",
                {"e": email},
            ).fetchone()

        if existing:
            rep.rows_skipped += 1
        else:
            conn.execute(
                """INSERT INTO crm.customers (full_name, document_id, email, phone, city, address, created_at, updated_at)
                   VALUES (:fn, :doc, :em, :ph, :ct, :ad, :now, :now)""",
                {
                    "fn": full_name,
                    "doc": doc,
                    "em": email,
                    "ph": phone,
                    "ct": city,
                    "ad": address,
                    "now": now,
                },
            )
            rep.rows_inserted += 1
    return rep


@handler("sales")
def _h_sales(rows: list[dict], conn, dry_run: bool) -> TabReport:
    """
    Tab: Ventas
    Columnas esperadas:
      numero_orden / id_venta → sales.orders.order_number
      fecha / fecha_venta → occurred_at
      cliente / cedula_cliente → customer (lookup by doc or name)
      total / total_venta → grand_total (COP)
      estado → status
      canal / medio → channel
      notas → notes
    """
    import re
    import unicodedata
    from datetime import UTC, datetime

    rep = TabReport(name="sales", rows_read=len(rows))

    def _norm(s: str) -> str:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
        return re.sub(r"[^a-z0-9]", "_", s.lower().strip()).strip("_")

    def _money(val) -> int:
        if val is None or str(val).strip() in ("", "-"):
            return 0
        cleaned = re.sub(r"[^\d,\.]", "", str(val)).replace(",", "")
        try:
            return int(float(cleaned))
        except ValueError:
            return 0

    def _parse_date(val):
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(str(val).strip(), fmt).replace(tzinfo=UTC)
            except ValueError:
                continue
        return datetime.now(UTC)

    STATUS_MAP = {
        "completada": "completed",
        "pagada": "completed",
        "entregada": "completed",
        "pendiente": "pending",
        "cancelada": "cancelled",
        "procesando": "processing",
    }

    now = datetime.now(UTC)
    for r in rows:
        nr = {_norm(k): v for k, v in r.items()}
        order_number = str(
            nr.get("numero_orden") or nr.get("id_venta") or nr.get("orden") or ""
        ).strip()
        if not order_number:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": "numero_orden vacío", "raw": r})
            continue
        total = _money(nr.get("total") or nr.get("total_venta") or nr.get("valor"))
        occurred = _parse_date(nr.get("fecha") or nr.get("fecha_venta") or now)
        raw_status = str(nr.get("estado") or "").strip().lower()
        status = STATUS_MAP.get(raw_status, "completed")
        channel = (
            str(nr.get("canal") or nr.get("medio") or "physical").strip().lower() or "physical"
        )

        if dry_run or conn is None:
            rep.rows_skipped += 1
            continue

        existing = conn.execute(
            "SELECT id FROM sales.orders WHERE order_number = :on",
            {"on": order_number},
        ).fetchone()
        if existing:
            rep.rows_skipped += 1
        else:
            conn.execute(
                """INSERT INTO sales.orders
                   (order_number, channel, status, grand_total, subtotal, paid_amount,
                    balance_due, payment_status, occurred_at, created_at, updated_at)
                   VALUES (:on, :ch, :st, :gt, :gt, :gt, 0, 'paid', :oc, :now, :now)""",
                {
                    "on": order_number,
                    "ch": channel,
                    "st": status,
                    "gt": total,
                    "oc": occurred,
                    "now": now,
                },
            )
            rep.rows_inserted += 1
    return rep


# ---------- Driver ----------


def fetch_tab_rows(tab: str) -> list[dict]:
    gspread, Credentials = _lazy_gspread()
    creds_path = os.environ["GOOGLE_SHEETS_CREDENTIALS_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.worksheet(tab)
    return ws.get_all_records()


def list_tabs() -> list[str]:
    gspread, Credentials = _lazy_gspread()
    creds_path = os.environ["GOOGLE_SHEETS_CREDENTIALS_JSON"]
    sheet_id = os.environ["GOOGLE_SHEET_ID"]
    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    return [ws.title for ws in sh.worksheets()]


def write_log(reports: list[TabReport], outdir: Path) -> Path:
    outdir.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    out = outdir / f"etl-{ts}.json"
    out.write_text(
        json.dumps(
            {"ts": ts, "reports": [r.__dict__ for r in reports]}, ensure_ascii=False, indent=2
        )
    )
    return out


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--tab", help="Nombre del tab a importar")
    p.add_argument("--all", action="store_true", help="Importar todos los tabs con handler")
    p.add_argument("--list-tabs", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--logs", default="etl_logs", type=Path)
    args = p.parse_args()

    if args.list_tabs:
        for t in list_tabs():
            handled = "✓" if t in HANDLERS else " "
            print(f"  [{handled}] {t}")
        return 0

    targets: list[str] = []
    if args.all:
        targets = list(HANDLERS.keys())
    elif args.tab:
        targets = [args.tab]
    else:
        p.print_help()
        return 2

    create_engine, text = (None, None)
    conn = None
    if not args.dry_run:
        create_engine, text = _lazy_sa()
        engine = create_engine(os.environ["DATABASE_URL_SYNC"])
        conn = engine.connect()

    reports: list[TabReport] = []
    for tab in targets:
        if tab not in HANDLERS:
            print(f"⚠ no hay handler para tab '{tab}', saltando")
            continue
        print(f"→ ETL tab: {tab}")
        rows = fetch_tab_rows(tab)
        rep = HANDLERS[tab](rows, conn, args.dry_run)
        reports.append(rep)
        print(
            f"  read={rep.rows_read} ins={rep.rows_inserted} upd={rep.rows_updated} skip={rep.rows_skipped} rej={rep.rows_rejected}"
        )

    if conn:
        conn.commit()
        conn.close()

    log = write_log(reports, args.logs)
    print(f"\nReporte: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
