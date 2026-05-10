# project-continuity.md

> Este archivo es la memoria operativa del proyecto. Cualquier sesión (humana o IA) debe leerlo ANTES de tomar decisiones que afecten arquitectura, storage o flujos.
> **Cada cambio operativo o arquitectónico debe quedar registrado aquí.**

---

## DECISIONES VIGENTES (no reabrir sin justificación)

| # | Decisión | Vigente desde | Razón |
|---|-----------|----------------|--------|
| C-001 | La app Streamlit actual NO se apaga durante la migración | 2026-05-10 | Producción operativa |
| C-002 | Migración bajo patrón **Strangler Fig** | 2026-05-10 | Riesgo controlado |
| C-003 | Backend objetivo: **PostgreSQL 16** | 2026-05-10 | Ver `DATABASE_STRATEGY.md` |
| C-004 | API objetivo: **FastAPI + Pydantic v2 + SQLAlchemy 2** | 2026-05-10 | Ver `API_STRATEGY.md` |
| C-005 | Frontend objetivo: **Next.js 14 App Router + TS estricto + Tailwind + shadcn** | 2026-05-10 | Ver `FRONTEND_STRATEGY.md` |
| C-006 | Orquestador: **Coolify** existente | 2026-05-10 | Usuario ya lo administra |
| C-007 | Monorepo con pnpm + Turborepo previsto | 2026-05-10 | Compartir tipos OpenAPI |
| C-008 | Google Sheets sigue siendo válido durante toda la transición | 2026-05-10 | Backwards-compat |
| C-009 | Toda escritura crítica futura es transaccional e idempotente | 2026-05-10 | Atomicidad |
| C-010 | Secretos sólo vía `project-secrets/` (plantillas) + Coolify (reales) | 2026-05-10 | Seguridad |
| C-011 | Tabla puente `ops.legacy_id_map` para convivencia con Streamlit | 2026-05-10 | Rollback seguro |

---

## REGISTRO CRONOLÓGICO

### 2026-05-10 — Auditoría inicial completa
- Generada auditoría exhaustiva del repo (ver `SYSTEM_AUDIT.md`).
- Creada documentación estratégica completa: `ARCHITECTURE_ANALYSIS.md`, `MIGRATION_MASTER_PLAN.md`, `DATABASE_STRATEGY.md`, `API_STRATEGY.md`, `FRONTEND_STRATEGY.md`, `DEVOPS_STRATEGY.md`, `TECH_DEBT_REPORT.md`.
- Creado `project-secrets/` con plantillas `.env*.example`, `SECRETS_SETUP.md`, `MISSING_SECRETS.md`.
- Reforzado `.gitignore` para evitar commit accidental de secretos y artefactos.
- **No se modificó código de la aplicación Streamlit.** Producción intacta.
- Próxima acción autónoma definida: **Sprint 0 de quick wins** (extraer `utils.py`, pinear deps, audit log mínimo, README, ruff/black) — todo sobre Streamlit, sin tocar lógica de negocio.

---

## PLANTILLA PARA NUEVAS ENTRADAS

```
### YYYY-MM-DD — <título corto>
- Qué cambió:
- Por qué:
- Cómo se hizo:
- Impacto en producción:
- Reversible: sí/no, cómo
- Próximo paso:
```
