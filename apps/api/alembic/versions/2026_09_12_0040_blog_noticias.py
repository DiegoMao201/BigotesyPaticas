"""Campos de noticia en los artículos del blog.

Las landings de "Noticias de interés" reutilizan content.blog_posts con
category='noticias' en vez de una tabla paralela: así heredan el sitemap, el
aviso a IndexNow, el RSS y todo el SEO que ya funciona. Lo único que les falta
es de dónde salió la noticia y el video vertical que ya armamos para las redes.

La fuente NO es decorativa: es lo que separa informar de desinformar, que es la
regla que puso Diego para todo el motor de noticias.
"""
from alembic import op

revision = "0040_blog_noticias"
down_revision = "0039_story_youtube"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE content.blog_posts
            ADD COLUMN IF NOT EXISTS source_url  text,
            ADD COLUMN IF NOT EXISTS source_name varchar(120),
            ADD COLUMN IF NOT EXISTS video_url   text,
            ADD COLUMN IF NOT EXISTS story_id    uuid;
        CREATE INDEX IF NOT EXISTS ix_blog_posts_categoria_fecha
            ON content.blog_posts (category, published_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS content.ix_blog_posts_categoria_fecha;
        ALTER TABLE content.blog_posts
            DROP COLUMN IF EXISTS source_url,
            DROP COLUMN IF EXISTS source_name,
            DROP COLUMN IF EXISTS video_url,
            DROP COLUMN IF EXISTS story_id;
    """)
