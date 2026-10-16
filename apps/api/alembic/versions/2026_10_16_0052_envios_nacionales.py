"""Envíos nacionales por transportadora con Envia.com (16-oct-2026).

Diego: *"quiero que hagas la integración total con esa API para hacer envíos fuera
de mi cobertura local que es Pereira y Dosquebradas [...] el cliente mira cuánto le
cuesta el envío y lo paga de una vez [...] aprobamos la venta y así se genera la
guía que le llega al cliente"*.

Hasta hoy un pedido con dirección en Bogotá entraba, pero NO se podía cobrar: el
checkout lo mandaba a WhatsApp a "coordinar el envío". Ahora el pedido sabe de qué
tipo es y, si es nacional, lleva el destino estructurado (ciudad con código DANE,
departamento, código postal) que exige la transportadora, y la cotización que el
cliente vio y pagó.

DOS COSAS, CADA UNA EN SU SITIO:

- **En `portal.portal_orders`** va lo que decide el cobro: `shipping_mode`
  ('local' o 'national'), el destino que escribió el cliente y la tarifa que
  eligió. Eso se congela al crear el pedido, porque es contra lo que se firmó el
  monto de Bold.
- **En `portal.shipments`** va cada guía generada ante Envia. Es una tabla aparte
  porque una guía se puede cancelar (Envia devuelve el saldo si la transportadora
  no la ha recogido) y volver a generar, y ese historial no cabe en una columna.
"""

from alembic import op

revision = "0052_envios_nacionales"
down_revision = "0051_nomina"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS shipping_mode     varchar(20),
            ADD COLUMN IF NOT EXISTS shipping_destination jsonb,
            ADD COLUMN IF NOT EXISTS shipping_quote    jsonb;

        CREATE INDEX IF NOT EXISTS ix_portal_orders_shipping_mode
            ON portal.portal_orders (shipping_mode)
            WHERE shipping_mode = 'national';

        CREATE TABLE IF NOT EXISTS portal.shipments (
            id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            portal_order_id  uuid NOT NULL REFERENCES portal.portal_orders(id) ON DELETE CASCADE,
            carrier          varchar(40)  NOT NULL,
            service          varchar(40)  NOT NULL,
            service_name     varchar(120),
            -- Lo que cobró Envia por la guía (puede diferir de lo cotizado si pasó tiempo).
            label_cost       numeric(12,2),
            currency         varchar(5) NOT NULL DEFAULT 'COP',
            envia_shipment_id bigint,
            tracking_number  varchar(80),
            track_url        text,
            label_url        text,
            -- Estado según Envia ('Created', 'Picked Up', 'In transit', 'Delivered'…).
            status           varchar(60),
            status_at        timestamptz,
            events           jsonb,
            pickup_number    varchar(80),
            pickup_date      date,
            pickup_window    varchar(20),
            cancelled_at     timestamptz,
            refunded_amount  numeric(12,2),
            packages         jsonb,
            raw_generate     jsonb,
            created_at       timestamptz NOT NULL DEFAULT now(),
            created_by       varchar(120)
        );
        CREATE INDEX IF NOT EXISTS ix_shipments_order ON portal.shipments (portal_order_id);
        CREATE INDEX IF NOT EXISTS ix_shipments_tracking ON portal.shipments (tracking_number);
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS portal.shipments;
        DROP INDEX IF EXISTS portal.ix_portal_orders_shipping_mode;
        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS shipping_mode,
            DROP COLUMN IF EXISTS shipping_destination,
            DROP COLUMN IF EXISTS shipping_quote;
    """)
