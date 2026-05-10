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
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

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
    rep = TabReport(name="products", rows_read=len(rows))
    # TODO: mapear a catalog.products + catalog.product_variants
    # Fields esperados: sku, name, brand, category, price, cost, barcode, ...
    for r in rows:
        sku = (r.get("sku") or r.get("SKU") or "").strip()
        if not sku:
            rep.rows_rejected += 1
            rep.rejections.append({"reason": "sku vacío", "row": r})
            continue
        rep.rows_skipped += 1  # placeholder
    return rep


@handler("inventory")
def _h_inventory(rows: list[dict], conn, dry_run: bool) -> TabReport:
    rep = TabReport(name="inventory", rows_read=len(rows))
    # TODO: mapear a inventory.stock_items
    rep.rows_skipped = len(rows)
    return rep


@handler("sales")
def _h_sales(rows: list[dict], conn, dry_run: bool) -> TabReport:
    rep = TabReport(name="sales", rows_read=len(rows))
    # TODO: mapear a sales.sales + sales.sale_items
    rep.rows_skipped = len(rows)
    return rep


@handler("customers")
def _h_customers(rows: list[dict], conn, dry_run: bool) -> TabReport:
    rep = TabReport(name="customers", rows_read=len(rows))
    # TODO: mapear a crm.customers
    rep.rows_skipped = len(rows)
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
    out.write_text(json.dumps(
        {"ts": ts, "reports": [r.__dict__ for r in reports]},
        ensure_ascii=False, indent=2
    ))
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
        print(f"  read={rep.rows_read} ins={rep.rows_inserted} upd={rep.rows_updated} skip={rep.rows_skipped} rej={rep.rows_rejected}")

    if conn:
        conn.commit()
        conn.close()

    log = write_log(reports, args.logs)
    print(f"\nReporte: {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
