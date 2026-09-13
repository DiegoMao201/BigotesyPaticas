"""Radar de noticias: qué vio el motor y qué ya se usó.

Sin esta tabla el radar repetiría noticias entre corridas y entre despliegues.
"""
from alembic import op
import sqlalchemy as sa

revision = "0038_noticias_radar"
down_revision = "0037_community_resolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS content.noticias_radar (
            huella        varchar(16) PRIMARY KEY,
            titulo        text        NOT NULL,
            medio         varchar(80),
            url           text,
            fecha_noticia timestamptz,
            puntaje       int         NOT NULL DEFAULT 0,
            escalon       varchar(20),
            cuerpo_chars  int         NOT NULL DEFAULT 0,
            estado        varchar(20) NOT NULL DEFAULT 'detectada',
            motivo        text,
            story_id      uuid,
            vista_en      timestamptz NOT NULL DEFAULT now(),
            usada_en      timestamptz
        );
        CREATE INDEX IF NOT EXISTS ix_noticias_radar_estado
            ON content.noticias_radar (estado, puntaje DESC);
        CREATE INDEX IF NOT EXISTS ix_noticias_radar_vista
            ON content.noticias_radar (vista_en DESC);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS content.noticias_radar;")
