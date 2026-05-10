# DEVOPS_STRATEGY.md

## 1. PLATAFORMA

- **Coolify** como orquestador (ya administrado por el usuario en `panel.datovatenexuspro.com`).
- Cada servicio = un Coolify resource (Docker container o stack docker-compose).
- Imágenes publicadas en GHCR (`ghcr.io/diegomao201/<repo>:<sha>`).
- Backups automatizados a almacenamiento externo (S3/MinIO).

## 2. SERVICIOS A DESPLEGAR

| Servicio | Tipo | Notas |
|----------|------|-------|
| `streamlit-legacy` | App | Estado actual, sigue corriendo |
| `api` | App | FastAPI + uvicorn/gunicorn |
| `admin-web` | App | Next.js (panel) |
| `store-web` | App | Next.js (storefront) |
| `worker` | App | RQ workers |
| `scheduler` | App | RQ scheduler / cron |
| `postgres` | DB | PG16 + replica + WAL archiving |
| `redis` | Cache/Queue | Redis 7 |
| `minio` | Storage | S3 compatible (PDFs, imágenes) |
| `loki` + `promtail` | Logs | Centralización |
| `prometheus` + `grafana` | Métricas | Dashboards y alertas |
| `tempo` o `jaeger` | Tracing | Opcional fase 2 |
| `sentry` o `glitchtip` | Errores | App-level |

## 3. AMBIENTES

| Env | Hostname | Datos | Despliegue |
|-----|----------|-------|------------|
| `dev` | local + branch previews | sintéticos | docker-compose / Coolify preview |
| `staging` | `staging.<dominio>` | snapshot anonimizado de prod (semanal) | auto desde `develop` |
| `prod` | `panel.datovatenexuspro.com` y dominios públicos | reales | manual (botón) desde `main` tras CI verde |

## 4. CI/CD (GitHub Actions)

Pipelines:
1. **lint + typecheck** (ruff/black/mypy + eslint/tsc).
2. **tests unit + integración** (pytest, vitest).
3. **build imágenes** (Docker buildx + cache).
4. **scan** (Trivy + gitleaks).
5. **push a GHCR**.
6. **deploy** vía Coolify API (webhook firmado).
7. **smoke tests post-deploy** (Playwright + curl healthchecks).
8. **rollback** (re-deploy del tag anterior si smoke falla).

Reglas:
- `main` = prod, `develop` = staging.
- PRs requieren CI verde + 1 review + cobertura no decreciente.
- Tags semver para releases (`v1.2.3`).

## 5. DOCKERIZACIÓN

- Multi-stage Dockerfiles por app.
- Imágenes finales basadas en `python:3.12-slim` y `node:20-slim`.
- Usuarios non-root.
- HEALTHCHECK en cada servicio.
- Tamaños objetivo: API < 250MB, Next < 300MB.

## 6. SECRETOS

- Centralizados en Coolify (UI) por ambiente.
- En repo sólo plantillas en `project-secrets/*.example`.
- Rotación cuatrimestral mínimo para credenciales sensibles.
- Reglas en `gitleaks` y pre-commit hook que bloquea push de secretos.

## 7. BACKUPS Y DR

- **Postgres**: `pg_basebackup` semanal + WAL continuo. Retención 30d. Snapshot mensual 12 meses.
- **MinIO**: replicación cross-bucket + snapshot diario.
- **Sheets**: export diario a CSV/Parquet en MinIO durante toda la transición.
- **Restore drill** mensual en staging documentado en `docs/RUNBOOKS.md`.
- RTO objetivo: 1h. RPO objetivo: 15 min.

## 8. OBSERVABILIDAD

- Logs JSON estructurados, agregados en Loki, vistos en Grafana.
- Métricas: Prometheus + Grafana dashboards por servicio.
- Tracing distribuido OpenTelemetry.
- Alertas en Grafana → Slack/Telegram/email.
- Alertas mínimas: error rate, latencia p95, disco, CPU, RAM, jobs failing, reconciliación divergente.

## 9. SEGURIDAD

- HTTPS obligatorio (Let's Encrypt vía Coolify).
- HSTS, CSP, X-Content-Type-Options, X-Frame-Options.
- WAF / rate limit en el proxy.
- Escaneos: Trivy (imágenes), gitleaks (repo), Dependabot (deps).
- Pen test ligero antes de F4 (e-commerce público).
- Política de mínimos privilegios para credenciales DB y service accounts.

## 10. POLÍTICA DE RAMAS Y RELEASE

- Trunk-based con feature branches cortas.
- Conventional Commits (`feat:`, `fix:`, `chore:`...).
- Changelog generado automáticamente con `release-please`.
- Hotfixes desde `main`, merge-back inmediato a `develop`.

## 11. RUNBOOKS MÍNIMOS A REDACTAR

- Restaurar Postgres desde backup.
- Reprocesar día de ETL Sheets→PG.
- Forzar reconciliación.
- Rotar service account de Sheets.
- Apagar/encender módulos vía feature flags.
- Rollback de deploy.

## 12. COSTOS / CAPACITY (estimado inicial)

- 1 VM mediana (4 vCPU, 8GB RAM) cubre F1–F3.
- Escalar horizontalmente API y workers en F4 cuando entre tráfico público.
- Postgres: 50–100 GB con crecimiento ~5GB/año estimado.
- MinIO: depende de PDFs e imágenes; arrancar con 100GB.
