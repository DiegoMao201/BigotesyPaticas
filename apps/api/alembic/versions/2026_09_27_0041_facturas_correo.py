"""Bandeja de facturas que llegan al correo de Bigotes.

Diego (27-sep-2026): "automatizamos la lectura de esos XML, los cargamos al admin en
una pestaña adicional de compras y el usuario revisa que todo esté bien, le dice cargar
y sigue el proceso de ingreso normal". Aquí queda cada documento DIAN leído del correo
(solo lectura, gmail.readonly) hasta que alguien lo carga o lo descarta. Nada se ingresa
solo: el paso "Cargar" abre el mismo flujo de revisión que la carga manual del XML.

estado: pendiente | cargada | ya_ingresada | descartada | otros
  - ya_ingresada: el número de factura de ese NIT ya existía en compras (se cargó a mano)
  - otros: no es mercancía (p. ej. tiquetes aéreos que llegan al mismo correo)
"""
from alembic import op

revision = "0041_facturas_correo"
down_revision = "0040_blog_noticias"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS purchasing.inbox_invoices (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            gmail_message_id varchar(64)  NOT NULL UNIQUE,
            cufe             varchar(128) UNIQUE,
            doc_type         varchar(4)   NOT NULL,          -- 01 factura · 91 nota crédito · 92 nota débito
            nit              varchar(20)  NOT NULL,
            supplier_name    varchar(200) NOT NULL,
            folio            varchar(80),
            issue_date       date,
            subtotal         numeric(14,2),
            tax_amount       numeric(14,2),
            total            numeric(14,2),
            xml              bytea        NOT NULL,
            email_date       timestamptz,
            estado           varchar(20)  NOT NULL DEFAULT 'pendiente',
            purchase_id      uuid,
            nota             text,
            created_at       timestamptz  NOT NULL DEFAULT now(),
            updated_at       timestamptz  NOT NULL DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS ix_inbox_invoices_estado ON purchasing.inbox_invoices (estado, issue_date DESC);
        CREATE INDEX IF NOT EXISTS ix_inbox_invoices_nit_folio ON purchasing.inbox_invoices (nit, folio);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS purchasing.inbox_invoices;")
