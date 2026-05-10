-- Inicialización del cluster Postgres en local.
-- En producción: provisionar de la misma forma vía Coolify (one-shot).

CREATE EXTENSION IF NOT EXISTS pgcrypto;     -- gen_random_uuid
CREATE EXTENSION IF NOT EXISTS citext;        -- emails / sku case-insensitive
CREATE EXTENSION IF NOT EXISTS pg_trgm;       -- búsqueda fuzzy
CREATE EXTENSION IF NOT EXISTS unaccent;      -- normalización
CREATE EXTENSION IF NOT EXISTS btree_gin;

-- Schemas por bounded context (ver docs/DATABASE_STRATEGY.md)
CREATE SCHEMA IF NOT EXISTS catalog;          -- productos, categorías, marcas, variantes
CREATE SCHEMA IF NOT EXISTS inventory;        -- stocks, movimientos, lotes
CREATE SCHEMA IF NOT EXISTS sales;            -- órdenes, items, pagos
CREATE SCHEMA IF NOT EXISTS purchasing;       -- proveedores, órdenes de compra
CREATE SCHEMA IF NOT EXISTS crm;              -- clientes, RFM, loyalty
CREATE SCHEMA IF NOT EXISTS finance;          -- cierres, gastos, conciliación
CREATE SCHEMA IF NOT EXISTS auth;             -- usuarios, roles, permisos
CREATE SCHEMA IF NOT EXISTS ops;              -- legacy_id_map, audit_log, jobs
CREATE SCHEMA IF NOT EXISTS analytics;        -- vistas materializadas, agregados

-- Configuración del cluster (idempotente)
ALTER DATABASE bp_dev SET timezone TO 'America/Bogota';
ALTER DATABASE bp_dev SET search_path TO public, catalog, inventory, sales, purchasing, crm, finance, auth, ops, analytics;

-- Comentario de auditoría
COMMENT ON SCHEMA catalog IS 'Bounded context: catálogo (productos, categorías, marcas, variantes)';
COMMENT ON SCHEMA inventory IS 'Bounded context: inventario y movimientos';
COMMENT ON SCHEMA sales IS 'Bounded context: ventas y pagos';
COMMENT ON SCHEMA purchasing IS 'Bounded context: compras y proveedores';
COMMENT ON SCHEMA crm IS 'Bounded context: clientes, segmentación, lealtad';
COMMENT ON SCHEMA finance IS 'Bounded context: contabilidad operativa';
COMMENT ON SCHEMA auth IS 'Bounded context: identidad, roles, permisos';
COMMENT ON SCHEMA ops IS 'Cross-cutting: tabla puente legacy, audit, jobs, feature flags';
COMMENT ON SCHEMA analytics IS 'Vistas materializadas y agregados de reporting';
