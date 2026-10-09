"""Antifraude de los pagos con Bold (8-oct-2026).

Diego: *"hacen pagos por la web y a los 15 días piden reembolsos, o son tarjetas
clonadas… yo como comercio pierdo y eso afectaría demasiado la caja"*.

LO QUE BOLD **NO** DA, Y POR ESO HAY QUE CONSTRUIRLO
El webhook de Bold tiene exactamente cuatro eventos —`SALE_APPROVED`,
`SALE_REJECTED`, `VOID_APPROVED`, `VOID_REJECTED`— y **ninguno es de contracargo**.
Bold avisa de una disputa por fuera (correo), así que el sistema nunca se entera
solo. Y su manual de ventas no presenciales es explícito: *"tu negocio asumirá el
riesgo de fraude"*, con **2 días hábiles** para mandar soportes, débito automático
**dentro de los 3 días hábiles** siguientes al aviso, retención posible **hasta 120
días**, y un índice de fraude máximo tolerado del **2,5 %**.

De ahí salen las tres cosas que crea esta migración:

1. **Las señales dejan de perderse.** Bold ya manda `masked_pan`, `card_type`,
   `brand`, `payer_email`, `installments` e `integration` en cada evento, pero hoy
   mueren enterrados en `raw_payload` y no se pueden cruzar. Cruzarlos es justo lo
   que detecta "la misma tarjeta con tres clientes" o "tres tarjetas a una misma
   dirección", que son dos de las señales que el propio Bold lista.

2. **El expediente de entrega.** Hoy, al entregar, solo se guarda `delivered_at`.
   Bold dice que lo que gana una disputa son *"guías de envío, fotos del producto
   recibido por el cliente, soportes de entrega"*. Sin eso, la disputa está perdida
   antes de empezar: se pierde la plata Y la mercancía.

3. **El registro de contracargos**, que es lo único que permite saber si vamos por
   debajo o por encima de ese 2,5 % — el umbral con el que Bold puede empezar a
   retener saldos.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0049_antifraude_bold"
down_revision = "0048_gastos_tabla_propia"
branch_labels = None
depends_on = None

#: Lo que Bold manda en cada evento y hasta hoy se tiraba. Se guarda en columnas y no
#: en el JSON porque una señal que no se puede consultar con un WHERE no sirve para
#: detectar nada.
SENALES = [
    ("bold_payment_method", sa.String(30)),   # CARD / PSE / NEQUI / BANCOLOMBIA / ...
    ("bold_card_type", sa.String(20)),        # CREDIT / DEBIT — el riesgo vive en CREDIT
    ("bold_card_brand", sa.String(40)),
    ("bold_masked_pan", sa.String(25)),       # 477379******7365
    ("bold_payer_email", sa.String(160)),
    ("bold_integration", sa.String(20)),      # BUTTON (web) / POS (datáfono) / LINK
    ("bold_installments", sa.SmallInteger()),
    # La IP de quien hizo el pedido. Es evidencia en una disputa y delata al que pide
    # diez veces desde el mismo sitio con tarjetas distintas.
    ("client_ip", sa.String(45)),
]

#: El veredicto del motor de riesgo, escrito en el pedido para que el admin lo vea sin
#: recalcular nada y para poder medir después si el semáforo acierta.
RIESGO = [
    ("risk_level", sa.String(10)),            # bajo / medio / alto
    ("risk_score", sa.SmallInteger()),
    ("risk_flags", postgresql.JSONB()),       # las señales que se dispararon, con su texto
    ("risk_cleared_at", sa.DateTime(timezone=True)),
    ("risk_cleared_by", sa.String(120)),
    ("risk_cleared_note", sa.Text()),
]

#: Con qué se defiende una disputa. Vacío = disputa perdida.
ENTREGA = [
    ("delivered_to_name", sa.String(140)),
    ("delivered_to_doc", sa.String(40)),
    ("delivery_evidence_url", sa.Text()),
    ("delivery_notes", sa.Text()),
]

TIPOS = [
    "health_reminder", "order_update", "loyalty", "appointment", "birthday",
    "general", "new_order", "new_appointment", "new_customer", "order_confirmed",
    "order_ready", "order_delivered", "appt_confirmed", "appt_rescheduled",
    "appt_cancelled", "referral_signup", "referral_reward", "welcome_bonus",
    "order_invoiced", "sos_nearby", "sos_sighting", "sos_found", "web_order_paid",
    # Nuevos: un pago que huele mal, y un contracargo que ya llegó.
    "payment_risk", "chargeback",
]


def _candado(tipos: list[str]) -> None:
    lista = ", ".join(f"'{t}'" for t in tipos)
    op.execute("ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type;")
    op.execute(
        f"ALTER TABLE portal.notifications ADD CONSTRAINT ck_notif_type "
        f"CHECK (type::text = ANY (ARRAY[{lista}]::text[]));"
    )


def upgrade() -> None:
    for nombre, tipo in SENALES + RIESGO + ENTREGA:
        op.add_column("portal_orders", sa.Column(nombre, tipo, nullable=True), schema="portal")

    # Cruzar tarjetas y correos es la consulta central del motor de riesgo; sin índice
    # se vuelve lenta justo cuando haya volumen, que es cuando hace falta.
    op.create_index("ix_portal_orders_masked_pan", "portal_orders", ["bold_masked_pan"],
                    schema="portal", postgresql_where=sa.text("bold_masked_pan IS NOT NULL"))
    op.create_index("ix_portal_orders_payer_email", "portal_orders", ["bold_payer_email"],
                    schema="portal", postgresql_where=sa.text("bold_payer_email IS NOT NULL"))
    op.create_index("ix_portal_orders_risk_level", "portal_orders", ["risk_level"],
                    schema="portal", postgresql_where=sa.text("risk_level IS NOT NULL"))

    op.create_table(
        "chargebacks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_reference", sa.String(60), nullable=True, index=True),
        sa.Column("bold_payment_id", sa.Text(), nullable=True),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        # El motivo tal como lo da Bold o el banco. Texto libre a propósito: la lista
        # de motivos la ponen las franquicias y cambia; encasillarla ahora obligaría a
        # migrar la tabla la primera vez que llegue uno que no habíamos previsto.
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=False),
        # 2 días hábiles desde el aviso. Se guarda calculado porque es la fecha que de
        # verdad importa: pasada, no hay nada que hacer.
        sa.Column("evidence_due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        # pendiente / ganado / perdido
        sa.Column("outcome", sa.String(20), nullable=False, server_default="pendiente"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.CheckConstraint("outcome IN ('pendiente','ganado','perdido')", name="ck_chargeback_outcome"),
        sa.CheckConstraint("amount > 0", name="ck_chargeback_amount"),
        schema="portal",
    )

    _candado(TIPOS)


def downgrade() -> None:
    op.execute("DELETE FROM portal.notifications WHERE type IN ('payment_risk','chargeback');")
    _candado([t for t in TIPOS if t not in ("payment_risk", "chargeback")])
    op.drop_table("chargebacks", schema="portal")
    for idx in ("ix_portal_orders_risk_level", "ix_portal_orders_payer_email",
                "ix_portal_orders_masked_pan"):
        op.drop_index(idx, table_name="portal_orders", schema="portal")
    for nombre, _ in SENALES + RIESGO + ENTREGA:
        op.drop_column("portal_orders", nombre, schema="portal")
