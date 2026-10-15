"""Nómina: empleados, parámetros legales y pagos de quincena (15-oct-2026).

Diego: *"yo estaba colocando un gasto como nómina y listo, pero ahora necesito que
sea una página más donde se lleve el control de pagos de nómina, que le envíe el
desprendible al empleado con los descuentos legales [...] un botón que diga pagar
nómina quincena y eso haga todo el ejercicio interno contable hacia los gastos"*.

TRES TABLAS, UNA RESPONSABILIDAD CADA UNA:

- **`finance.employees`**: quién trabaja, con qué cargo, desde cuándo y con qué
  salario. Si `salario_base` va vacío, el empleado gana el mínimo vigente y sube
  solo cuando cambie el parámetro en enero.
- **`finance.payroll_params`**: el salario mínimo y el auxilio de transporte con
  su fecha de vigencia. Viven en la base y no en el código para que el cambio de
  año sea un registro nuevo, no un despliegue.
- **`finance.payrolls`**: cada quincena PAGADA, con todos los números congelados
  tal como se liquidaron (devengado, deducciones, neto y provisión de
  prestaciones). El desprendible se vuelve a generar desde estas cifras, así que
  nunca cambia aunque cambie el salario después.

El pago de una quincena crea DOS gastos en `finance.expenses`: el neto consignado
(categoría Nómina) y la provisión de prestaciones sociales (cesantías, intereses,
prima y vacaciones), que Diego pidió registrar como gasto *"para tener claridad
de todo"*. Las dos filas quedan enlazadas desde el pago.

DE PASO: desde el 5-oct el botón de "nuevo gasto" seguía escribiendo en el JSON
viejo (`ops.legacy_id_map`) y no en `finance.expenses`, así que esos gastos no
contaban en el punto de equilibrio. Esta migración vuelve a correr el traspaso
(idempotente por `legacy_id`) para recoger los que se quedaron atrás, y el código
pasa a escribir y leer solo de la tabla propia.
"""

from alembic import op

revision = "0051_nomina"
down_revision = "0050_pago_a_varias_ventas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS finance.employees (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            nombre          varchar(160) NOT NULL,
            documento       varchar(30)  NOT NULL UNIQUE,
            email           varchar(160),
            cargo           varchar(80)  NOT NULL DEFAULT 'Auxiliar',
            fecha_ingreso   date         NOT NULL,
            fecha_retiro    date,
            -- NULL = gana el mínimo vigente según finance.payroll_params.
            salario_base    numeric(14,2),
            aux_transporte  numeric(14,2),
            tipo_contrato   varchar(40)  NOT NULL DEFAULT 'indefinido',
            activo          boolean      NOT NULL DEFAULT true,
            notas           text,
            contrato_enviado_at timestamptz,
            contrato_enviado_a  varchar(160),
            created_at      timestamptz  NOT NULL DEFAULT now(),
            updated_at      timestamptz  NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS finance.payroll_params (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            vigencia_desde  date         NOT NULL UNIQUE,
            smmlv           numeric(14,2) NOT NULL CHECK (smmlv > 0),
            aux_transporte  numeric(14,2) NOT NULL CHECK (aux_transporte >= 0),
            pct_salud       numeric(5,2)  NOT NULL DEFAULT 4,
            pct_pension     numeric(5,2)  NOT NULL DEFAULT 4,
            fuente          text,
            created_at      timestamptz  NOT NULL DEFAULT now()
        );

        CREATE TABLE IF NOT EXISTS finance.payrolls (
            id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            consecutivo     integer      NOT NULL UNIQUE,
            employee_id     uuid         NOT NULL REFERENCES finance.employees(id),
            periodo_inicio  date         NOT NULL,
            periodo_fin     date         NOT NULL,
            quincena        smallint     NOT NULL CHECK (quincena IN (1, 2)),
            dias_trabajados integer      NOT NULL CHECK (dias_trabajados BETWEEN 0 AND 15),
            -- Snapshot mensual con el que se liquidó.
            salario_base    numeric(14,2) NOT NULL,
            aux_base        numeric(14,2) NOT NULL,
            pct_salud       numeric(5,2)  NOT NULL,
            pct_pension     numeric(5,2)  NOT NULL,
            -- Devengado
            dev_salario     numeric(14,2) NOT NULL,
            dev_auxilio     numeric(14,2) NOT NULL,
            otros_devengados numeric(14,2) NOT NULL DEFAULT 0,
            total_devengado numeric(14,2) NOT NULL,
            -- Deducciones
            ded_salud       numeric(14,2) NOT NULL,
            ded_pension     numeric(14,2) NOT NULL,
            otros_descuentos numeric(14,2) NOT NULL DEFAULT 0,
            descripcion_otros text,
            total_deducciones numeric(14,2) NOT NULL,
            neto            numeric(14,2) NOT NULL,
            -- Provisión de prestaciones sociales de esta quincena
            prov_cesantias  numeric(14,2) NOT NULL DEFAULT 0,
            prov_intereses  numeric(14,2) NOT NULL DEFAULT 0,
            prov_prima      numeric(14,2) NOT NULL DEFAULT 0,
            prov_vacaciones numeric(14,2) NOT NULL DEFAULT 0,
            total_provision numeric(14,2) NOT NULL DEFAULT 0,
            -- Pago
            estado          varchar(20)  NOT NULL DEFAULT 'pagada',
            fecha_pago      date         NOT NULL,
            pagada_at       timestamptz  NOT NULL DEFAULT now(),
            pagada_por      varchar(160),
            metodo_pago     varchar(40)  NOT NULL DEFAULT 'Transferencia',
            banco_origen    varchar(60),
            expense_id      uuid REFERENCES finance.expenses(id),
            provision_expense_id uuid REFERENCES finance.expenses(id),
            -- Desprendible por correo
            email_enviado_a varchar(160),
            email_enviado_at timestamptz,
            email_error     text,
            created_at      timestamptz  NOT NULL DEFAULT now(),
            UNIQUE (employee_id, periodo_inicio)
        );
        CREATE INDEX IF NOT EXISTS ix_payrolls_employee ON finance.payrolls (employee_id, periodo_inicio DESC);
        CREATE SEQUENCE IF NOT EXISTS finance.payrolls_consecutivo_seq START 1;
    """)

    # ── Parámetros 2026 (decretos 1469 y 1470 de 2025; sostenido por el 0159 de 2026) ──
    op.execute("""
        INSERT INTO finance.payroll_params (vigencia_desde, smmlv, aux_transporte, pct_salud, pct_pension, fuente)
        VALUES ('2026-01-01', 1750905, 249095, 4, 4,
                'Decretos 1469 y 1470 del 29-dic-2025; Decreto 0159 del 19-feb-2026')
        ON CONFLICT (vigencia_desde) DO NOTHING;
    """)

    # ── Mario: domiciliario desde el 1-oct-2026, gana el mínimo (salario_base NULL) ──
    op.execute("""
        INSERT INTO finance.employees (nombre, documento, email, cargo, fecha_ingreso, tipo_contrato)
        VALUES ('Mario Hernan Mojica Ibarra', '1088247868', 'mhmojica2013@gmail.com',
                'Domiciliario', '2026-10-01', 'indefinido')
        ON CONFLICT (documento) DO NOTHING;
    """)

    # ── Gastos creados después del 5-oct que se quedaron en el JSON viejo ──
    op.execute("""
        INSERT INTO finance.expenses
            (fecha, monto, categoria, tipo, descripcion, metodo_pago, banco_origen,
             es_fijo, created_by, legacy_id, created_at)
        SELECT
            (l.extra->>'fecha')::date,
            round((l.extra->>'monto')::numeric, 2),
            coalesce(nullif(trim(l.extra->>'categoria'), ''), 'Sin categoría'),
            coalesce(nullif(trim(l.extra->>'tipo'), ''), 'Operativo'),
            nullif(trim(l.extra->>'descripcion'), ''),
            nullif(trim(l.extra->>'metodo_pago'), ''),
            nullif(trim(l.extra->>'banco_origen'), ''),
            (
                lower(coalesce(l.extra->>'categoria','')) IN ('arriendo','nómina','nomina','servicios')
                OR lower(coalesce(l.extra->>'descripcion','')) ~ '(arrend|arrien|nomina|nómina|servicios|energia|energía|acueducto|internet|credito|crédito)'
            ),
            nullif(trim(l.extra->>'created_by'), ''),
            l.legacy_id,
            l.created_at
        FROM ops.legacy_id_map l
        WHERE l.entity = 'gasto'
          AND l.extra->>'fecha' IS NOT NULL
          AND l.extra->>'fecha' <> ''
          AND (l.extra->>'monto') ~ '^[0-9]+(\\.[0-9]+)?$'
        ON CONFLICT (legacy_id) WHERE legacy_id IS NOT NULL DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS finance.payrolls;
        DROP SEQUENCE IF EXISTS finance.payrolls_consecutivo_seq;
        DROP TABLE IF EXISTS finance.payroll_params;
        DROP TABLE IF EXISTS finance.employees;
    """)
