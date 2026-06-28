"""sprint6a: content engine — schema content.*

Revision ID: 0017_content_engine
Revises: 0016_sprint5_reviews_gbp
Create Date: 2026-06-28
"""
from __future__ import annotations
from alembic import op

revision = "0017_content_engine"
down_revision = "0016_sprint5_reviews_gbp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE SCHEMA IF NOT EXISTS content;

        -- Templates de posts (12 tipos editoriales)
        CREATE TABLE IF NOT EXISTS content.post_templates (
            id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code            VARCHAR(80) UNIQUE NOT NULL,
            name            VARCHAR(200) NOT NULL,
            category        VARCHAR(50) NOT NULL,
            visual_style    VARCHAR(50) NOT NULL,
            visual_prompt_template TEXT NOT NULL,
            caption_template       TEXT NOT NULL,
            hashtags_pool   TEXT[]  DEFAULT ARRAY[]::TEXT[],
            cta_type        VARCHAR(50),
            active          BOOLEAN DEFAULT true,
            created_at      TIMESTAMP DEFAULT now()
        );

        -- Posts programados / publicados
        CREATE TABLE IF NOT EXISTS content.scheduled_posts (
            id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            template_id         UUID REFERENCES content.post_templates(id),
            category            VARCHAR(50) NOT NULL,

            -- Source data
            source_product_id      UUID REFERENCES catalog.products(id),
            source_review_id       UUID REFERENCES catalog.product_reviews(id),
            source_gbp_review_id   UUID REFERENCES catalog.gbp_reviews_cache(id),
            source_data            JSONB,

            -- Contenido generado
            visual_prompt   TEXT NOT NULL,
            caption         TEXT NOT NULL,
            hashtags        TEXT[]  DEFAULT ARRAY[]::TEXT[],
            cta_url         TEXT,
            image_url       TEXT,
            image_local_path TEXT,

            -- Programación
            scheduled_at        TIMESTAMP NOT NULL,
            optimal_time_slot   VARCHAR(20),
            target_platforms    VARCHAR(20)[] DEFAULT ARRAY['instagram','facebook']::VARCHAR(20)[],

            -- Workflow
            status              VARCHAR(20) NOT NULL DEFAULT 'pending_approval',
            approved_by         UUID,
            approved_at         TIMESTAMP,
            rejected_reason     TEXT,
            edited_by_admin     BOOLEAN DEFAULT false,

            -- Resultado publicación
            published_at        TIMESTAMP,
            instagram_post_id   VARCHAR(100),
            facebook_post_id    VARCHAR(100),
            publish_error       TEXT,
            dry_run             BOOLEAN DEFAULT false,

            -- Métricas (Sprint 6B)
            metrics             JSONB,
            last_metrics_update TIMESTAMP,

            created_at  TIMESTAMP DEFAULT now(),
            updated_at  TIMESTAMP DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_scheduled_status
            ON content.scheduled_posts(status, scheduled_at);
        CREATE INDEX IF NOT EXISTS idx_scheduled_publish
            ON content.scheduled_posts(scheduled_at)
            WHERE status = 'approved';

        -- Library de assets reutilizables
        CREATE TABLE IF NOT EXISTS content.assets_library (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            asset_type  VARCHAR(50) NOT NULL,
            name        VARCHAR(200),
            url         TEXT NOT NULL,
            local_path  TEXT,
            tags        TEXT[] DEFAULT ARRAY[]::TEXT[],
            used_count  INTEGER DEFAULT 0,
            last_used_at TIMESTAMP,
            created_at  TIMESTAMP DEFAULT now()
        );

        -- Horarios óptimos por día de semana
        CREATE TABLE IF NOT EXISTS content.optimal_time_slots (
            id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            day_of_week      INTEGER NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
            slot_name        VARCHAR(20) NOT NULL,
            hour             INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
            minute           INTEGER DEFAULT 0,
            engagement_score DECIMAL(4,2) DEFAULT 0,
            last_updated_at  TIMESTAMP DEFAULT now()
        );

        -- L-V: 7:30, 12:30, 19:00 / Sáb: 9:00, 13:00, 18:00 / Dom: 10:00, 15:00, 19:00
        INSERT INTO content.optimal_time_slots (day_of_week, slot_name, hour, minute) VALUES
            (1,'morning',7,30),(1,'lunch',12,30),(1,'evening',19,0),
            (2,'morning',7,30),(2,'lunch',12,30),(2,'evening',19,0),
            (3,'morning',7,30),(3,'lunch',12,30),(3,'evening',19,0),
            (4,'morning',7,30),(4,'lunch',12,30),(4,'evening',19,0),
            (5,'morning',7,30),(5,'lunch',12,30),(5,'evening',19,0),
            (6,'morning',9,0),(6,'lunch',13,0),(6,'evening',18,0),
            (0,'morning',10,0),(0,'lunch',15,0),(0,'evening',19,0);

        -- Kill-switch global
        CREATE TABLE IF NOT EXISTS content.engine_config (
            key         VARCHAR(80) PRIMARY KEY,
            value       TEXT NOT NULL,
            description TEXT,
            updated_at  TIMESTAMP DEFAULT now()
        );

        INSERT INTO content.engine_config (key, value, description) VALUES
            ('is_active','false','Master switch: si false, NO publica ni genera nada'),
            ('dry_run_mode','true','Si true, genera todo pero NO publica en redes reales'),
            ('weekly_generation_enabled','true','Si false, el plan semanal NO se ejecuta'),
            ('max_posts_per_day','3','Cantidad máxima de posts por día'),
            ('approval_required','true','Si true, requiere aprobación manual'),
            ('whatsapp_notify_on_drafts','true','Notificar cuando hay drafts pending')
        ON CONFLICT (key) DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("""
        DROP TABLE IF EXISTS content.engine_config CASCADE;
        DROP TABLE IF EXISTS content.optimal_time_slots CASCADE;
        DROP TABLE IF EXISTS content.assets_library CASCADE;
        DROP TABLE IF EXISTS content.scheduled_posts CASCADE;
        DROP TABLE IF EXISTS content.post_templates CASCADE;
        DROP SCHEMA IF EXISTS content CASCADE;
    """)
