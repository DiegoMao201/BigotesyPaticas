"""Correo de satisfacción y enlace de pago enviado por el admin (1-nov-2026).

Diego: *"le envié el nuevo link de pago y el pedido desapareció de pedidos en el
admin"* y *"necesitamos enviarle el correo de satisfacción... que nos califique
en Google y que nos califique los productos"*.

- `link_enviado_por_admin_at`: el admin mandó un enlace de pago sobre un pedido
  que ya existía (contraentrega o transferencia). El listado esconde los pedidos
  con pago en línea pendiente (intención de compra), pero este no es una
  intención: es un pedido real esperando que el cliente pague por PSE.
- `satisfaction_email_sent_at`: candado para mandar el correo de agradecimiento
  una sola vez por pedido.
"""

from alembic import op

revision = "0056_correo_satisfaccion"
down_revision = "0055_bono_bienvenida"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS link_enviado_por_admin_at timestamptz,
            ADD COLUMN IF NOT EXISTS satisfaction_email_sent_at timestamptz;
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS link_enviado_por_admin_at,
            DROP COLUMN IF EXISTS satisfaction_email_sent_at;
    """)
