"""Permitir el aviso 'web_order_paid' en portal.notifications (5-oct-2026).

`portal.notifications.type` tiene un CHECK con la lista cerrada de avisos válidos.
Al confirmarse el primer pago real con Bold, la inserción reventó con
`CheckViolationError: ck_notif_type` y el aviso nunca llegó al panel: el pago se
registraba bien y Diego no se enteraba.

Costó tres intentos encontrarlo porque el fallo era INVISIBLE. La notificación se
escribía dentro de una sesión que ya venía de otros commits y la excepción no
llegaba a ningún log; solo apareció al darle sesión propia y un tope de tiempo.

Un aviso de pago merece tipo propio y no reutilizar 'new_order': un pedido PAGADO no
es lo mismo que un pedido que entra, y el panel tiene que poder distinguirlos para
darle prioridad al que ya tiene el dinero.
"""
from alembic import op

revision = "0047_notif_pago_web"
down_revision = "0046_checkout_bold"
branch_labels = None
depends_on = None

TIPOS = [
    "health_reminder", "order_update", "loyalty", "appointment", "birthday",
    "general", "new_order", "new_appointment", "new_customer", "order_confirmed",
    "order_ready", "order_delivered", "appt_confirmed", "appt_rescheduled",
    "appt_cancelled", "referral_signup", "referral_reward", "welcome_bonus",
    "order_invoiced", "sos_nearby", "sos_sighting", "sos_found",
    # Nuevo: pago en línea confirmado, de la tienda web o del portal.
    "web_order_paid",
]


def _aplicar(tipos: list[str]) -> None:
    lista = ", ".join(f"'{t}'" for t in tipos)
    op.execute("ALTER TABLE portal.notifications DROP CONSTRAINT IF EXISTS ck_notif_type;")
    op.execute(
        f"ALTER TABLE portal.notifications ADD CONSTRAINT ck_notif_type "
        f"CHECK (type::text = ANY (ARRAY[{lista}]::text[]));"
    )


def upgrade() -> None:
    _aplicar(TIPOS)


def downgrade() -> None:
    # Al revertir hay que quitar primero las filas del tipo nuevo, o el CHECK no se
    # puede volver a crear y la bajada falla a medias.
    op.execute("DELETE FROM portal.notifications WHERE type = 'web_order_paid';")
    _aplicar([t for t in TIPOS if t != "web_order_paid"])
