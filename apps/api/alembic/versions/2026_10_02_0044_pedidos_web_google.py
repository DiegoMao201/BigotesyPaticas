"""Pedidos de la tienda web: quedan registrados y se le cuentan a Google (2-oct-2026).

Diego: "esos pedidos llegan al admin y yo les hago el proceso como a un pedido del
portal y cuando le doy completado le decimos a google fue una compra real".

Hasta hoy el checkout de la tienda solo armaba el enlace de WhatsApp: el pedido no
quedaba en ninguna tabla y Google nunca supo que la página vendía (GA4: 0 compras,
0 checkouts, con 10 carritos y 42 fichas vistas en 7 días).

Tres columnas:
  origen          de dónde entró el pedido ('web' = tienda pública, NULL = portal).
  ga_client_id    el id de la cookie _ga de ESA visita. Sin él GA4 registra la compra
                  como "(direct)" y no le da el crédito a la búsqueda ni al anuncio
                  que trajo al cliente — que es justo lo que queremos medir.
  ga_session_id   la sesión de esa misma visita (cookie _ga_G-K46540SJVJ). Con ella la
                  compra se pega a la sesión exacta, no solo al usuario.
  gclid           el clic de Google Ads, cuando el cliente llegó por un anuncio. Hoy se
                  guarda nada más: GA4 atribuye por client_id. Sirve para importar
                  conversiones a Google Ads más adelante.
  purchase_sent_at  candado de idempotencia: el purchase se manda UNA vez por pedido.
"""
from alembic import op

revision = "0044_pedidos_web_google"
down_revision = "0043_agenda_bloqueos"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS origen           varchar(30),
            ADD COLUMN IF NOT EXISTS ga_client_id     varchar(64),
            ADD COLUMN IF NOT EXISTS ga_session_id    varchar(32),
            ADD COLUMN IF NOT EXISTS gclid            text,
            ADD COLUMN IF NOT EXISTS purchase_sent_at timestamptz;

        CREATE INDEX IF NOT EXISTS ix_portal_orders_origen
            ON portal.portal_orders (origen)
            WHERE origen IS NOT NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS portal.ix_portal_orders_origen;
        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS origen,
            DROP COLUMN IF EXISTS ga_client_id,
            DROP COLUMN IF EXISTS ga_session_id,
            DROP COLUMN IF EXISTS gclid,
            DROP COLUMN IF EXISTS purchase_sent_at;
    """)
