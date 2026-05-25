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

### 2026-05-10 — Incidente de secretos en `.env.production.example`
- El usuario pegó valores REALES (Google SA private key, OpenRouter, Spaces, Postgres, Gmail App Password) al final de la plantilla.
- **NO se llegaron a commitear.** Se verificó `git log` y `git show e99f6dd` — ningún hash en remoto contiene los secretos.
- Mitigación: secretos movidos a `project-secrets/.env.production` (ya gitignored), `.example` restaurado limpio, añadido `.gitleaks.toml` con reglas custom + hook pre-commit + job CI.
- **Acción humana pendiente**: rotar Google SA key, password Postgres, OpenRouter API key, DigitalOcean Spaces keys, Gmail App Password (ver `INCIDENT_2026-05-10_secrets_in_example.md` y `MISSING_SECRETS.md`).

### 2026-05-10 — Sprint 0 (Hardening Streamlit) ENTREGADO
- Paquete `bp_common/` (11 módulos opt-in, bit-exact respecto al legacy): `currency`, `ids`, `pricing`, `payments`, `tz`, `sheets_sanitize`, `flags`, `audit`, `version_info`, `logging_setup`.
- Suite de tests: 88 casos verdes (`pytest -q` → 88 passed). Golden tests para `clean_currency`, `normalizar_id_producto`, `precio_con_margen`, `_normalizar_estado_pago`.
- `pyproject.toml` con ruff (lint+format), pytest, coverage, mypy. Streamlit legacy exento del linter para no introducir cambios destructivos.
- `requirements.txt` pineado (removido `twilio` no usado). `requirements-dev.txt` añadido.
- `.pre-commit-config.yaml` (ruff + gitleaks + detect-private-key + checks varios).
- `.github/workflows/ci.yml` (lint + tests py3.11/3.12 + secrets-scan).
- `scripts/backup_sheets.py` standalone con manifest JSON, listo para cron.
- Documentado en `docs/SPRINT0_HARDENING.md`.
- **App Streamlit y `pages/*.py` NO se modificaron.** Producción intacta.
- Próximo: Fase 1 — Fundación infraestructura (monorepo, docker-compose, esqueletos `apps/api` FastAPI y `apps/admin` Next.js).

---

## PLANTILLA PARA NUEVAS ENTRADAS

### 2026-05-25 — Cierre de caja operativo + ventas pendientes a pagadas + clientes con mascota
- Qué cambió:
	- API: nuevo endpoint `POST /v1/sales/orders/{order_id}/mark-paid` para convertir saldo pendiente en pago y dejar la orden en `Pagado`.
	- API/CRM: alta y edición de clientes ahora incluye `address`, `pet_name`, `pet_type`, `pet_notes` (persistidos en `extra`).
	- Admin: acción "Marcar como pagada" en detalle de venta, formulario de clientes ampliado, y limpieza del duplicado legacy en cash-closings.
- Por qué:
	- El usuario no podía cerrar operación diaria con confianza, no podía regularizar ventas pendientes y faltaban campos clave en clientes.
- Cómo se hizo:
	- Se corrigió código backend/frontend, se validó build de Admin y compilación Python, se hizo commit `97d6f52` y deploy real en Coolify (no solo restart).
	- Deploys verificados `finished`: API `gggb92b2necl8s6i6r5dn68j`, Admin `alobuja2e123hjf0n010c8j0`.
- Impacto en producción:
	- OpenAPI en prod confirma rutas nuevas (`mark-paid`, `cash-closings/today`).
	- UI en prod confirma versión nueva de cash-closings y sales.
	- Verificación DB en contenedor PostgreSQL (`l0k0kck8cwck4goskcs0scsg`):
		- 2026-05-23: 19 órdenes, ventas 1,623,700 y pagos 1,075,900 (saldo pendiente 547,800).
		- `finance.cash_closings` contiene actualmente solo fila de 2026-05-25 en estado `open`.
- Reversible: sí.
	- Revertir commit `97d6f52` y redeploy de API/Admin.
- Próximo paso:
	- Ejecutar cierre funcional desde UI (con saldo contado) y validar que la fila del día pase a `closed` con snapshot y diferencia esperada.

### 2026-05-25 — Hardening operativo: proveedores, análisis IA, XML y móvil
- Qué cambió:
	- `cash-closings/today` ahora usa fecha de negocio `America/Bogota` (no `date.today()` de servidor), corrigiendo ventas que no aparecían en cierre.
	- `inventory/analytics/velocity` corregido para usar columnas reales de `inventory.stock_movements` (`movement_type`, `quantity_delta`), restaurando la pestaña de Análisis IA.
	- `purchases/xml/parse` ajustado para inferir costo unitario sin dividir incorrectamente cuando `PriceAmount` ya viene unitario.
	- `purchases` ahora hace upsert de `purchasing.supplier_sku_map` al registrar compras, vinculando SKU proveedor ↔ producto interno de forma automática.
	- `suppliers/{id}/skus` ampliado con productos asociados + inteligencia de recompra (8/15/20 días): cobertura, velocidad diaria y cantidades sugeridas.
	- Admin: ficha de proveedor robusta (sin crash por shape), mejoras de edición de clientes en UI, y navegación móvil con drawer para operación en celular.
- Por qué:
	- Había crash en `/suppliers`, Análisis IA vacío, costos de compra incorrectos en XML y desalineación de fecha entre ventas y cierre de caja.
- Cómo se hizo:
	- Correcciones en FastAPI y Next.js, validación con build de Admin (`next build`) y compilación Python de módulos API editados.
- Impacto en producción:
	- Al desplegar este lote, la app debe mostrar: análisis IA activo, proveedor con productos/recompra, costos XML correctos y ventas visibles en cierre del día local.
- Reversible: sí.
	- Revertir commits del lote y redeploy de API/Admin.
- Próximo paso:
	- Deploy API/Admin y smoke test guiado en prod: editar cliente, abrir ficha proveedor, importar XML, registrar venta y verificar reflejo inmediato en cierre de caja.

### 2026-05-25 — Ajuste fino operativo: cuadre de caja + IA con proveedores + comprobante premium
- Qué cambió:
	- `finance._compute_live_totals` ahora normaliza pagos por orden para no sobrecontar efectivo entregado cuando hay cambio (ej: pago 5,000 para venta 2,900 ya no infla caja a 5,000).
	- `inventory/analytics/velocity` expone `category_name`, `supplier_id`, `supplier_name` por producto (join con categorías y proveedor preferente en `supplier_sku_map`).
	- Admin inventario (Análisis IA): filtros nuevos por proveedor y categoría; el plan de compra ahora genera mensaje profesional totalizado por proveedor, con acciones directas de copiar y abrir WhatsApp.
	- Comprobante de venta (`/v1/sales/orders/{id}/invoice`) rediseñado con paleta institucional teal/amber, layout más limpio y referencia compacta `REF-XXXXXX` para evitar SKU largos ilegibles.
- Por qué:
	- El cierre diario estaba mostrando más efectivo del realmente vendido cuando se ingresaba valor entregado con cambio.
	- Operación necesitaba pasar de análisis IA a acción comercial real (orden de compra por WhatsApp) filtrando por proveedor/categoría.
	- El comprobante debía reflejar estética institucional y mejorar lectura para cliente/equipo.
- Cómo se hizo:
	- Ajuste SQL en backend de finanzas para prorrateo/cap por `grand_total` por orden.
	- Enriquecimiento de payload de velocidad + tipado frontend (`VelocityProduct`).
	- Mejora UI en `inventory/page.tsx` con filtros y generador de mensaje OC.
	- Reescritura de plantilla HTML de factura con estilos institucionales y referencia compacta.
- Impacto en producción:
	- Funcionalmente listo para deploy; cambia respuesta de analytics y la presentación de comprobante.
	- No introduce migraciones ni cambios de esquema.
- Reversible: sí.
	- Revertir commit del lote y redeploy de API/Admin.
- Próximo paso:
	- Deploy y smoke test en prod: venta en efectivo con cambio + cierre del día, IA con filtros y envío WhatsApp, descarga de comprobante nuevo.

```
### YYYY-MM-DD — <título corto>
- Qué cambió:
- Por qué:
- Cómo se hizo:
- Impacto en producción:
- Reversible: sí/no, cómo
- Próximo paso:
```
