"""Citas de peluquería: huella de Google y candado del purchase.

Diego (2-oct-2026): "y las citas de baño mejor dicho necesito que google nos vea como
la mejor tienda de mascotas de la zona".

La reserva ya se reportaba a Google como `generate_lead` desde el navegador. Lo que
faltaba es la plata: cuando el admin completa la cita y escribe cuánto cobró, eso es una
venta real y se le cuenta a Google como `purchase`. Para que la venta quede atribuida a
la búsqueda o al anuncio que trajo al cliente hay que guardar el client_id de la cookie
_ga de esa visita — igual que en los pedidos de la tienda (migración 0044).

`price` ya existía en la tabla (nullable) y nada la llenaba; ahora sí.

Revision ID: 0045_citas_google
Revises: 0044_pedidos_web_google
"""

from alembic import op

revision = "0045_citas_google"
down_revision = "0044_pedidos_web_google"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE portal.appointments
            ADD COLUMN IF NOT EXISTS origen           varchar(30),
            ADD COLUMN IF NOT EXISTS ga_client_id     varchar(64),
            ADD COLUMN IF NOT EXISTS ga_session_id    varchar(32),
            ADD COLUMN IF NOT EXISTS gclid            text,
            ADD COLUMN IF NOT EXISTS purchase_sent_at timestamptz;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE portal.appointments
            DROP COLUMN IF EXISTS origen,
            DROP COLUMN IF EXISTS ga_client_id,
            DROP COLUMN IF EXISTS ga_session_id,
            DROP COLUMN IF EXISTS gclid,
            DROP COLUMN IF EXISTS purchase_sent_at;
        """
    )
