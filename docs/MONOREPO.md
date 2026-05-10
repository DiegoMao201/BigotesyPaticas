# Bigotes y Paticas — Monorepo

Plataforma empresarial premium para una marca de mascotas:
**E-commerce + Admin (ERP/POS) + API + Streamlit legacy**, conviviendo bajo el patrón Strangler Fig.

## Estructura

```
apps/
  api/              FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2
  admin/            Next.js 14 (App Router) — admin.bigotesypaticas.com
  store/            Next.js 14 (App Router) — bigotesypaticas.com
  legacy-streamlit/ Stub apuntando a la app raíz (NO mover archivos)

packages/
  shared/           Tipos TypeScript compartidos (generados desde OpenAPI)
  ui/               (futuro) componentes shadcn compartidos
  config/           (futuro) ESLint / TS / Tailwind base configs

infrastructure/
  docker/           docker-compose.yml + Dockerfiles
  coolify/          Manifests / instrucciones de despliegue
  monitoring/       (futuro) Grafana / Loki / OTel collector
  backups/          Scripts adicionales de backup

bp_common/          Lib Python compartida (ya existente, opt-in para Streamlit)
scripts/            Scripts operativos (backup, ETL, seed, etc.)
docs/               Estrategia + bitácora viva
tests/              pytest (golden + unit)
```

## Quick start (desarrollo local)

Requisitos: Docker Desktop, Node 20+, pnpm 9+, Python 3.11+.

```bash
# 1. Levantar infra (Postgres 16 + Redis + MinIO + Mailhog)
make infra-up

# 2. Backend
make api-dev

# 3. Admin panel
make admin-dev

# 4. Storefront
make store-dev

# 5. Streamlit legacy (sigue funcionando exactamente igual)
make streamlit-dev
```

Servicios locales:
- Storefront: http://localhost:3000
- Admin: http://localhost:3100
- API: http://localhost:8000 (docs en `/docs`)
- Postgres: localhost:5432 (`bp_dev` / `postgres` / `devpass`)
- Redis: localhost:6379
- MinIO: http://localhost:9001 (`minioadmin` / `minioadmin`)
- Mailhog: http://localhost:8025
- Streamlit: http://localhost:8501

## Producción

Ver [docs/DEVOPS_STRATEGY.md](DEVOPS_STRATEGY.md) y `infrastructure/coolify/`.

## Documentación clave

- [docs/MIGRATION_MASTER_PLAN.md](MIGRATION_MASTER_PLAN.md)
- [docs/ARCHITECTURE_ANALYSIS.md](ARCHITECTURE_ANALYSIS.md)
- [docs/DATABASE_STRATEGY.md](DATABASE_STRATEGY.md)
- [docs/API_STRATEGY.md](API_STRATEGY.md)
- [docs/FRONTEND_STRATEGY.md](FRONTEND_STRATEGY.md)
- [docs/project-continuity.md](project-continuity.md) — bitácora viva
