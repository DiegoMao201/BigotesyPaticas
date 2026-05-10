# API_STRATEGY.md

## 1. STACK
- **FastAPI** (Python 3.12) — async, OpenAPI 3.1 nativo, type-hints.
- **Pydantic v2** — schemas y validación.
- **SQLAlchemy 2 + Alembic** — ORM + migraciones.
- **Uvicorn + Gunicorn** detrás de Coolify.
- **PostgreSQL** primario, **Redis** para cache + colas (RQ).
- **OpenTelemetry** para tracing.

## 2. ESTRUCTURA DEL PROYECTO

```
apps/api/
├── pyproject.toml
├── alembic/
│   ├── versions/
│   └── env.py
├── src/
│   └── bp_api/
│       ├── main.py
│       ├── core/
│       │   ├── config.py
│       │   ├── security.py        # JWT, hashing, RBAC deps
│       │   ├── db.py
│       │   ├── cache.py
│       │   ├── logging.py
│       │   ├── feature_flags.py
│       │   └── errors.py
│       ├── modules/
│       │   ├── identity/
│       │   │   ├── router.py
│       │   │   ├── service.py
│       │   │   ├── schemas.py
│       │   │   └── models.py
│       │   ├── catalog/
│       │   ├── inventory/
│       │   ├── customers/
│       │   ├── pos/
│       │   ├── purchasing/
│       │   ├── finance/
│       │   ├── loyalty/
│       │   └── ecommerce/
│       ├── integrations/
│       │   ├── google_sheets.py   # adapter ETL
│       │   ├── whatsapp.py
│       │   └── payments/
│       └── workers/
│           ├── etl_sheets.py
│           ├── reconciliation.py
│           └── reorder.py
└── tests/
    ├── unit/
    └── integration/
```

## 3. CONVENCIONES REST

- Versionado por path: `/api/v1/...`.
- Recursos en plural: `/products`, `/sales`, `/customers/{id}/pets`.
- Filtros vía query: `?status=paid&from=2026-01-01&page=1&page_size=50`.
- Paginación cursor-based en endpoints high-volume (`/sales`, `/stock_movements`).
- Errores con `application/problem+json` (RFC 7807).
- IDs en path/body siempre UUID. Para retro-compatibilidad se aceptan `legacy_id` vía `?legacy=true`.

## 4. AUTENTICACIÓN Y AUTORIZACIÓN

- **Login** `POST /api/v1/auth/login` → cookies `access_token` (15 min) + `refresh_token` (7 días) httpOnly + Secure + SameSite=Lax.
- **Refresh** `POST /api/v1/auth/refresh`.
- **Logout** invalida refresh en Redis.
- **RBAC** declarativo:
  ```python
  @router.post("/sales", dependencies=[Depends(require("pos:sale:create"))])
  ```
- Roles iniciales: `admin`, `manager`, `cashier`, `purchaser`, `viewer`, `customer` (storefront).
- Permisos en formato `dominio:recurso:acción`.
- Audit log automático vía middleware (request_id, actor, ip, ruta, status, latencia).

## 5. ENDPOINTS BASE (v1, recorte)

| Método | Path | Descripción | Permiso |
|--------|------|-------------|---------|
| POST   | /auth/login | Login | público |
| POST   | /auth/refresh | Refrescar token | autenticado |
| GET    | /products | Listar productos | catalog:product:read |
| POST   | /products | Crear producto | catalog:product:write |
| PATCH  | /products/{id} | Actualizar | catalog:product:write |
| GET    | /products/{id}/stock | Stock por bodega | inventory:stock:read |
| POST   | /sales | Registrar venta (transaccional) | pos:sale:create |
| GET    | /sales | Listar ventas | pos:sale:read |
| POST   | /sales/{id}/payments | Registrar abono | pos:payment:create |
| POST   | /purchases | Crear orden de compra | purchasing:po:create |
| POST   | /purchases/{id}/receive | Recibir mercancía | purchasing:po:receive |
| POST   | /expenses | Registrar gasto | finance:expense:create |
| POST   | /cash_closures | Cierre diario | finance:closure:create |
| GET    | /customers | Listar / buscar | customers:read |
| POST   | /customers | Crear | customers:write |
| GET    | /loyalty/segments | RFM | loyalty:read |
| POST   | /loyalty/campaigns | Crear campaña | loyalty:write |
| GET    | /storefront/products | Catálogo público | público |
| POST   | /storefront/cart | Crear/actualizar carrito | público |
| POST   | /storefront/checkout | Cerrar compra | público |

## 6. CONTRATOS

- OpenAPI 3.1 publicado en `/api/v1/openapi.json`.
- Tipos compartidos generados al frontend con `openapi-typescript` en `packages/shared/api-types`.
- SDK opcional generado con `openapi-fetch` para Next.js.

## 7. RESILIENCIA

- Idempotency-Key en endpoints de escritura (`POST /sales`, `POST /payments`) — clave única en Redis 24h.
- Rate limiting por IP y por usuario (`slowapi` o `nginx`/`coolify`).
- Circuit breakers para integraciones externas (WhatsApp, pasarela de pago).
- Reintentos con backoff exponencial.

## 8. WORKERS

| Worker | Frecuencia | Propósito |
|--------|------------|-----------|
| `etl_sheets_to_pg` | cada 5 min (F2) | Espejo Sheets → Postgres |
| `etl_pg_to_sheets` | cada 5 min (F3) | Dual-write asíncrono opcional |
| `reconciliation_daily` | 04:00 COT | Comparar Sheets vs PG, alertas |
| `reorder_engine` | 06:00 COT | Recalcular sugerencias de compra |
| `loyalty_campaign_dispatcher` | bajo demanda | Generar mensajes WhatsApp |
| `pdf_invoice_async` | bajo demanda | Generar PDFs grandes en background |
| `kpi_snapshot` | 23:55 COT | Snapshot diario de KPIs financieros |

## 9. OBSERVABILIDAD

- `request_id` propagado vía header `X-Request-ID`.
- Logs JSON con `loguru`/`structlog` → Loki.
- Métricas Prometheus en `/metrics` (latencia, RPS, errores, jobs en cola).
- Tracing OTel exportado a Tempo/Jaeger.
- Alertas mínimas: 5xx > 1%/5min, p95 latencia > 1s, jobs failing > 3 consecutivos, reconciliation_diff > 0.

## 10. TESTING

- `pytest` + `pytest-asyncio`.
- Test DB efímera con `pytest-postgresql` + transacciones rollback por test.
- Cobertura mínima objetivo: 80% en `services` de cada módulo.
- Contract tests sobre OpenAPI con `schemathesis`.
- Carga: `k6` smoke en CI, `locust` para escenarios reales antes de cutover de POS.
