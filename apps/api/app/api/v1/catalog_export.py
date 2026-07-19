"""Export / import masivo de productos en Excel."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation
from sqlalchemy import select, text

from app.deps import DBSession, require_permission
from app.models.catalog import Brand, Category, Product

catalog_export_router = APIRouter(
    prefix="/catalog",
    tags=["catalog-export"],
    dependencies=[Depends(require_permission("admin"))],
)

# ── Paleta ────────────────────────────────────────────────────────────────────
_TEAL_DARK = "0D4A45"
_TEAL_MID = "187F77"
_TEAL_LIGHT = "E0F2F1"
_HDR_EDITABLE = "FFF9C4"   # amarillo suave — columna editable
_HDR_READONLY = "B2DFDB"   # teal claro — columna de solo lectura
_ROW_ALT = "F0FDF4"
_ROW_WHITE = "FFFFFF"
_LOCK_BG = "FAFAFA"

_THIN = Side(style="thin", color="CCCCCC")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)

# Columnas: (header, attr, editable, width)
_COLS = [
    ("ID",                  "id",                  False, 38),
    ("SKU",                 "sku",                 True,  16),
    ("Nombre",              "name",                True,  40),
    ("Categoría",           "category_name",       True,  22),
    ("Marca",               "brand_name",          True,  20),
    ("Descripción Corta",   "short_description",   True,  45),
    ("Descripción",         "description",         True,  60),
    ("Precio Venta",        "price",               True,  16),
    ("Precio Costo",        "cost",                True,  16),
    ("Precio Tachado",      "compare_at_price",    True,  16),
    ("Stock",               "stock",               False, 10),
    ("Activo",              "is_active_label",     True,  10),
    ("Publicado",           "is_published_label",  True,  12),
    ("Destacado",           "is_featured_label",   True,  12),
    ("Tiene Imagen",        "has_image",           False, 14),
    ("URL Imagen Principal","primary_image_url",   True,  50),
    ("Num. Imágenes",       "num_images",          False, 14),
    ("Tipo Mascota",        "pet_type",            True,  14),
    ("Etapa de Vida",       "life_stage",          True,  16),
    ("Tamaño",              "size_range",          True,  14),
    ("Peso (kg/g)",         "peso",                True,  14),
    ("Tags",                "tags_csv",            True,  35),
    ("SEO Título",          "seo_title",           True,  40),
    ("SEO Descripción",     "seo_description",     True,  55),
    ("Creado",              "created_at_label",    False, 20),
]


def _cell_style(ws, row: int, col: int, editable: bool, alt: bool):
    cell = ws.cell(row=row, column=col)
    cell.border = _BORDER
    cell.alignment = Alignment(vertical="top", wrap_text=False)
    if not editable:
        cell.fill = PatternFill("solid", fgColor=_LOCK_BG)
    elif alt:
        cell.fill = PatternFill("solid", fgColor=_ROW_ALT)
    else:
        cell.fill = PatternFill("solid", fgColor=_ROW_WHITE)
    return cell


async def _load_all_products(db: DBSession) -> list[dict]:
    rows = await db.execute(text("""
        SELECT
            p.id, p.sku, p.name, p.slug,
            p.short_description, p.description,
            p.price::float, p.cost::float,
            p.compare_at_price::float,
            p.is_active, p.is_published, p.is_featured,
            p.primary_image_url,
            COALESCE(jsonb_array_length(p.images), 0) AS num_images,
            p.pet_type, p.life_stage, p.size_range,
            p.attributes,
            p.tags,
            p.seo_title, p.seo_description,
            p.created_at,
            c.name AS category_name,
            b.name AS brand_name,
            COALESCE(SUM(s.quantity), 0)::int AS stock
        FROM catalog.products p
        LEFT JOIN catalog.categories c ON c.id = p.category_id
        LEFT JOIN catalog.brands     b ON b.id = p.brand_id
        LEFT JOIN inventory.stock    s ON s.product_id = p.id
        WHERE p.deleted_at IS NULL
        GROUP BY p.id, c.name, b.name
        ORDER BY c.name NULLS LAST, p.name
    """))
    products = []
    for r in rows.mappings():
        attrs = r["attributes"] or {}
        peso = attrs.get("peso") or attrs.get("weight") or attrs.get("Peso") or ""
        tags = r["tags"] or []
        products.append({
            "id": str(r["id"]),
            "sku": r["sku"] or "",
            "name": r["name"] or "",
            "category_name": r["category_name"] or "",
            "brand_name": r["brand_name"] or "",
            "short_description": r["short_description"] or "",
            "description": r["description"] or "",
            "price": float(r["price"] or 0),
            "cost": float(r["cost"] or 0),
            "compare_at_price": float(r["compare_at_price"]) if r["compare_at_price"] else "",
            "stock": int(r["stock"] or 0),
            "is_active_label": "SÍ" if r["is_active"] else "NO",
            "is_published_label": "SÍ" if r["is_published"] else "NO",
            "is_featured_label": "SÍ" if r["is_featured"] else "NO",
            "has_image": "SÍ" if r["primary_image_url"] else "NO",
            "primary_image_url": r["primary_image_url"] or "",
            "num_images": r["num_images"],
            "pet_type": r["pet_type"] or "",
            "life_stage": r["life_stage"] or "",
            "size_range": r["size_range"] or "",
            "peso": str(peso),
            "tags_csv": ", ".join(tags) if isinstance(tags, list) else "",
            "seo_title": r["seo_title"] or "",
            "seo_description": r["seo_description"] or "",
            "created_at_label": r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "",
        })
    return products


def _build_excel(products: list[dict], categories: list[str], brands: list[str]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Productos"

    # ── Instrucciones ────────────────────────────────────────────────────────
    ws_info = wb.create_sheet("INSTRUCCIONES", 0)
    ws_info.sheet_view.showGridLines = False
    ws_info["A1"] = "INSTRUCCIONES DE USO"
    ws_info["A1"].font = Font(bold=True, size=14, color="FFFFFF")
    ws_info["A1"].fill = PatternFill("solid", fgColor=_TEAL_DARK)
    ws_info["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws_info.merge_cells("A1:E1")
    ws_info.row_dimensions[1].height = 30

    instrucciones = [
        ("", ""),
        ("EXPORTAR", "Este Excel contiene TODOS tus productos con su información actual."),
        ("EDITAR", "Modifica las columnas EN AMARILLO. Las columnas en gris son solo lectura."),
        ("COLUMNA ID", "NO borres ni modifiques la columna ID — es la clave de importación."),
        ("ACTIVO/PUBLICADO", "Usa SÍ o NO (en mayúsculas) para los campos booleanos."),
        ("CATEGORÍA", "Escribe el nombre exacto de la categoría o déjalo vacío."),
        ("MARCA", "Escribe el nombre exacto de la marca o déjalo vacío."),
        ("TAGS", "Separados por coma. Ej: premium, adulto, pollo"),
        ("PESO", "Escribe el peso con unidad. Ej: 3kg, 500g, 2.5kg"),
        ("IMPORTAR", "Guarda el archivo y súbelo en el admin → Catálogo → Importar Excel."),
        ("", ""),
        ("CAMPOS EDITABLES", "SKU, Nombre, Categoría, Marca, Descripción Corta, Descripción,"),
        ("", "Precio Venta, Precio Costo, Precio Tachado, Activo, Publicado,"),
        ("", "Destacado, URL Imagen Principal, Tipo Mascota, Etapa de Vida,"),
        ("", "Tamaño, Peso, Tags, SEO Título, SEO Descripción"),
    ]
    for i, (label, detail) in enumerate(instrucciones, start=2):
        ws_info.cell(row=i, column=1, value=label).font = Font(bold=True, color=_TEAL_MID)
        ws_info.cell(row=i, column=2, value=detail)
    ws_info.column_dimensions["A"].width = 20
    ws_info.column_dimensions["B"].width = 80

    # ── Sheet de productos ───────────────────────────────────────────────────
    ws = wb["Productos"]
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "C3"

    # Fila 1: mega-título
    ws.merge_cells(f"A1:{get_column_letter(len(_COLS))}1")
    title_cell = ws["A1"]
    title_cell.value = f"Bigotes y Paticas — Catálogo de Productos ({len(products)} productos)"
    title_cell.font = Font(bold=True, size=13, color="FFFFFF")
    title_cell.fill = PatternFill("solid", fgColor=_TEAL_DARK)
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 28

    # Fila 2: encabezados
    for col_i, (header, _, editable, width) in enumerate(_COLS, start=1):
        cell = ws.cell(row=2, column=col_i, value=header)
        cell.font = Font(bold=True, size=10, color="FFFFFF" if not editable else "0D4A45")
        cell.fill = PatternFill("solid", fgColor=_TEAL_MID if not editable else "FFF176")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _BORDER
        ws.column_dimensions[get_column_letter(col_i)].width = width
    ws.row_dimensions[2].height = 32

    # Datos
    for row_i, prod in enumerate(products, start=3):
        alt = (row_i % 2 == 1)
        for col_i, (_, attr, editable, _) in enumerate(_COLS, start=1):
            val = prod.get(attr, "")
            cell = _cell_style(ws, row_i, col_i, editable, alt)
            cell.value = val
            if attr in ("price", "cost") and isinstance(val, (int, float)):
                cell.number_format = "#,##0"
            elif attr == "compare_at_price" and isinstance(val, (int, float)) and val:
                cell.number_format = "#,##0"
        ws.row_dimensions[row_i].height = 16

    # Dropdowns para Activo / Publicado / Destacado / PetType
    last_row = 2 + len(products)

    dv_sino = DataValidation(type="list", formula1='"SÍ,NO"', allow_blank=True)
    ws.add_data_validation(dv_sino)

    dv_pet = DataValidation(type="list", formula1='"perro,gato,ambos,"', allow_blank=True)
    ws.add_data_validation(dv_pet)

    # Columnas de SÍ/NO: Activo(12), Publicado(13), Destacado(14)
    for col_i in [12, 13, 14]:
        col_letter = get_column_letter(col_i)
        dv_sino.add(f"{col_letter}3:{col_letter}{last_row}")

    # Pet type col 18
    pet_col = get_column_letter(18)
    dv_pet.add(f"{pet_col}3:{pet_col}{last_row}")

    # Ocultar columna ID (col 1) — la dejamos visible pero angosta para que el
    # usuario no la borre accidentalmente; la marcamos en gris oscuro
    ws.column_dimensions["A"].width = 38

    # Hoja de listas para dropdowns de categoría y marca
    ws_lists = wb.create_sheet("_listas")
    ws_lists.sheet_state = "hidden"
    for i, cat in enumerate(sorted(categories), start=1):
        ws_lists.cell(row=i, column=1, value=cat)
    for i, br in enumerate(sorted(brands), start=1):
        ws_lists.cell(row=i, column=2, value=br)

    n_cats = len(categories)
    n_brands = len(brands)
    if n_cats > 0:
        dv_cat = DataValidation(
            type="list",
            formula1=f"_listas!$A$1:$A${n_cats}",
            allow_blank=True,
        )
        ws.add_data_validation(dv_cat)
        cat_col = get_column_letter(4)
        dv_cat.add(f"{cat_col}3:{cat_col}{last_row}")

    if n_brands > 0:
        dv_brand = DataValidation(
            type="list",
            formula1=f"_listas!$B$1:$B${n_brands}",
            allow_blank=True,
        )
        ws.add_data_validation(dv_brand)
        brand_col = get_column_letter(5)
        dv_brand.add(f"{brand_col}3:{brand_col}{last_row}")

    # Leyenda de colores debajo de los datos
    legend_row = last_row + 2
    ws.cell(row=legend_row, column=1, value="Amarillo = editable").font = Font(size=9, italic=True, color="888888")
    ws.cell(row=legend_row, column=3, value="Gris = solo lectura").font = Font(size=9, italic=True, color="888888")

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


@catalog_export_router.get("/export-excel")
async def export_products_excel(db: DBSession):
    """Descarga todos los productos en Excel para edición masiva."""
    products = await _load_all_products(db)

    cats = await db.execute(
        select(Category.name).where(Category.is_active == True).where(Category.deleted_at == None)  # noqa: E711,E712
    )
    brands = await db.execute(
        select(Brand.name).where(Brand.is_active == True).where(Brand.deleted_at == None)  # noqa: E711,E712
    )
    cat_names = [r[0] for r in cats.all() if r[0]]
    brand_names = [r[0] for r in brands.all() if r[0]]

    data = _build_excel(products, cat_names, brand_names)
    filename = f"BigotesyPaticas_Productos_{datetime.now(UTC).strftime('%Y%m%d')}.xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Importar ─────────────────────────────────────────────────────────────────

_COL_MAP = {
    "ID": "id",
    "SKU": "sku",
    "Nombre": "name",
    "Categoría": "category_name",
    "Marca": "brand_name",
    "Descripción Corta": "short_description",
    "Descripción": "description",
    "Precio Venta": "price",
    "Precio Costo": "cost",
    "Precio Tachado": "compare_at_price",
    "Activo": "is_active_label",
    "Publicado": "is_published_label",
    "Destacado": "is_featured_label",
    "URL Imagen Principal": "primary_image_url",
    "Tipo Mascota": "pet_type",
    "Etapa de Vida": "life_stage",
    "Tamaño": "size_range",
    "Peso (kg/g)": "peso",
    "Tags": "tags_csv",
    "SEO Título": "seo_title",
    "SEO Descripción": "seo_description",
}


@catalog_export_router.post("/import-excel")
async def import_products_excel(
    db: DBSession,
    file: UploadFile = File(...),
):
    """Importa el Excel editado y actualiza los productos en masa."""
    content = await file.read()
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(400, "Archivo Excel inválido")

    if "Productos" not in wb.sheetnames:
        raise HTTPException(400, "El archivo no tiene una hoja llamada 'Productos'")

    ws = wb["Productos"]

    # Detectar encabezados en fila 2
    headers: dict[int, str] = {}
    for cell in ws[2]:
        if cell.value and str(cell.value).strip() in _COL_MAP:
            headers[cell.column] = _COL_MAP[str(cell.value).strip()]

    if "id" not in headers.values():
        raise HTTPException(400, "Columna ID no encontrada — no se puede importar sin ella")

    # Cargar categorías y marcas para mapear nombre → id
    cats_rows = await db.execute(
        select(Category.id, Category.name).where(Category.deleted_at == None)  # noqa: E711
    )
    brands_rows = await db.execute(
        select(Brand.id, Brand.name).where(Brand.deleted_at == None)  # noqa: E711
    )
    cat_map = {r.name.strip().lower(): r.id for r in cats_rows.all()}
    brand_map = {r.name.strip().lower(): r.id for r in brands_rows.all()}

    updated = 0
    errors = []

    for row in ws.iter_rows(min_row=3, values_only=True):
        # Saltar filas vacías
        if not any(v for v in row):
            continue

        row_data: dict[str, object] = {}
        for col_i, field in headers.items():
            val = row[col_i - 1]
            row_data[field] = val

        product_id_raw = row_data.get("id")
        if not product_id_raw:
            continue

        try:
            product_id = uuid.UUID(str(product_id_raw).strip())
        except ValueError:
            errors.append(f"ID inválido: {product_id_raw}")
            continue

        # Construir dict de updates
        updates: dict[str, object] = {"updated_at": datetime.now(UTC)}

        def _str(v) -> str | None:
            return str(v).strip() if v not in (None, "") else None

        def _float(v) -> float | None:
            try:
                return float(v) if v not in (None, "") else None
            except (ValueError, TypeError):
                return None

        def _bool(v) -> bool | None:
            if v is None:
                return None
            return str(v).strip().upper() in ("SÍ", "SI", "S", "YES", "TRUE", "1")

        if "sku" in row_data and row_data["sku"]:
            updates["sku"] = str(row_data["sku"]).strip()
        if "name" in row_data and row_data["name"]:
            updates["name"] = str(row_data["name"]).strip()
        if "short_description" in row_data:
            updates["short_description"] = _str(row_data["short_description"])
        if "description" in row_data:
            updates["description"] = _str(row_data["description"])

        price = _float(row_data.get("price"))
        if price is not None:
            updates["price"] = price
        cost = _float(row_data.get("cost"))
        if cost is not None:
            updates["cost"] = cost
        cap = _float(row_data.get("compare_at_price"))
        if cap is not None:
            updates["compare_at_price"] = cap
        elif row_data.get("compare_at_price") in ("", None):
            updates["compare_at_price"] = None

        # Booleans
        for label_field, db_field in [
            ("is_active_label", "is_active"),
            ("is_published_label", "is_published"),
            ("is_featured_label", "is_featured"),
        ]:
            if label_field in row_data and row_data[label_field] is not None:
                updates[db_field] = _bool(row_data[label_field])

        # Imagen
        if "primary_image_url" in row_data:
            updates["primary_image_url"] = _str(row_data["primary_image_url"])

        # Filtros de catálogo
        if "pet_type" in row_data:
            updates["pet_type"] = _str(row_data["pet_type"])
        if "life_stage" in row_data:
            updates["life_stage"] = _str(row_data["life_stage"])
        if "size_range" in row_data:
            updates["size_range"] = _str(row_data["size_range"])

        # Peso → attributes
        if "peso" in row_data and row_data["peso"] not in (None, ""):
            updates["attributes"] = text(
                "attributes || jsonb_build_object('peso', :peso::text)"
            )
            # Se maneja abajo con raw SQL

        # Tags
        if "tags_csv" in row_data:
            raw_tags = row_data["tags_csv"]
            if raw_tags not in (None, ""):
                tag_list = [t.strip() for t in str(raw_tags).split(",") if t.strip()]
                updates["tags"] = tag_list
            else:
                updates["tags"] = []

        # SEO
        if "seo_title" in row_data:
            updates["seo_title"] = _str(row_data["seo_title"])
        if "seo_description" in row_data:
            updates["seo_description"] = _str(row_data["seo_description"])

        # Categoría
        cat_raw = row_data.get("category_name")
        if cat_raw not in (None, ""):
            cat_key = str(cat_raw).strip().lower()
            cat_id = cat_map.get(cat_key)
            if cat_id:
                updates["category_id"] = cat_id
            else:
                errors.append(f"Categoría no encontrada: '{cat_raw}' (SKU {row_data.get('sku', '?')})")

        # Marca
        brand_raw = row_data.get("brand_name")
        if brand_raw not in (None, ""):
            brand_key = str(brand_raw).strip().lower()
            brand_id = brand_map.get(brand_key)
            if brand_id:
                updates["brand_id"] = brand_id
            else:
                errors.append(f"Marca no encontrada: '{brand_raw}' (SKU {row_data.get('sku', '?')})")

        # Separar peso del resto (needs jsonb merge via raw SQL)
        peso_val = row_data.get("peso")
        non_json_updates = {k: v for k, v in updates.items() if not isinstance(v, type(text("")))}

        if peso_val not in (None, ""):
            await db.execute(
                text("""
                    UPDATE catalog.products
                    SET attributes = attributes || jsonb_build_object('peso', :peso::text),
                        updated_at = :now
                    WHERE id = :pid
                """),
                {"peso": str(peso_val).strip(), "now": datetime.now(UTC), "pid": str(product_id)},
            )

        # Tags es JSONB — usar raw SQL para evitar problemas de tipo
        tags_val = non_json_updates.pop("tags", None)
        if tags_val is not None:
            import json
            await db.execute(
                text("UPDATE catalog.products SET tags = :tags::jsonb WHERE id = :pid"),
                {"tags": json.dumps(tags_val, ensure_ascii=False), "pid": str(product_id)},
            )

        # El resto de los campos con SQLAlchemy ORM update
        simple = {k: v for k, v in non_json_updates.items() if k not in ("updated_at",)}
        if simple:
            simple["updated_at"] = datetime.now(UTC)
            await db.execute(
                text(
                    "UPDATE catalog.products SET "
                    + ", ".join(f"{k} = :{k}" for k in simple)
                    + " WHERE id = :pid AND deleted_at IS NULL"
                ),
                {**simple, "pid": str(product_id)},
            )

        updated += 1

    await db.commit()

    return {
        "updated": updated,
        "errors": errors[:50],
        "total_errors": len(errors),
        "message": f"{updated} productos actualizados" + (f", {len(errors)} advertencias" if errors else ""),
    }
