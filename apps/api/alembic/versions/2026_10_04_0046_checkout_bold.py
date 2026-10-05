"""Checkout con Bold: el pedido web puede llegar YA PAGADO (4-oct-2026).

Diego: "habilitamos la pasarela de pago Bold con API, webhooks y toda la tecnología
posible y links de pagos propios con una plataforma clara y confiable".

POR QUÉ ESTO EXTIENDE `portal_orders` Y NO CREA UNA TABLA NUEVA
El encargo original pedía `portal.web_orders` + `portal.web_order_items` aparte. Se
descartó al mirar el repo: desde el 2-oct los pedidos de la tienda YA entran a
`portal.portal_orders` con `origen='web'` (migración 0044), y de ahí cuelga todo lo
que ya funciona — `bridge_to_sales()`, `credit_loyalty_points()`,
`process_referral_reward()`, las notificaciones y la vista del admin en pet-monitor.
Una tabla paralela obligaría a duplicar esas cinco cosas y a arreglar cada bug en dos
sitios. Diego aprobó extender el 4-oct.

Así que el pago es un ESTADO MÁS del pedido que ya existe, no un pedido distinto.

LA CONVENCIÓN ES MINÚSCULA, no la del encargo. `payment_method` ya existe en la tabla
y en producción vale `cash`, `transfer` o `nequi`. Se le suma `bold`, en minúscula,
para no partir el vocabulario en dos.

POR QUÉ `bold_amount` ES UN ENTERO Y NO UN `numeric`
Es el monto EXACTO que se firmó y se le mandó a Bold: pesos enteros, sin decimales ni
separadores (76000, nunca 76.000 ni 76000.00). Se guarda aparte de `total_amount`
—que es el numeric de siempre— porque es el valor contra el que se compara lo que
devuelve el webhook. Si se recalculara desde el numeric al validar, un redondeo
distinto haría fallar la comparación y rechazaríamos un pago bueno.

`bold_payment_id UNIQUE` en las dos tablas es lo que hace imposible acreditar dos
veces el mismo pago: Bold reintenta el webhook hasta 5 veces (15 min, 1 h, 4 h, 8 h,
24 h) y los reintentos SON parte del funcionamiento normal, no un error.
"""
from alembic import op

revision = "0046_checkout_bold"
down_revision = "0045_citas_google"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE portal.portal_orders
            ADD COLUMN IF NOT EXISTS order_reference     varchar(60),
            ADD COLUMN IF NOT EXISTS payment_status      varchar(20),
            ADD COLUMN IF NOT EXISTS bold_amount         bigint,
            ADD COLUMN IF NOT EXISTS bold_payment_id     text,
            ADD COLUMN IF NOT EXISTS paid_at             timestamptz,
            ADD COLUMN IF NOT EXISTS payment_expires_at  timestamptz;

        -- La referencia es lo que viaja a Bold como orderId y vuelve en el webhook:
        -- tiene que ser única o no se puede saber a qué pedido pertenece un pago.
        CREATE UNIQUE INDEX IF NOT EXISTS ux_portal_orders_order_reference
            ON portal.portal_orders (order_reference)
            WHERE order_reference IS NOT NULL;

        -- Un pago de Bold acredita UN pedido. El índice es el candado real contra
        -- los reintentos del webhook; el código que compruebe antes es una cortesía.
        CREATE UNIQUE INDEX IF NOT EXISTS ux_portal_orders_bold_payment_id
            ON portal.portal_orders (bold_payment_id)
            WHERE bold_payment_id IS NOT NULL;

        -- Para la conciliación: busca pendientes vencidos cada 10 minutos.
        CREATE INDEX IF NOT EXISTS ix_portal_orders_payment_pending
            ON portal.portal_orders (payment_status, payment_expires_at)
            WHERE payment_status = 'pending';
    """)

    op.execute("""
        -- Bitácora de TODO lo que llega de Bold, válido o no. Sirve para tres cosas:
        -- idempotencia (el UNIQUE), auditoría de discrepancias de monto, y poder
        -- depurar una firma que no cuadra sin tener que reproducir el pago.
        CREATE TABLE IF NOT EXISTS portal.payment_events (
            id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            bold_payment_id   text        NOT NULL,
            event_type        varchar(40) NOT NULL,
            order_reference   varchar(60),
            raw_payload       jsonb       NOT NULL,
            -- false = firma inválida. La fila se guarda IGUAL: un intento fallido es
            -- justo lo que hay que poder revisar después.
            signature_valid   boolean     NOT NULL DEFAULT false,
            amount            bigint,
            -- Se llena cuando el evento termina de procesarse. NULL con
            -- signature_valid=true significa que algo se quedó a medias.
            processed_at      timestamptz,
            -- Qué impidió procesarlo: discrepancia de monto, pedido inexistente…
            error             text,
            received_at       timestamptz NOT NULL DEFAULT now()
        );

        -- EL candado de idempotencia. Con esto, procesar cinco veces el mismo pago
        -- deja exactamente un pedido, una fila en sales, unos puntos y un aviso:
        -- el INSERT ... ON CONFLICT DO NOTHING no inserta, y el proceso sale.
        -- Resiste incluso dos reintentos simultáneos, que es donde falla cualquier
        -- comprobación hecha a mano antes del insert.
        CREATE UNIQUE INDEX IF NOT EXISTS ux_payment_events_bold_payment_id
            ON portal.payment_events (bold_payment_id);

        CREATE INDEX IF NOT EXISTS ix_payment_events_order_reference
            ON portal.payment_events (order_reference);

        CREATE INDEX IF NOT EXISTS ix_payment_events_sin_procesar
            ON portal.payment_events (received_at)
            WHERE processed_at IS NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS portal.payment_events;

        DROP INDEX IF EXISTS portal.ix_portal_orders_payment_pending;
        DROP INDEX IF EXISTS portal.ux_portal_orders_bold_payment_id;
        DROP INDEX IF EXISTS portal.ux_portal_orders_order_reference;

        ALTER TABLE portal.portal_orders
            DROP COLUMN IF EXISTS payment_expires_at,
            DROP COLUMN IF EXISTS paid_at,
            DROP COLUMN IF EXISTS bold_payment_id,
            DROP COLUMN IF EXISTS bold_amount,
            DROP COLUMN IF EXISTS payment_status,
            DROP COLUMN IF EXISTS order_reference;
    """)
