# TECH_DEBT_REPORT.md

## CRITERIOS
- **Severidad**: 🔴 Alta · 🟠 Media · 🟡 Baja
- **Esfuerzo**: S (≤2h) · M (≤1d) · L (≤1w) · XL (>1w)
- **Tipo**: ARQ · CAL · SEG · PERF · OPS · DX

---

## 1. CATÁLOGO DE DEUDA

| # | Item | Tipo | Sev | Esf | Estrategia |
|---|------|------|-----|-----|------------|
| D-01 | Lógica utilitaria duplicada en 5 páginas (`clean_currency`, `normalizar_id_producto`, `_find_col`, `_norm_col`, `money_int/float`, `_safe_to_*`) | ARQ/CAL | 🟠 | S | Extraer `bp_common/utils.py` y refactor de imports |
| D-02 | `requirements.txt` sin pinning de versiones | OPS | 🟠 | S | Migrar a `pip-tools` o `uv` con lockfile |
| D-03 | `twilio` declarado y nunca usado | DX | 🟡 | S | Remover dependencia |
| D-04 | Atomicidad venta+stock no transaccional | ARQ/SEG | 🔴 | M | Refactor temporal a "preflight check + write + verify"; definitivo en migración a PG |
| D-05 | Race conditions con múltiples usuarios sobre Sheets | ARQ | 🔴 | L | Sólo se resuelve en PG; mientras tanto, advertir y mantener single-writer |
| D-06 | Dos contenedores `session_state` paralelos (`db` y `data_store`) | ARQ | 🟠 | M | Unificar en un único `app_state` con interfaz tipada |
| D-07 | `ws.find()` lineal residual | PERF | 🟡 | S | Sustituir por índices precomputados ya disponibles |
| D-08 | Validación débil de input (teléfonos, emails, montos) | SEG/CAL | 🟠 | M | Capa de validación con Pydantic en utilidades comunes |
| D-09 | Sin tests automatizados | CAL | 🔴 | L | Bootstrap `pytest` + golden tests sobre lógica crítica antes de tocarla |
| D-10 | Sin linter/formatter | CAL/DX | 🟠 | S | `ruff` + `black` + pre-commit |
| D-11 | Sin CI/CD | OPS | 🟠 | M | GitHub Actions: lint+test en PR; deploy a staging en `develop` |
| D-12 | Sin observabilidad (logs/métricas/audit) | OPS/SEG | 🔴 | M | Logging JSON a archivo + tab `Audit_Log` en Sheets como puente |
| D-13 | Sin autenticación de usuarios | SEG | 🔴 | L | Mientras tanto: SSO de Streamlit Cloud o reverse proxy con basic auth; definitivo en Next.js |
| D-14 | Plantilla `factura.html` con branding hardcoded | ARQ | 🟡 | S | Parametrizar empresa y contacto desde config |
| D-15 | Mensajes WhatsApp hardcoded en código | ARQ | 🟡 | M | Mover a tabla/config de plantillas |
| D-16 | Reorden y ABC con thresholds hardcoded | ARQ | 🟡 | S | Externalizar a tabla `policies` |
| D-17 | PDF generation sin progress feedback ni queue | UX/PERF | 🟡 | S | Spinner + en migración: worker async |
| D-18 | Schema implícito (nombres de columnas mágicos) | ARQ/CAL | 🟠 | M | Constantes centralizadas + verificación en startup (`asegurar_esquema_operativo` ya parcial) |
| D-19 | Service account compartido sin rotación | SEG | 🟠 | S | Crear segundo service account read-only para ETL futuro; documentar rotación |
| D-20 | Sin backup externo del spreadsheet | OPS/SEG | 🟠 | S | Job diario que exporta a CSV/Parquet en almacenamiento externo |
| D-21 | Renombrar producto huérfana ventas históricas | ARQ | 🟡 | M | Forzar uso de `Producto_UID` en escritura; bloquear edición destructiva |
| D-22 | Imports dispersos y orden inconsistente | DX | 🟡 | S | `ruff --select I` (isort) en pre-commit |
| D-23 | `factura.html` sin repetición de header/footer multipágina | UX | 🟡 | S | Ajustar CSS `@page` |
| D-24 | Sin healthcheck endpoint en Streamlit | OPS | 🟡 | S | Endpoint `/_stcore/health` ya existe; documentarlo y monitorearlo |
| D-25 | Mezcla `pytz` y `zoneinfo` | CAL | 🟡 | S | Estandarizar `zoneinfo`; mantener fallback `pytz` para Py<3.9 |
| D-26 | `Maestro_Proveedores` poco mantenido | DATOS | 🟠 | M | UI de upsert directo + auto-creación al cargar factura |
| D-27 | `Historial_Ordenes` no afecta stock | ARQ | 🟠 | M | En migración: estado `received` dispara movimiento de stock |
| D-28 | Sin auditoría de quién hizo qué | SEG | 🔴 | M | Audit log mínimo en Sheets (`Audit_Log` tab) hasta cutover |
| D-29 | Errores PDF silenciosos | UX | 🟡 | S | Capturar y mostrar fallback explícito al cajero |
| D-30 | Sin documentación funcional ni README | DX | 🟠 | S | `README.md` con setup local, deploy, arquitectura |

---

## 2. PRIORIZACIÓN RECOMENDADA

### Sprint 0 (sin tocar lógica crítica, sólo higiene)
- D-01, D-02, D-03, D-10, D-22, D-30, D-24, D-25, D-29.

### Sprint 1 (preparar terreno para migración)
- D-12 (logs + audit log en Sheets), D-19 (segundo SA), D-20 (backup externo), D-18 (constantes de esquema), D-08 (validación entrada).

### Sprint 2 (mientras se construye F1 nuevo)
- D-06 (unificar session_state), D-07, D-14, D-15, D-16, D-26, D-29.

### Resueltos por la migración (no se atacan en Streamlit)
- D-04, D-05, D-09, D-11, D-13, D-17, D-21, D-27, D-28.

---

## 3. NO HACER (anti-patterns evitar)

- ❌ Reescribir Streamlit "in-place" mientras se construye la nueva plataforma.
- ❌ Migrar todo de golpe sin reconciliación.
- ❌ Cambiar primary keys (UUIDs nuevos) sin tabla puente.
- ❌ Refactorizar `_normalizar_estado_pago`, `precio_con_margen`, `clean_currency` sin tests golden previos.
- ❌ Eliminar columnas de Sheets durante la transición.
- ❌ Borrar el spreadsheet original tras cutover (mantener congelado read-only).
