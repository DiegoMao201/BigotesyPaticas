"""Códigos de barras de los productos, para la pistola lectora (26-oct-2026).

Diego: *"en producto selecciono mi producto, paso el lector de barras y lo guardo,
eso se haría una sola vez"*. Con eso la pistola sirve en ventas (POS) y en la
búsqueda de productos.

De dónde salen los códigos:

- **El lector en el admin**: la fuente segura, porque registra lo que trae la bolsa.
- **La factura XML del proveedor**: la DIAN tiene el campo
  `StandardItemIdentification` con `schemeID="010"` (GTIN). Algunos proveedores lo
  llenan y otros no (Royal Canin solo manda su código interno). El importador ya
  lo guarda como `sku_proveedor` cuando viene, así que aquí no se toca el parser:
  al recibir la compra, si ese código es un EAN válido y la línea viene por
  unidad (`factor_pack = 1`), se guarda también como código de barras.
- **`attributes.gtin`** de la ficha, el que ya se manda a Merchant.

El relleno de abajo hace lo mismo con lo que ya está guardado.
"""

from alembic import op
from app.services.codigos_barras import es_gtin_unidad
from sqlalchemy import text

revision = "0054_codigos_barras"
down_revision = "0053_candado_publicar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS catalog.product_barcodes (
            code        varchar(32) PRIMARY KEY,
            product_id  uuid NOT NULL REFERENCES catalog.products(id) ON DELETE CASCADE,
            source      varchar(20) NOT NULL DEFAULT 'lector',
            created_at  timestamptz NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_product_barcodes_product_id
            ON catalog.product_barcodes (product_id);
    """)

    bind = op.get_bind()
    candidatos = bind.execute(text("""
        SELECT btrim(p.attributes->>'gtin') AS code, p.id, 'ficha' AS source
          FROM catalog.products p
         WHERE p.deleted_at IS NULL AND coalesce(p.attributes->>'gtin', '') <> ''
        UNION ALL
        SELECT btrim(m.sku_proveedor), m.product_id, 'xml'
          FROM purchasing.supplier_sku_map m
          JOIN catalog.products p ON p.id = m.product_id AND p.deleted_at IS NULL
         WHERE m.factor_pack = 1
    """)).all()

    # Un código que apunta a dos productos distintos es ambiguo: no se guarda.
    por_codigo: dict[str, set] = {}
    origen: dict[str, str] = {}
    for code, product_id, source in candidatos:
        if es_gtin_unidad(code):
            por_codigo.setdefault(code, set()).add(product_id)
            origen.setdefault(code, source)
    for code, productos in por_codigo.items():
        if len(productos) == 1:
            bind.execute(
                text("""
                    INSERT INTO catalog.product_barcodes (code, product_id, source)
                    VALUES (:c, :p, :s) ON CONFLICT (code) DO NOTHING
                """),
                {"c": code, "p": next(iter(productos)), "s": origen[code]},
            )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS catalog.product_barcodes")
