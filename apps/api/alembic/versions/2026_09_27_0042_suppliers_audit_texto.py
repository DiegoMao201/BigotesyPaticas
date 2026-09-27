"""purchasing.suppliers.created_by/updated_by: uuid → texto, como en TODAS las demás tablas.

La migración 0003 los creó como uuid, pero el modelo (AuditMixin) los declara
String(100) y la API les manda el id del usuario como texto. PostgreSQL respondía
"column created_by is of type uuid but expression is of type character varying" y
NINGÚN proveedor nuevo se podía guardar, ni desde Proveedores ni desde la carga por
XML (Diego, 27-sep-2026). Los valores uuid existentes se conservan como texto.
"""
from alembic import op

revision = "0042_suppliers_audit_texto"
down_revision = "0041_facturas_correo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE purchasing.suppliers
            ALTER COLUMN created_by TYPE varchar(100) USING created_by::text,
            ALTER COLUMN updated_by TYPE varchar(100) USING updated_by::text;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE purchasing.suppliers
            ALTER COLUMN created_by TYPE uuid USING NULLIF(created_by, '')::uuid,
            ALTER COLUMN updated_by TYPE uuid USING NULLIF(updated_by, '')::uuid;
    """)
