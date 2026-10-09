"""Un pago puede cubrir VARIAS ventas ya facturadas (9-oct-2026).

Diego: *"puede ser una o dos ventas o muchas ventas un solo pago; yo pueda
asignarle las ventas ya registradas correspondientes, por lo que son pagos sin
pedido"*.

POR QUÉ UNA TABLA Y NO UNA COLUMNA
`portal_orders.sales_order_id` solo apunta a UNA venta. Serviría para el caso simple
y se rompería en el que Diego describe: alguien que debe tres facturas y las paga de
un giro. Una columna más con una lista dentro tampoco sirve —habría que leerla entera
para responder *"¿qué pago cubrió esta venta?"*, que es justo la pregunta que se hace
cuando llega un contracargo.

Con una fila por (pago, venta) se puede mirar desde los dos lados y, además, **queda
escrito cuánto se le abonó a cada una**: un pago de $500.000 repartido entre tres
facturas no es lo mismo que tres pagos de $500.000.

El UNIQUE impide aplicar dos veces el mismo pago a la misma venta, que es como se
cobraría dos veces sin que nadie lo note.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0050_pago_a_varias_ventas"
down_revision = "0049_antifraude_bold"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        #: El cobro (un `portal_orders` de origen 'libre' o 'link': plata sin pedido).
        sa.Column("portal_order_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        #: La venta ya facturada a la que se le aplica.
        sa.Column("sales_order_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        #: Lo que se le abonó AHORA a esa venta. Puede ser 0 cuando la venta ya estaba
        #: cobrada y lo único que se agrega es la trazabilidad del pago.
        sa.Column("amount", sa.BigInteger(), nullable=False, server_default="0"),
        #: El pago de `sales.payments` que se creó o se anotó, si hubo alguno.
        sa.Column("sales_payment_id", postgresql.UUID(as_uuid=True), nullable=True),
        #: GA4 se marca POR VENTA, no por pago: si el pago cubre tres facturas son
        #: tres transacciones distintas para Google, y aplicarlas en dos tandas no
        #: puede dejar fuera a las de la segunda.
        sa.Column("purchase_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(150), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("portal_order_id", "sales_order_id", name="uq_pago_venta"),
        sa.CheckConstraint("amount >= 0", name="ck_pago_venta_monto"),
        schema="portal",
    )


def downgrade() -> None:
    op.drop_table("payment_applications", schema="portal")
