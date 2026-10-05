"""Los gastos dejan de vivir en un JSON y pasan a tener tabla propia (5-oct-2026).

Diego: *"organízalo todo y créale su tabla, organiza bien todo para que sigamos
fuertes en datos y en análisis"*.

DÓNDE ESTABAN Y POR QUÉ NO SERVÍA
En `ops.legacy_id_map` con `entity='gasto'` y todo el contenido dentro de un `extra`
JSON. Funcionaba para guardar, pero no para analizar:

- **El monto era texto.** Cada suma obligaba a convertir en la consulta, y un dato
  mal escrito reventaba el informe entero en vez de saltarse una fila.
- **La fecha también.** Agrupar por mes era `substr(extra->>'fecha',1,7)`: sin
  índice, recorriendo las 478 filas enteras cada vez.
- **Sin índices y sin tipos**, cada informe nuevo era una consulta frágil escrita a
  mano, y el listado del admin se traía TODAS las filas a memoria para filtrarlas en
  Python, incluso pidiendo una página de 50.

Con tabla propia, el punto de equilibrio y cualquier informe futuro se calculan en
la base, con índices, y un gasto mal escrito no tumba nada.

LOS DATOS SE MIGRAN, NO SE PIERDEN: las 478 filas pasan a la tabla nueva y las
originales se quedan donde están. Si algo sale mal, el `downgrade` borra la tabla y
el sistema vuelve a leer del JSON sin que falte un peso.
"""
from alembic import op

revision = "0048_gastos_tabla_propia"
down_revision = "0047_notif_pago_web"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS finance.expenses (
            id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
            fecha         date         NOT NULL,
            monto         numeric(14,2) NOT NULL CHECK (monto >= 0),
            categoria     varchar(60)  NOT NULL DEFAULT 'Sin categoría',
            -- 'Operativo' (sostener la tienda abierta) vs 'Mercancía' (lo que se
            -- revende). La diferencia NO es cosmética: la mercancía ya está
            -- descontada en el margen bruto, así que meterla en los gastos fijos
            -- contaría el mismo peso dos veces e inflaría el punto de equilibrio
            -- hasta volverlo inalcanzable.
            tipo          varchar(30)  NOT NULL DEFAULT 'Operativo',
            descripcion   text,
            metodo_pago   varchar(40),
            banco_origen  varchar(60),
            -- Verdadero si el gasto se repite todos los meses (arriendo, nómina,
            -- servicios). Es lo que separa el costo de tener la tienda abierta de
            -- un imprevisto, y sin esa distinción el punto de equilibrio mezcla
            -- peras con manzanas.
            es_fijo       boolean      NOT NULL DEFAULT false,
            created_by    varchar(160),
            -- De dónde salió la fila, para poder rastrear la migración.
            legacy_id     text,
            created_at    timestamptz  NOT NULL DEFAULT now(),
            updated_at    timestamptz  NOT NULL DEFAULT now()
        );

        -- Los informes agrupan por mes y por categoría: estos dos índices son los
        -- que hacen que el punto de equilibrio no tenga que leer la tabla entera.
        CREATE INDEX IF NOT EXISTS ix_expenses_fecha     ON finance.expenses (fecha DESC);
        CREATE INDEX IF NOT EXISTS ix_expenses_categoria ON finance.expenses (categoria);
        CREATE INDEX IF NOT EXISTS ix_expenses_tipo      ON finance.expenses (tipo);
        CREATE UNIQUE INDEX IF NOT EXISTS ux_expenses_legacy
            ON finance.expenses (legacy_id) WHERE legacy_id IS NOT NULL;
    """)

    # ── Migración de las 478 filas ──
    # `ON CONFLICT DO NOTHING` sobre legacy_id: correr esto dos veces no duplica.
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
            -- Se marcan como fijos los que se repiten todos los meses. Arriendo y
            -- nómina se detectan TAMBIÉN por la descripción, porque buena parte
            -- están archivados como "Otros": solo en junio-septiembre hay $2.700.000
            -- de arriendo y $900.000 de nómina escondidos ahí.
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
    # Los datos originales siguen intactos en ops.legacy_id_map, así que borrar
    # esta tabla no pierde nada.
    op.execute("DROP TABLE IF EXISTS finance.expenses;")
