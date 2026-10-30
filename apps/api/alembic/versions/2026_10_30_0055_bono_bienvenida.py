"""Bono de bienvenida PRIMERAPATA: dónde queda escrito que se usó (30-oct-2026).

Diego: *"una persona se registró y le llegó el bono al correo... yo ese bono
tendría que registrarlo en la venta para que el sistema admin le calcule el
descuento y que se diferencie claramente que es bono por registrarse"*.

El cupón salía en el correo del newsletter y nada más: la tabla de suscriptores
solo sabía cuándo se envió (`coupon_sent_at`). Tres columnas cierran el ciclo:
cuándo se canjeó, en qué venta y para qué cliente. Las reglas viven en
`app/services/bono_bienvenida.py`.
"""

from alembic import op

revision = "0055_bono_bienvenida"
down_revision = "0054_codigos_barras"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE crm.newsletter_subscribers
            ADD COLUMN IF NOT EXISTS coupon_redeemed_at timestamptz,
            ADD COLUMN IF NOT EXISTS coupon_order_id uuid
                REFERENCES sales.orders(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS coupon_customer_id uuid
                REFERENCES crm.customers(id) ON DELETE SET NULL;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE crm.newsletter_subscribers
            DROP COLUMN IF EXISTS coupon_redeemed_at,
            DROP COLUMN IF EXISTS coupon_order_id,
            DROP COLUMN IF EXISTS coupon_customer_id;
    """)
