"""portal.agenda_bloqueos: días u horas en que la peluquería no atiende (29-sep-2026).

Diego: "bloquear días de agendamiento porque de pronto el groomer no está, se va de
vacaciones, se enfermó… el portal y la web no tendrán disponibles esos días o esas
horas". Un bloqueo es un rango [inicio, fin); la web y el portal no ofrecen horas que se
crucen con él. El admin SÍ puede agendar o mover citas encima (lo decide él).
"""
from alembic import op

revision = "0043_agenda_bloqueos"
down_revision = "0042_suppliers_audit_texto"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS portal.agenda_bloqueos (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            inicio timestamptz NOT NULL,
            fin timestamptz NOT NULL,
            motivo varchar(200),
            created_by varchar(100),
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now(),
            CONSTRAINT ck_agenda_bloqueos_rango CHECK (fin > inicio)
        );
        CREATE INDEX IF NOT EXISTS ix_agenda_bloqueos_rango ON portal.agenda_bloqueos (inicio, fin);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS portal.agenda_bloqueos;")
