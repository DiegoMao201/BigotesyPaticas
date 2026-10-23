"""Candado: un producto sin precio o sin foto no se puede publicar (23-oct-2026).

Diego: *"no se publica productos con [precio] 0 eso daña mi feed y como google y
merchant me ven y tampoco se publica sin foto"*.

24 productos (Chunky, Nutra Nuggets, Agility 15k) llevaban publicados en $0 desde
el lote del 19-20 de julio: la tienda los mostraba como "$ 0 Agotado". Nunca
tuvieron precio (el conteo de mayo ya los traía en 0).

El candado va en la base y no en un endpoint porque a `is_published` se escribe
desde muchos lados: el admin, la importación de Excel, el ETL y los scripts. Un
trigger los cubre a todos, y además despublica solo un producto que pierda el
precio o la foto después de publicado.
"""

from alembic import op

revision = "0053_candado_publicar"
down_revision = "0052_envios_nacionales"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION catalog.candado_publicar() RETURNS trigger AS $$
        BEGIN
            IF NEW.is_published
               AND (NEW.price <= 0 OR coalesce(NEW.primary_image_url, '') = '') THEN
                NEW.is_published := false;
            END IF;
            RETURN NEW;
        END $$ LANGUAGE plpgsql;

        DROP TRIGGER IF EXISTS trg_candado_publicar ON catalog.products;
        CREATE TRIGGER trg_candado_publicar
            BEFORE INSERT OR UPDATE ON catalog.products
            FOR EACH ROW EXECUTE FUNCTION catalog.candado_publicar();

        UPDATE catalog.products SET is_published = false
         WHERE is_published AND (price <= 0 OR coalesce(primary_image_url, '') = '');
    """)


def downgrade() -> None:
    op.execute("""
        DROP TRIGGER IF EXISTS trg_candado_publicar ON catalog.products;
        DROP FUNCTION IF EXISTS catalog.candado_publicar();
    """)
