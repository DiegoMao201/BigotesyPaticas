"""
Importación masiva de inventario desde Excel — BigotesyPaticas
==============================================================
Lee "Inventario Mayo actualizado con cambios.xlsx" y aplica:
  1. Actualiza precio, costo y categoría de productos existentes (SKU UUID hex).
  2. Crea/actualiza productos con SKU corto (BP-*, RC-*) si existen o no.
  3. Crea nuevos productos para filas sin SKU, generando SKU automático.
  4. Fija el stock (inventory.stock) al valor de CONTEO FÍSICO de cada producto.

Uso:
  python scripts/etl/xlsx_inventory_import.py [--dry-run] [--db-url URL]

Por defecto conecta al tunnel SSH en localhost:5433.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
import uuid
from pathlib import Path

import openpyxl
import psycopg2
import psycopg2.extras

# ─── Configuración ───────────────────────────────────────────────────────────

EXCEL_PATH = Path(__file__).parent.parent.parent / "Inventario Mayo actualizado con cambios.xlsx"
DEFAULT_DB_URL = "postgresql://postgres:JE7zr39ODs6ZHrTgzH1OWgsvt5J005hid73BfIMjiIKit9KxqJSNXh3KOHowMXwb@127.0.0.1:5433/bp_prod"

# Prefijos de SKU por categoría para productos sin SKU
CAT_SKU_PREFIX = {
    "ARENA": "AEN",
    "ACCESORIOS": "ACC",
    "ASEO": "ASE",
    "CONCENTRADO": "CON",
    "JUGUETES": "JUG",
    "MEDICAMENTO": "MED",
    "SNACK": "SNK",
}

# ─── Helpers ─────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """Genera slug URL-safe a partir de un string."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text.lower())
    text = re.sub(r"[\s_-]+", "-", text).strip("-")
    return text


def is_valid_hex_sku(val) -> bool:
    """Devuelve True si val es una cadena hexadecimal de 32 chars (UUID sin guiones)."""
    if not val:
        return False
    s = str(val).strip()
    return len(s) == 32 and re.fullmatch(r"[0-9a-f]{32}", s, re.I) is not None


def hex_to_sku(val: str) -> str:
    """Normaliza UUID-hex a string tal cual (lowercase, sin guiones)."""
    return str(val).strip().lower()


def parse_excel(path: Path) -> list[dict]:
    """
    Parsea la hoja 'Conteo' del Excel y devuelve lista de dicts con:
      sku_raw, name, category, cost, stock_sys, conteo, price, species
    Omite filas de encabezado de categoría y filas vacías.
    """
    wb = openpyxl.load_workbook(str(path), data_only=True)
    ws = wb["Conteo"]
    products = []

    for row in ws.iter_rows(min_row=4, values_only=True):
        if len(row) < 8:
            continue
        sku_raw = row[0]
        name = row[1]
        category = row[2]
        cost = row[3]
        stock_sys = row[4]
        conteo = row[5]
        price = row[7]
        species = row[8] if len(row) > 8 else None

        # Omitir filas de cabecera de categoría (name es None o vacía)
        if not name or not category:
            continue

        # Normalizar valores
        name = str(name).strip()
        category = str(category).strip().upper()
        cost = int(cost or 0)
        conteo = int(conteo or 0)
        price = int(price or 0)
        species = str(species).strip().upper() if species else None

        products.append(
            {
                "sku_raw": sku_raw,
                "name": name,
                "category": category,
                "cost": cost,
                "stock_sys": int(stock_sys or 0),
                "conteo": conteo,
                "price": price,
                "species": species,
            }
        )

    return products


def ensure_category(conn, name: str, dry_run: bool) -> str | None:
    """Retorna category_id (UUID str) existente o crea la categoría."""
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM catalog.categories WHERE UPPER(name) = %s AND deleted_at IS NULL LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if row:
        return str(row[0])
    # Crear categoría si no existe
    if dry_run:
        print(f"  [DRY-RUN] Crearía categoría: {name}")
        return None
    cat_id = str(uuid.uuid4())
    cat_slug = slugify(name)
    # Resolver conflicto de slug
    cur.execute(
        "SELECT id FROM catalog.categories WHERE slug = %s AND deleted_at IS NULL LIMIT 1",
        (cat_slug,),
    )
    if cur.fetchone():
        cat_slug = f"{cat_slug}-{cat_id[:6]}"
    cur.execute(
        """
        INSERT INTO catalog.categories (id, name, slug, is_active, created_at, updated_at)
        VALUES (%s, %s, %s, true, now(), now())
        """,
        (cat_id, name.capitalize(), cat_slug),
    )
    print(f"  [NEW CAT] {name} → {cat_id}")
    return cat_id


def get_default_location(conn, dry_run: bool) -> str | None:
    """Obtiene o crea la ubicación de stock por defecto."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM inventory.stock_locations WHERE is_default = 1 LIMIT 1")
    row = cur.fetchone()
    if row:
        return str(row[0])
    # Fallback: cualquier location
    cur.execute("SELECT id FROM inventory.stock_locations LIMIT 1")
    row = cur.fetchone()
    if row:
        return str(row[0])
    # Crear location por defecto
    if dry_run:
        print("  [DRY-RUN] Crearía stock location 'Tienda Principal'")
        return None
    loc_id = str(uuid.uuid4())
    cur.execute(
        """
        INSERT INTO inventory.stock_locations (id, code, name, is_default, created_at, updated_at)
        VALUES (%s, 'MAIN', 'Tienda Principal', 1, now(), now())
        """,
        (loc_id,),
    )
    print(f"  [NEW LOC] Tienda Principal → {loc_id}")
    return loc_id


def upsert_stock(conn, product_id: str, location_id: str, quantity: int, dry_run: bool):
    """Crea o actualiza registro inventory.stock."""
    if dry_run:
        return
    cur = conn.cursor()
    cur.execute(
        "SELECT id, quantity FROM inventory.stock WHERE product_id = %s AND location_id = %s LIMIT 1",
        (product_id, location_id),
    )
    row = cur.fetchone()
    if row:
        stock_id, old_qty = row
        cur.execute(
            "UPDATE inventory.stock SET quantity = %s, updated_at = now() WHERE id = %s",
            (quantity, stock_id),
        )
        # Registrar movimiento de ajuste
        cur.execute(
            """
            INSERT INTO inventory.stock_movements
              (id, product_id, location_id, movement_type, quantity_delta, quantity_after, notes, occurred_at, created_at, updated_at)
            VALUES (%s, %s, %s, 'COUNT_ADJUST', %s, %s, 'Importación inventario Mayo 2026', now(), now(), now())
            """,
            (str(uuid.uuid4()), product_id, location_id, quantity - old_qty, quantity),
        )
    else:
        cur.execute(
            """
            INSERT INTO inventory.stock
              (id, product_id, location_id, quantity, reserved, created_at, updated_at)
            VALUES (%s, %s, %s, %s, 0, now(), now())
            """,
            (str(uuid.uuid4()), product_id, location_id, quantity),
        )
        if quantity != 0:
            cur.execute(
                """
                INSERT INTO inventory.stock_movements
                  (id, product_id, location_id, movement_type, quantity_delta, quantity_after, notes, occurred_at, created_at, updated_at)
                VALUES (%s, %s, %s, 'COUNT_ADJUST', %s, %s, 'Importación inventario Mayo 2026', now(), now(), now())
                """,
                (str(uuid.uuid4()), product_id, location_id, quantity, quantity),
            )


def generate_sku(conn, category: str, name: str) -> str:
    """Genera un SKU único para productos nuevos: BP-{PREFIX}-{seq}."""
    prefix = CAT_SKU_PREFIX.get(category, "PRD")
    cur = conn.cursor()
    # Tomar el mayor número existente con este prefix
    cur.execute(
        "SELECT sku FROM catalog.products WHERE sku LIKE %s ORDER BY sku DESC LIMIT 20",
        (f"BP-{prefix}-%",),
    )
    rows = cur.fetchall()
    max_num = 0
    for (sku,) in rows:
        parts = sku.split("-")
        if len(parts) == 3:
            try:
                n = int(parts[2])
                if n > max_num:
                    max_num = n
            except ValueError:
                pass
    return f"BP-{prefix}-{max_num + 1:03d}"


def run_import(db_url: str, dry_run: bool):
    print(f"{'[DRY-RUN] ' if dry_run else ''}Conectando a BD...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False

    try:
        print(f"Leyendo Excel: {EXCEL_PATH.name}")
        products = parse_excel(EXCEL_PATH)
        print(f"  Filas parseadas: {len(products)}")

        location_id = get_default_location(conn, dry_run)
        if not location_id and not dry_run:
            raise RuntimeError("No se pudo obtener/crear stock location por defecto")

        # Precache de categorías
        category_map: dict[str, str | None] = {}

        stats = {"updated": 0, "created": 0, "skipped": 0, "errors": 0}
        cur = conn.cursor()

        for _i, p in enumerate(products):
            sku_raw = p["sku_raw"]
            name = p["name"]
            cat_name = p["category"]
            cost = p["cost"]
            conteo = p["conteo"]
            price = p["price"]
            species = p["species"]

            # Resolver category_id
            if cat_name not in category_map:
                category_map[cat_name] = ensure_category(conn, cat_name, dry_run)
            category_id = category_map[cat_name]

            attributes = {}
            if species:
                attributes["species"] = species.lower()

            # ── CASO 1: SKU es UUID hex (producto existente) ──────────────────
            if is_valid_hex_sku(sku_raw):
                sku = hex_to_sku(str(sku_raw))
                cur.execute(
                    "SELECT id FROM catalog.products WHERE sku = %s AND deleted_at IS NULL LIMIT 1",
                    (sku,),
                )
                row = cur.fetchone()
                if row:
                    product_id = str(row[0])
                    if not dry_run:
                        if category_id:
                            cur.execute(
                                """
                                UPDATE catalog.products
                                SET price = %s, cost = %s, category_id = %s,
                                    attributes = attributes || %s::jsonb, updated_at = now()
                                WHERE id = %s
                                """,
                                (
                                    price,
                                    cost,
                                    category_id,
                                    psycopg2.extras.Json(attributes) if attributes else "{}",
                                    product_id,
                                ),
                            )
                        else:
                            cur.execute(
                                """
                                UPDATE catalog.products
                                SET price = %s, cost = %s,
                                    attributes = attributes || %s::jsonb, updated_at = now()
                                WHERE id = %s
                                """,
                                (
                                    price,
                                    cost,
                                    psycopg2.extras.Json(attributes) if attributes else "{}",
                                    product_id,
                                ),
                            )
                        upsert_stock(conn, product_id, location_id, conteo, dry_run)
                    stats["updated"] += 1
                else:
                    print(f"  [WARN] SKU no encontrado en DB: {sku} — {name}")
                    stats["skipped"] += 1
                continue

            # ── CASO 2: SKU corto ya asignado (BP-*, RC-*, etc.) ─────────────
            if sku_raw and str(sku_raw).strip():
                sku = str(sku_raw).strip()
                cur.execute(
                    "SELECT id FROM catalog.products WHERE sku = %s AND deleted_at IS NULL LIMIT 1",
                    (sku,),
                )
                row = cur.fetchone()
                if row:
                    # Producto ya existe con ese SKU corto → solo actualizar
                    product_id = str(row[0])
                    if not dry_run:
                        if category_id:
                            cur.execute(
                                """
                                UPDATE catalog.products
                                SET price = %s, cost = %s, category_id = %s,
                                    attributes = attributes || %s::jsonb, updated_at = now()
                                WHERE id = %s
                                """,
                                (
                                    price,
                                    cost,
                                    category_id,
                                    psycopg2.extras.Json(attributes) if attributes else "{}",
                                    product_id,
                                ),
                            )
                        else:
                            cur.execute(
                                """
                                UPDATE catalog.products
                                SET price = %s, cost = %s,
                                    attributes = attributes || %s::jsonb, updated_at = now()
                                WHERE id = %s
                                """,
                                (
                                    price,
                                    cost,
                                    psycopg2.extras.Json(attributes) if attributes else "{}",
                                    product_id,
                                ),
                            )
                        upsert_stock(conn, product_id, location_id, conteo, dry_run)
                    stats["updated"] += 1
                    continue
                # No existe → crear con el SKU corto dado
                pass  # fall through to creation logic below

            # ── CASO 3: Sin SKU → generar nuevo ──────────────────────────────
            if not sku_raw or not str(sku_raw).strip():
                if dry_run:
                    sku = f"BP-{CAT_SKU_PREFIX.get(cat_name, 'PRD')}-XXX"
                else:
                    sku = generate_sku(conn, cat_name, name)
            else:
                # Viene del caso 2 fall-through (SKU corto no existe en DB)
                sku = str(sku_raw).strip()

            # Crear producto nuevo
            product_id = str(uuid.uuid4())
            slug_base = slugify(name)
            slug = slug_base

            if not dry_run:
                # Resolver conflicto de slug
                cur.execute(
                    "SELECT id FROM catalog.products WHERE slug = %s AND deleted_at IS NULL LIMIT 1",
                    (slug,),
                )
                if cur.fetchone():
                    slug = f"{slug_base}-{product_id[:6]}"

                # Resolver conflicto de SKU (por si generate_sku tuvo race)
                cur.execute(
                    "SELECT id FROM catalog.products WHERE sku = %s AND deleted_at IS NULL LIMIT 1",
                    (sku,),
                )
                if cur.fetchone():
                    sku = f"{sku}-{product_id[:4]}"

                margin = round((price - cost) / price, 4) if price > 0 else 0.20

                cur.execute(
                    """
                    INSERT INTO catalog.products
                      (id, sku, name, slug, category_id, cost, price, margin_pct,
                       is_active, is_featured, is_published,
                       attributes, images, tags,
                       created_at, updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,
                            true, false, true,
                            %s,'[]'::jsonb,'[]'::jsonb,
                            now(), now())
                    """,
                    (
                        product_id,
                        sku,
                        name,
                        slug,
                        category_id,
                        cost,
                        price,
                        margin,
                        psycopg2.extras.Json(attributes),
                    ),
                )
                upsert_stock(conn, product_id, location_id, conteo, dry_run)
                stats["created"] += 1
                print(f"  [NEW] {sku} — {name} (stock={conteo})")
            else:
                print(f"  [DRY-RUN NEW] {sku} — {name} (stock={conteo})")
                stats["created"] += 1

        if not dry_run:
            conn.commit()
            print("\n✓ Transacción confirmada (commit).")
        else:
            conn.rollback()
            print("\n[DRY-RUN] No se aplicaron cambios.")

        print("\nResumen:")
        print(f"  Actualizados:  {stats['updated']}")
        print(f"  Creados:       {stats['created']}")
        print(f"  Omitidos:      {stats['skipped']}")
        print(f"  Errores:       {stats['errors']}")

    except Exception as exc:
        conn.rollback()
        print(f"\n[ERROR] {exc}")
        raise
    finally:
        conn.close()


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Importar inventario desde Excel a PostgreSQL")
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo muestra cambios, no escribe en BD"
    )
    parser.add_argument("--db-url", default=DEFAULT_DB_URL, help="URL de conexión PostgreSQL")
    args = parser.parse_args()

    run_import(args.db_url, args.dry_run)
