# Despliegue en Coolify

Este documento describe paso a paso cómo desplegar **Bigotes y Paticas** en Coolify v4.

## Arquitectura objetivo

```
api.bigotesypaticas.com    →  apps/api          (FastAPI · puerto 8000)
admin.bigotesypaticas.com  →  apps/admin        (Next.js · puerto 3001)
bigotesypaticas.com        →  apps/store        (Next.js · puerto 3000)
                              + Streamlit POS   (puerto 8501, dominio interno)

PostgreSQL 16  →  resource interno (no expuesto)
Redis 7        →  resource interno (no expuesto)
S3 / Spaces    →  externo (DigitalOcean Spaces o MinIO ya existente)
```

## 1. Crear el proyecto

1. Entrar a `https://panel.datovatenexuspro.com`
2. Projects → **+ Add** → nombre `Bigotes y Paticas` → entorno `production`
3. Seleccionar el server `localhost`

## 2. Recursos (Resources)

### 2.1 PostgreSQL 16
- Resources → + Database → PostgreSQL 16
- Nombre: `bp-postgres`
- Database: `bp_prod`
- User: `bp_app`
- Pass: generar (guardar en project-secrets)
- Save → Deploy
- Tras ready: copiar **Internal URL** (ej. `postgresql://bp_app:***@bp-postgres:5432/bp_prod`)

### 2.2 Redis 7
- Resources → + Database → Redis 7
- Nombre: `bp-redis`
- Pass: generar
- Save → Deploy → copiar Internal URL

### 2.3 (Opcional) MinIO
Si ya tienes uno corporativo o usas Spaces, sáltalo. Si no:
- Resources → + Service → MinIO
- Crear buckets: `bp-uploads`, `bp-public`, `bp-backups`

## 3. Desplegar la API (FastAPI)

1. Resources → + New Resource → **Public Repository**
2. URL: `https://github.com/DiegoMao201/BigotesyPaticas`
3. Branch: `main`
4. Build Pack: **Dockerfile**
5. Dockerfile location: `apps/api/Dockerfile`
6. Base directory: `/` (monorepo, contexto raíz)
7. Port: `8000`
8. Domain: `api.bigotesypaticas.com` (Coolify gestiona Let's Encrypt)
9. Environment variables:

```env
ENVIRONMENT=production
APP_NAME=Bigotes y Paticas API
DATABASE_URL=postgresql+asyncpg://bp_app:***@bp-postgres:5432/bp_prod
DATABASE_URL_SYNC=postgresql+psycopg://bp_app:***@bp-postgres:5432/bp_prod
REDIS_URL=redis://default:***@bp-redis:6379/0
JWT_SECRET=<generar con: openssl rand -hex 32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7
ADMIN_EMAIL=admin@bigotesypaticas.com
ADMIN_PASSWORD=<generar fuerte>
CORS_ORIGINS=https://bigotesypaticas.com,https://admin.bigotesypaticas.com
S3_ENDPOINT_URL=https://nyc3.digitaloceanspaces.com
S3_REGION=nyc3
S3_BUCKET=bp-uploads
S3_ACCESS_KEY=<spaces key>
S3_SECRET_KEY=<spaces secret>
LOG_LEVEL=INFO
```

10. Healthcheck: `GET /health` (Coolify lo configura desde el Dockerfile HEALTHCHECK)
11. Deploy. El CMD del Dockerfile correrá automáticamente:
    - `alembic upgrade head` (migraciones)
    - `python -m app.cli.seed` (admin + roles + location)
    - `gunicorn -w 4 ...` (servidor)

## 4. Desplegar el Admin (Next.js)

1. Resources → + New Resource → **Public Repository** (mismo repo)
2. Branch: `main`
3. Build Pack: **Nixpacks** (auto-detecta Next.js)
4. Base directory: `/apps/admin`
5. Install command: `corepack enable && pnpm install --frozen-lockfile`
6. Build command: `pnpm build`
7. Start command: `pnpm start`
8. Port: `3001`
9. Domain: `admin.bigotesypaticas.com`
10. ENV:

```env
NEXT_PUBLIC_API_BASE_URL=https://api.bigotesypaticas.com
SESSION_SECRET=<openssl rand -hex 32>
NEXT_PUBLIC_BRAND_NAME=Bigotes y Paticas
NEXT_PUBLIC_BRAND_DOMAIN=bigotesypaticas.com
```

11. Deploy.

## 5. Desplegar la Tienda (Next.js)

Idéntico al admin pero:
- Base directory: `/apps/store`
- Port: `3000`
- Domain: `bigotesypaticas.com` + `www.bigotesypaticas.com`
- ENV: `NEXT_PUBLIC_API_BASE_URL=https://api.bigotesypaticas.com`

## 6. Webhook GitHub para auto-deploy

Cada resource en Coolify expone un webhook. Configurarlos en GitHub:

1. Repo → Settings → Webhooks → Add
2. Payload URL: el que provee Coolify por servicio
3. Content type: `application/json`
4. Secret: el que provee Coolify
5. Events: `push` (filter por branch `main`)

Cada `git push origin main` desencadenará el redeploy.

## 7. SSL y dominios

Coolify integra Let's Encrypt automáticamente cuando:
- El dominio resuelve al servidor
- El puerto 80/443 están abiertos en el server

Configurar DNS (en tu proveedor):
```
A     api.bigotesypaticas.com    → <IP del server>
A     admin.bigotesypaticas.com  → <IP del server>
A     bigotesypaticas.com        → <IP del server>
A     www.bigotesypaticas.com    → <IP del server>
```

## 8. Verificación post-deploy

```bash
# Healthcheck API
curl https://api.bigotesypaticas.com/health
curl https://api.bigotesypaticas.com/health/ready
curl https://api.bigotesypaticas.com/version

# Login admin
curl -X POST https://api.bigotesypaticas.com/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@bigotesypaticas.com","password":"<el que pusiste>"}'

# Frontend admin
open https://admin.bigotesypaticas.com

# Storefront
open https://bigotesypaticas.com
```

## 9. Backups

- PostgreSQL: Coolify ofrece backups automáticos en el resource → Backups → enable. Frecuencia diaria 02:00, retención 30 días.
- Sheets (legacy): cron `make backup-sheets` configurado por GitHub Actions → ya activo.
- MinIO/S3: políticas del bucket (versionado + lifecycle).

## 10. Coexistencia con Streamlit

El Streamlit POS sigue corriendo en su servicio actual (Streamlit Cloud o Coolify). El backend FastAPI **lee de la misma fuente** durante la transición:

- Fase A: Sheets sigue siendo *single source of truth*. ETL bidireccional Sheets ↔ PG cada 15 min.
- Fase B (con flags `WRITE_TO_PG=true`): Streamlit empieza a escribir también a PG.
- Fase C (con `WRITE_TO_SHEETS=false`): PG es la fuente, Sheets se desactiva como destino.

Nada se rompe en producción mientras se transiciona.
