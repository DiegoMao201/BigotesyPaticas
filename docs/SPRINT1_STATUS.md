# Continuidad — Sprint 1 (Fases 1-5)

## Estado al cierre de esta sesión (2026-05-10)

### Commits empujados a `main`
- `acf0048` — Sprint 0 hardening Streamlit (sesión anterior)
- `97d0487` — Fase 1+2+3: monorepo + infra docker + FastAPI backend completo
- _(este commit)_ — Fase 4+5: Admin Panel + Storefront + docs Coolify

### Lo que está funcionando
- ✅ Streamlit producción intacto
- ✅ `bp_common/` con 88 tests golden (bit-exact con legacy)
- ✅ FastAPI backend operativo: 5 routers, RBAC, auth JWT, ventas atómicas con lock pesimista
- ✅ Migración Alembic inicial con 14 tablas en 7 schemas
- ✅ Seed CLI: superadmin + 5 roles + StockLocation MAIN
- ✅ Dockerfile multi-stage para API
- ✅ Admin Panel Next.js 14: login, dashboard, products list, sales list, settings (light/dark)
- ✅ Storefront Next.js 14: home premium, categorías, PDP, carrito persistente Zustand, checkout placeholder
- ✅ Docker Compose dev local (PG16 + Redis7 + MinIO + Mailhog)
- ✅ Docs `COOLIFY_DEPLOY.md` con plan operativo completo

### Verificaciones operativas ejecutadas
- 5/5 tests smoke API pasando (hash bcrypt, JWT, settings, normalización pago, app start)
- `from app.main import app` carga sin errores (23 rutas)
- Estructura monorepo válida (pnpm workspaces + turbo)

### Pendiente para próxima sesión

#### Inmediato (operativo)
1. **Crear proyecto en Coolify** siguiendo `docs/COOLIFY_DEPLOY.md`. Recursos:
   - PG16 + Redis7 + (opcional MinIO)
   - API (Dockerfile)
   - Admin (Nixpacks Next.js)
   - Storefront (Nixpacks Next.js)
2. **Configurar DNS** de los 3 subdominios
3. **Configurar webhooks GitHub** para auto-deploy

#### ETL Sheets → PG
4. `scripts/etl_sheets_to_pg.py` con mapeo de cada tab a su modelo PG, idempotente vía `ops.legacy_id_map`
5. Activar dual-write controlado por flags en `bp_common.flags`

#### Tests + observabilidad
6. Tests E2E API contra PG real (pytest-asyncio + testcontainers)
7. Sentry / OpenTelemetry en API + Next.js
8. Métricas Prometheus opcionales

#### Features admin avanzadas
9. CRUD producto completo (drawer con validaciones, upload imágenes a S3)
10. Vista inventario con kardex y ajustes
11. CRM con segmentos RFM
12. Reportes y dashboards en `/analytics`

#### Features tienda avanzadas
13. Búsqueda con filtros (precio, marca, atributos)
14. Pasarela de pago real (Wompi / Mercado Pago)
15. Cuenta de cliente (registro/login + historial)
16. Blog con MDX

### Decisiones arquitectónicas confirmadas (no revisitar)
- Monorepo: pnpm + Turborepo + TypeScript estricto
- Backend: FastAPI + SQLAlchemy 2 async + Alembic + PG16 con schemas por bounded context
- Frontend: Next.js 14 App Router + Tailwind 3 + Zustand + TanStack Query + shadcn-style UI
- Deploy: Coolify single-server + Let's Encrypt + webhooks GitHub
- Coexistencia: Streamlit POS sigue activo en paralelo, ETL bidireccional → cutover controlado por flags
- Storage: PG para datos relacionales, S3/Spaces para assets, Redis para cache/sessions

### Variables de entorno de producción a generar (NO commitear)
- `JWT_SECRET` (32 bytes hex)
- `ADMIN_PASSWORD` (fuerte)
- `SESSION_SECRET` admin (32 bytes hex)
- `S3_ACCESS_KEY` + `S3_SECRET_KEY`
- Pass de Postgres y Redis (Coolify los genera)

Guardar en `project-secrets/.env.production` (gitignored) y replicar como ENV en Coolify.

### Comandos útiles

```bash
# Levantar stack local
make infra-up

# Migraciones
cd apps/api && alembic upgrade head

# Seed
cd apps/api && python -m app.cli.seed

# Servir API local
cd apps/api && uvicorn app.main:app --reload

# Tests API smoke
cd apps/api && PYTHONPATH=. pytest tests/test_smoke.py -v

# Admin dev
cd apps/admin && pnpm install && pnpm dev   # :3001

# Store dev
cd apps/store && pnpm install && pnpm dev   # :3000
```
