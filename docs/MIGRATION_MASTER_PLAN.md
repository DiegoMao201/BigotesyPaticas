# MIGRATION_MASTER_PLAN.md

> **Regla de oro:** la app Streamlit actual NO se apaga ni se rompe en ninguna fase.
> Cada cambio es reversible. Cada flip se hace por feature flag y se valida con reconciliación.

---

## 0. PRINCIPIOS

1. **Strangler Fig** — la nueva plataforma envuelve gradualmente al monolito.
2. **Backwards-compatible always** — Sheets sigue siendo válida durante toda la transición.
3. **Dual-write con reconciliación diaria** — durante F2/F3 toda escritura va a Postgres y Sheets.
4. **Cutover por módulo** — no se apaga nada de golpe.
5. **Rollback en <5 min** — vía feature flag de lectura/escritura.

---

## 1. FASES (alto nivel, sin estimación de tiempo)

### **F0 — Inception (estado actual)**
- Streamlit + Sheets en producción.
- Auditoría completa generada (`SYSTEM_AUDIT.md`).
- Plantillas de secretos creadas (`/project-secrets/`).
- `docs/` versionado con la estrategia.

### **F1 — Cimientos (no toca producción)**
Objetivo: tener infraestructura nueva lista, vacía, paralela.
- Repo monorepo o multirepo decidido (recomendado **monorepo** con `apps/streamlit`, `apps/api`, `apps/admin`, `apps/store`, `packages/shared`).
- PostgreSQL provisionado en Coolify (instancia + replica).
- Redis provisionado.
- MinIO/S3 provisionado.
- Repos `apps/api` (FastAPI) y `apps/admin` (Next.js) inicializados con CI/CD básico.
- Pipeline de migraciones (Alembic) operativo.
- Esquema inicial de DB diseñado (ver `DATABASE_STRATEGY.md`).
- Observabilidad mínima: logs estructurados + healthchecks + Sentry/Glitchtip.

**Quick wins paralelos sobre Streamlit (sin romper):**
- Extraer `utils.py` compartido.
- Pinear `requirements.txt`.
- Añadir audit log a tab `Audit_Log` del spreadsheet.
- Añadir badge de versión + commit hash en sidebar.

### **F2 — ETL espejo (lectura)**
Objetivo: PostgreSQL refleja Sheets en near-real-time.
- Worker `etl-sheets-to-pg` corriendo cada 5–10 min (RQ scheduler).
- Tablas espejo en Postgres con la misma forma que Sheets (zona `staging`).
- Mapeo a esquema relacional normalizado en zona `core`.
- Reconciliación diaria automática: conteos por tabla, hash de filas críticas, alertas si divergencia.
- Dashboard interno de salud del ETL.
- API expone endpoints **sólo de lectura** (`GET /products`, `GET /sales`, ...).

### **F3 — Dual-write controlado**
Objetivo: empezar a escribir desde la nueva plataforma sin perder Sheets.
- Cada módulo migrado activa flag `module.write.target = "both" | "sheets" | "pg"`.
- Orden recomendado de migración (de menor riesgo a mayor):
  1. **Catálogo / Productos** (lectura intensiva, escritura baja).
  2. **Clientes / Mascotas** (escritura media, sin transaccionalidad crítica).
  3. **Compras / Proveedores** (semi-batch).
  4. **Inventario / Movimientos** (transaccional).
  5. **POS / Ventas** (el más crítico — al final).
  6. **Cierres / Finanzas** (depende de los anteriores).
  7. **Loyalty / Campañas** (puede ir antes; sólo lectura agregada).
- Cada módulo migrado tiene su panel admin Next.js correspondiente.
- Streamlit sigue funcionando y leyendo desde Sheets.

### **F4 — Frontend público (e-commerce)**
- Storefront Next.js consume API de catálogo + inventario en tiempo real.
- Carrito, checkout, pagos (pasarela a definir).
- Órdenes de e-commerce generan `sales` con `channel = "online"`.
- Stock se descuenta en la misma transacción.

### **F5 — Cutover por módulo**
- Para cada módulo: flip flag a `pg`, Streamlit pasa a leer también desde la API o desde Sheets en modo congelado.
- Verificación de reconciliación 0 diferencias durante N días → cutover definitivo.

### **F6 — Decommission Streamlit**
- Cuando todos los módulos viven en la nueva plataforma y los usuarios trabajan en el admin panel:
  - Streamlit pasa a modo solo-lectura.
  - Eventualmente se archiva.
  - Sheets queda como respaldo histórico read-only.

---

## 2. CRITERIOS DE SALIDA POR FASE

| Fase | Criterio para avanzar |
|------|------------------------|
| F1 → F2 | API healthcheck verde, DB migrada, CI/CD funcionando, secretos gestionados |
| F2 → F3 | Reconciliación 7 días consecutivos sin diferencias en tablas core |
| F3 → F4 | ≥3 módulos en dual-write estable durante 14 días |
| F4 → F5 | Storefront pasa pruebas E2E + de carga + de seguridad básica |
| F5 → F6 | 30 días sin escrituras desde Streamlit, reconciliación limpia |

---

## 3. MATRIZ MÓDULO × ESTADO

| Módulo | Lectura PG | Escritura PG | UI Next.js | Streamlit |
|--------|------------|--------------|------------|-----------|
| Catálogo | ⏳ | ⏳ | ⏳ | ✅ activo |
| Clientes | ⏳ | ⏳ | ⏳ | ✅ activo |
| Inventario | ⏳ | ⏳ | ⏳ | ✅ activo |
| Compras | ⏳ | ⏳ | ⏳ | ✅ activo |
| POS | ⏳ | ⏳ | ⏳ | ✅ activo |
| Finanzas | ⏳ | ⏳ | ⏳ | ✅ activo |
| Loyalty | ⏳ | ⏳ | ⏳ | ✅ activo |
| E-commerce | ⏳ | ⏳ | ⏳ | N/A |

> Esta matriz se actualiza en cada PR que mueva el estado de un módulo.

---

## 4. ROLLBACK PLAYBOOK

Para cualquier flip por módulo:

1. Detectar incidente (alerta de reconciliación o reporte de usuario).
2. Cambiar flag `module.write.target` a `sheets`.
3. Cambiar flag `module.read.source` a `sheets`.
4. Streamlit retoma el control.
5. Postmortem + fix + re-flip planificado.

Tiempo objetivo: **< 5 minutos** desde detección a rollback.

---

## 5. DEPENDENCIAS / RIESGOS DE LA MIGRACIÓN

| Riesgo | Mitigación |
|--------|------------|
| Divergencia Sheets vs PG durante dual-write | Reconciliación diaria automática + alertas |
| Service account de Sheets compartido | Crear segundo service account read-only para ETL |
| Cambios manuales en Sheets durante la migración | Bloquear edición humana en tabs migrados (proteger ranges) |
| Cuota Google Sheets API | ETL con caching + lectura por delta |
| Pérdida de adopción del admin Next.js | Replicar UX de Streamlit antes de pedir migrar usuarios |
| Migración de IDs (UUID nuevos vs SKU viejos) | Tabla `legacy_id_map` puente |

---

## 6. ENTREGABLES POR FASE

| Fase | Entregables versionados en `docs/` |
|------|------------------------------------|
| F0 | `SYSTEM_AUDIT.md`, `ARCHITECTURE_ANALYSIS.md`, `MIGRATION_MASTER_PLAN.md`, `DATABASE_STRATEGY.md`, `API_STRATEGY.md`, `FRONTEND_STRATEGY.md`, `DEVOPS_STRATEGY.md`, `TECH_DEBT_REPORT.md`, `project-continuity.md` |
| F1 | `INFRA_BOOTSTRAP.md`, `SCHEMA_V1.sql`, `CI_CD_PIPELINE.md` |
| F2 | `ETL_DESIGN.md`, `RECONCILIATION_PLAYBOOK.md` |
| F3 | `MODULE_CUTOVER_<modulo>.md` por cada módulo migrado |
| F4 | `ECOMMERCE_SPEC.md`, `PAYMENT_INTEGRATION.md` |
| F5 | `RUNBOOKS.md`, `INCIDENT_PLAYBOOK.md` |
| F6 | `STREAMLIT_DECOMMISSION.md` |
