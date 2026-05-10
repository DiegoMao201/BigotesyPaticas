# DATABASE_STRATEGY.md

## 1. ELECCIÓN

**PostgreSQL 16** como base de datos primaria.
- JSONB nativo para datos semi-estructurados (`pets`, `items_payload` legacy).
- Full-Text Search (`tsvector`) para buscador de productos y clientes.
- Particionado declarativo (para `sales` y `stock_movements` por mes).
- Extensiones: `pg_trgm` (fuzzy match SKUs), `pgcrypto` (UUID + hashing), `citext` (cédulas/emails case-insensitive), `uuid-ossp`.

---

## 2. CONVENCIONES

- `snake_case` en tablas y columnas.
- PK siempre `id BIGINT GENERATED ALWAYS AS IDENTITY` o `UUID DEFAULT gen_random_uuid()` cuando se necesita exposición pública.
- Toda tabla incluye `created_at TIMESTAMPTZ DEFAULT now()`, `updated_at TIMESTAMPTZ DEFAULT now()`, `created_by UUID NULL`, `updated_by UUID NULL`.
- Soft-delete vía `deleted_at TIMESTAMPTZ NULL` (índice parcial `WHERE deleted_at IS NULL`).
- Timestamps siempre `TIMESTAMPTZ` en UTC. Conversión a `America/Bogota` en la capa API.
- Dinero: `NUMERIC(14,2)` (no `FLOAT`). Para COP que hoy es entero, se almacena con 2 decimales por compatibilidad futura.
- Booleans con default explícito.

---

## 3. ESQUEMAS LÓGICOS

```
identity     -> users, roles, permissions, role_permissions, user_roles, sessions, audit_log
catalog      -> categories, products, product_variants, product_images, suppliers, supplier_products, taxes
inventory    -> warehouses, stock_levels, stock_movements, physical_counts, count_lines
customers    -> customers, pets, customer_addresses, customer_tags
pos          -> sales, sale_items, payments, cash_closures, sale_status_history
purchasing   -> purchase_orders, po_items, po_receipts, expenses, expense_categories
finance      -> accounts_receivable, ar_payments, kpi_snapshots
loyalty      -> campaigns, campaign_targets, messages, message_events
ecommerce    -> carts, cart_items, online_orders, shipments, addresses
ops          -> feature_flags, etl_runs, reconciliation_reports
```

---

## 4. TABLAS NÚCLEO (esquema v1, abreviado)

```sql
-- catalog.products
CREATE TABLE catalog.products (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  legacy_uid      TEXT UNIQUE,                -- ex Producto_UID
  sku             TEXT NOT NULL,              -- ex ID_Producto
  sku_norm        TEXT NOT NULL,              -- ex ID_Producto_Norm
  name            TEXT NOT NULL,
  category_id     UUID REFERENCES catalog.categories(id),
  cost            NUMERIC(14,2) NOT NULL DEFAULT 0,
  price           NUMERIC(14,2) NOT NULL DEFAULT 0,
  tax_rate        NUMERIC(5,2)  NOT NULL DEFAULT 0,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  search_tsv      tsvector GENERATED ALWAYS AS (
                    to_tsvector('spanish', coalesce(name,'') || ' ' || coalesce(sku,''))
                  ) STORED,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
  deleted_at      TIMESTAMPTZ
);
CREATE UNIQUE INDEX ON catalog.products (sku_norm) WHERE deleted_at IS NULL;
CREATE INDEX        ON catalog.products USING GIN (search_tsv);
CREATE INDEX        ON catalog.products USING GIN (sku gin_trgm_ops);

-- inventory.stock_levels
CREATE TABLE inventory.stock_levels (
  product_id   UUID NOT NULL REFERENCES catalog.products(id),
  warehouse_id UUID NOT NULL REFERENCES inventory.warehouses(id),
  qty          NUMERIC(14,3) NOT NULL DEFAULT 0,
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (product_id, warehouse_id)
);

-- inventory.stock_movements (particionada por mes)
CREATE TABLE inventory.stock_movements (
  id            BIGINT GENERATED ALWAYS AS IDENTITY,
  product_id    UUID NOT NULL REFERENCES catalog.products(id),
  warehouse_id  UUID NOT NULL REFERENCES inventory.warehouses(id),
  delta         NUMERIC(14,3) NOT NULL,
  reason        TEXT NOT NULL,                -- 'sale' | 'purchase' | 'adjustment' | 'count'
  ref_table     TEXT,
  ref_id        UUID,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by    UUID
) PARTITION BY RANGE (created_at);

-- pos.sales
CREATE TABLE pos.sales (
  id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  legacy_id          TEXT UNIQUE,             -- ex ID_Venta
  customer_id        UUID REFERENCES customers.customers(id),
  channel            TEXT NOT NULL DEFAULT 'pos',  -- pos|online
  delivery_type      TEXT,
  shipping_address   TEXT,
  shipping_status    TEXT,
  payment_method     TEXT,
  bank_destination   TEXT,
  total              NUMERIC(14,2) NOT NULL,
  cost_total         NUMERIC(14,2) NOT NULL DEFAULT 0,
  payment_status     TEXT NOT NULL DEFAULT 'pending', -- paid|pending|partial
  amount_paid        NUMERIC(14,2) NOT NULL DEFAULT 0,
  amount_due         NUMERIC(14,2) NOT NULL DEFAULT 0,
  promised_pay_date  DATE,
  notes              TEXT,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  created_by         UUID
) PARTITION BY RANGE (created_at);

CREATE TABLE pos.sale_items (
  sale_id        UUID NOT NULL REFERENCES pos.sales(id) ON DELETE CASCADE,
  line_no        INT  NOT NULL,
  product_id     UUID NOT NULL REFERENCES catalog.products(id),
  qty            NUMERIC(14,3) NOT NULL,
  unit_price     NUMERIC(14,2) NOT NULL,
  unit_discount  NUMERIC(14,2) NOT NULL DEFAULT 0,
  line_subtotal  NUMERIC(14,2) NOT NULL,
  PRIMARY KEY (sale_id, line_no)
);
```

> El esquema completo se materializará en migraciones Alembic en `apps/api/alembic/versions/` durante F1.

---

## 5. ATOMICIDAD CRÍTICA

### Caso: registrar venta
Toda venta se ejecuta en **una sola transacción**:

```sql
BEGIN;
  INSERT INTO pos.sales (...) RETURNING id;
  INSERT INTO pos.sale_items (...);              -- bulk
  INSERT INTO inventory.stock_movements (...);   -- delta negativo por item
  UPDATE inventory.stock_levels                  -- usando upsert
     SET qty = qty - :delta
   WHERE (product_id, warehouse_id) = (:p, :w);
  INSERT INTO pos.payments (...);                -- si hubo abono
COMMIT;
```

- Lock optimista: `UPDATE ... WHERE qty >= :delta` para evitar stock negativo.
- Si falla cualquier paso → `ROLLBACK`. Cliente no recibe confirmación.

---

## 6. ESTRATEGIA DE MIGRACIÓN DE DATOS

### 6.1 Mapping Sheets → tablas

| Sheet | Tabla destino | Notas |
|-------|----------------|-------|
| Inventario | `catalog.products` + `inventory.stock_levels` | `Stock` se separa de la ficha del producto |
| Clientes | `customers.customers` + `customers.pets` | `Info_Mascotas` JSON se desnormaliza |
| Ventas | `pos.sales` + `pos.sale_items` + `pos.payments` | `Items_JSON` desnormalizado |
| Gastos | `purchasing.expenses` | 1:1 |
| Cierres | `pos.cash_closures` | 1:1 |
| Maestro_Proveedores | `catalog.suppliers` + `catalog.supplier_products` | join por `SKU_Interno` |
| Historial_Ordenes | `purchasing.purchase_orders` + `purchasing.po_items` | parsea `Items_JSON` |

### 6.2 Tabla puente
```sql
CREATE TABLE ops.legacy_id_map (
  entity      TEXT NOT NULL,        -- 'product','sale','customer',...
  legacy_id   TEXT NOT NULL,
  new_id      UUID NOT NULL,
  migrated_at TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (entity, legacy_id)
);
```
Permite convivencia con Streamlit y rollbacks.

### 6.3 ETL
- Worker Python (`apps/etl/`) usa `gspread` (read-only) + `psycopg`/`SQLAlchemy`.
- Idempotente vía `UPSERT` (`ON CONFLICT (legacy_id) DO UPDATE`).
- Corre en intervalos configurables; logs estructurados; métricas Prometheus.
- Reconciliación: hash MD5 por fila + conteos.

---

## 7. RENDIMIENTO

- Índices: por FK, por `created_at`, por `sku_norm`, por `customer_id`, por `payment_status`.
- Particionado por mes en `sales` y `stock_movements`.
- Vistas materializadas para dashboards (`finance.kpi_daily`, `loyalty.rfm_snapshot`) refrescadas por job nocturno.
- `pgbouncer` en transaction pooling para FastAPI.

---

## 8. SEGURIDAD

- Roles: `app_rw` (FastAPI), `app_ro` (read-only para ETL inverso/BI), `migrator` (Alembic), `admin`.
- `REVOKE ALL` por defecto y `GRANT` por esquema/tabla.
- Row-Level Security preparado para multi-tenant futuro (no activado en v1).
- Cifrado en reposo a nivel de volumen (Coolify).
- Backups: `pg_basebackup` + WAL archiving a S3/MinIO. Retención 30 días + snapshot mensual 1 año.
- Restore probado mensualmente en entorno staging (RTO objetivo < 1h, RPO < 15 min).

---

## 9. AUDITORÍA

```sql
CREATE TABLE identity.audit_log (
  id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  actor_id    UUID,
  actor_role  TEXT,
  entity      TEXT NOT NULL,
  entity_id   TEXT,
  action      TEXT NOT NULL,        -- create|update|delete|login|export
  diff        JSONB,
  ip          INET,
  user_agent  TEXT,
  created_at  TIMESTAMPTZ DEFAULT now()
);
```

Triggers `AFTER INSERT/UPDATE/DELETE` en tablas críticas escriben el diff en `audit_log`.

---

## 10. ESTRATEGIA DE MIGRACIONES

- Alembic en `apps/api/alembic/`.
- Política: una migración por PR; revisada por par; ejecutada en CI/CD vía `alembic upgrade head` antes del deploy.
- Migraciones siempre **forward-compatible** (pasos en dos releases si requieren rename: add → backfill → switch → drop).
