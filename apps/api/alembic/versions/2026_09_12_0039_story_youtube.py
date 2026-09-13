"""Guarda el id de YouTube en cada pieza.

Sin esto el agente no sabe qué ya subió y volvería a subir lo mismo cada vez
que corre (YouTube tiene tope diario de subidas, así que reintenta al día
siguiente y necesita saber dónde quedó).
"""
from alembic import op

revision = "0039_story_youtube"
down_revision = "0038_noticias_radar"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content.story_posts
            ADD COLUMN IF NOT EXISTS youtube_video_id varchar(20),
            ADD COLUMN IF NOT EXISTS youtube_subido_en timestamptz;
        CREATE INDEX IF NOT EXISTS ix_story_posts_sin_youtube
            ON content.story_posts (status) WHERE youtube_video_id IS NULL;
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS content.ix_story_posts_sin_youtube;
        ALTER TABLE content.story_posts
            DROP COLUMN IF EXISTS youtube_video_id,
            DROP COLUMN IF EXISTS youtube_subido_en;
    """)
