"""Liquidación final de un empleado al terminar el contrato (17-nov-2026).

Una fila por empleado retirado, con las cifras congeladas (cesantías, intereses,
prima, vacaciones) y el ajuste de la provisión que se venía registrando como
gasto en cada quincena. El pago en sí no es un gasto nuevo: ya estaba provisionado.
"""

from alembic import op

revision = "0057_liquidacion_final"
down_revision = "0056_correo_satisfaccion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS finance.payroll_settlements (
            id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consecutivo integer NOT NULL UNIQUE,
            employee_id uuid NOT NULL UNIQUE REFERENCES finance.employees(id),
            fecha_retiro date NOT NULL,
            fecha_documento date NOT NULL,
            motivo varchar(40) NOT NULL,
            razon text,
            detalle jsonb NOT NULL,
            total numeric(14,2) NOT NULL,
            provision_acumulada numeric(14,2) NOT NULL,
            ajuste_provision numeric(14,2) NOT NULL DEFAULT 0,
            ajuste_expense_id uuid REFERENCES finance.expenses(id),
            metodo_pago varchar(40),
            fecha_pago date,
            registrada_por varchar(160),
            email_enviado_a varchar(160),
            email_enviado_at timestamptz,
            email_error text,
            created_at timestamptz NOT NULL DEFAULT now()
        );
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS finance.payroll_settlements;")
