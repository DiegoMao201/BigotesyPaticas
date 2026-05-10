# SYSTEM_AUDIT.md
**Proyecto:** BigotesyPaticas (Streamlit ERP/POS — Pet Shop)
**Fecha auditoría:** 2026-05-10
**Alcance:** Auditoría exhaustiva read-only del repo completo en `main`.
**Modo:** Sin tocar producción. Sólo análisis y documentación.

---

## 0. TL;DR EJECUTIVO

- Aplicación **Streamlit monolítica** operativa que cubre POS, CRM, inventario, compras, finanzas y loyalty.
- **Backend = Google Sheets** (un único spreadsheet con 7 worksheets activos). No hay base de datos relacional.
- **Sin autenticación, sin RBAC, sin auditoría, sin tests, sin observabilidad**. Single service account compartido.
- Lógica de negocio crítica funciona pero presenta **riesgos de concurrencia, atomicidad e integridad**.
- **No se detectan secretos hardcoded** ✅. Todo vía `st.secrets`.
- Deuda técnica principal: duplicación masiva de utilitarios (~5 copias), acoplamiento a Sheets, ausencia de capa de validación.
- Estado: **OPERATIVO con riesgo MEDIO**. Aceptable para 1 usuario / pocos usuarios concurrentes. **No escalable** sin migración.

---

## 1. INVENTARIO DE ARTEFACTOS

| Artefacto | Tipo | LOC aprox | Responsabilidad |
|-----------|------|-----------|------------------|
| [BigotesyPaticas.py](../BigotesyPaticas.py) | Entry point Streamlit | ~2.000 | Orquestador, POS, sync, generación PDF |
| [pages/Analisis_financiero.py](../pages/Analisis_financiero.py) | Página | ~400 | Dashboard financiero / KPIs |
| [pages/Compras.py](../pages/Compras.py) | Página | ~700 | Compras, OCR factura, ABC, reorden |
| [pages/Inventario_Nexus.py](../pages/Inventario_Nexus.py) | Página | ~500 | Estado de stock, conteo físico |
| [pages/Nexus_Loyalty.py](../pages/Nexus_Loyalty.py) | Página | ~600 | RFM, campañas WhatsApp, cumpleaños |
| [pages/Producto_360.py](../pages/Producto_360.py) | Página | ~400 | Análisis precio/costo/margen |
| [factura.html](../factura.html) | Template Jinja2 | ~150 | Plantilla PDF factura |
| [requirements.txt](../requirements.txt) | Deps Python | 12 | Dependencias sin pinning |
| [packages.txt](../packages.txt) | Deps OS | 5 | Libs nativas para WeasyPrint |

**Total LOC estimado:** ~4.000–4.500.

---

## 2. INTEGRACIONES EXTERNAS

### 2.1 Google Sheets (única fuente de datos)
- Cliente: `gspread` con service account.
- Secrets requeridos: `st.secrets["google_service_account"]`, `st.secrets["SHEET_URL"]`.
- Conexión cacheada `@st.cache_resource(ttl=3600)`.
- Retry: `safe_api_call()` con backoff exponencial (2→4→8s) sobre HTTP 429.

### 2.2 Worksheets (7 tabs en un spreadsheet maestro)

| Tab | PK lógica | Volumen esperado | Patrón de acceso |
|-----|-----------|--------------------|--------------------|
| `Inventario` | `Producto_UID` (UUID) | 100–5.000 filas | Read full + update por celda |
| `Clientes` | `Cedula` | 50–2.000 | Read full + append/update |
| `Ventas` | `ID_Venta` | 1.000–50.000+ | Read full + append + updates parciales (pagos) |
| `Gastos` | `ID_Gasto` | 500–10.000 | Read + append |
| `Cierres` | `Fecha+Hora` | ≤365/año | Read + append |
| `Maestro_Proveedores` | `ID_Proveedor` + `SKU_Proveedor` | 50–500 | Read + upsert |
| `Historial_Ordenes` | `ID_Orden` | 1–1.000 | Read + append |

### 2.3 Otras integraciones
- **WhatsApp**: links `wa.me/...` generados client-side. **No hay envío automatizado** (Twilio importado pero nunca llamado).
- **PDF**: `weasyprint` con fallback a `reportlab`.
- **No hay**: pasarela de pagos, email, CDN, almacenamiento de imágenes externo, OCR real (XML referenciado pero no operativo en flujo principal).

---

## 3. SECRETOS / CREDENCIALES

| Secreto | Storage actual | Hardcoded? | Rotación |
|---------|----------------|------------|----------|
| `google_service_account` | `st.secrets` ✅ | No ✅ | **Ninguna política** ⚠️ |
| `SHEET_URL` | `st.secrets` ✅ | No ✅ | N/A |

Postura general: **buena externalización**, pero falta rotación, monitoreo de uso del service account y separación dev/prod.

---

## 4. ENTIDADES DE NEGOCIO PRINCIPALES

```
Cliente (Cedula PK)
  └─ tiene N Mascotas (Info_Mascotas JSON embebido)

Producto (Producto_UID PK, ID_Producto SKU)
  ├─ tiene N Proveedores (Maestro_Proveedores: SKU_Proveedor)
  └─ tiene 1 Stock + 1 Costo + 1 Precio + 1 IVA

Venta (ID_Venta PK)
  ├─ pertenece a 1 Cliente (Cedula_Cliente)
  ├─ contiene N Items (Items_JSON embebido, sin tabla normalizada)
  ├─ tiene 1 Estado_Pago + Abono_Recibido + Saldo_Pendiente
  └─ tiene 1 Estado_Envio

Gasto (ID_Gasto PK) — independiente
Cierre (Fecha PK) — agregación diaria
OrdenCompra (ID_Orden PK) — referencia, no afecta stock automáticamente
```

**Foreign keys lógicas (no enforced):**
- `Ventas.Cedula_Cliente` → `Clientes.Cedula`
- `Items_JSON.Producto_UID` → `Inventario.Producto_UID`
- `Maestro_Proveedores.SKU_Interno` → `Inventario.ID_Producto_Norm`

---

## 5. LÓGICA DE NEGOCIO CRÍTICA (preservar 1:1)

| Lógica | Ubicación | Contrato |
|--------|-----------|----------|
| Descuento de stock al vender | `registrar_venta()` | Decrementa `Stock` por cada item del carrito |
| Estado de pago | `_normalizar_estado_pago()` | `Pagado` (abono≥total), `Pendiente` (abono=0), `Abono parcial` |
| Precio desde costo + margen | `precio_con_margen()` | `P = C / (1 - m)` (no `C·(1+m)`) |
| Normalización SKU | `normalizar_id_producto()` | strip, upper, sin ceros a la izquierda; `"01-ABC.5" → "1ABC5"` |
| Currency | `clean_currency()` | Todo a `int` (COP sin decimales) |
| Timezone | `now_co()` | `America/Bogota` siempre |
| RFM Loyalty | `procesar_inteligencia_df()` | 0-30 Activo / 31-60 Alerta / 61-90 Riesgo / >90 Perdido |
| Reorden | `Compras.calcular_master_df()` | `(vel_día × 5) + (vel_día × 1)` |
| ABC | `_calc_clase_abc()` | 80% rev = A, 95% = B, resto = C |

---

## 6. CACHING / SESSION STATE

- `st.cache_resource(ttl=3600)`: conexión gspread principal.
- `st.cache_resource(ttl=600)`: `conectar_crm()` en Loyalty, `conectar_db()` en Compras.
- `st.cache_data(ttl=120)`: catálogos en Compras.
- **`st.session_state.db`** = single source of truth in-memory para POS y dashboards (`inv`, `cli`, `ven`, `gas`, `cie`).
- **`st.session_state.data_store`** = duplicado parcial usado por Compras/Inventario_Nexus/Producto_360 (acoplamiento implícito).

⚠️ Hay **dos contenedores paralelos** (`db` y `data_store`) con datos similares y sin sincronización formal entre sí.

---

## 7. POSTURA DE SEGURIDAD

| Aspecto | Estado |
|---------|--------|
| Hardcoded secrets | ✅ Ninguno detectado |
| Auth de usuario | 🔴 No existe (público o protegido sólo por Streamlit Cloud SSO si aplica) |
| RBAC | 🔴 No existe |
| Audit log | 🔴 No existe |
| Validación de input | 🟡 Parcial (parseo defensivo de currency/fechas) |
| Sanitización para Sheets | 🟡 `sanitizar_para_sheet()` existe pero limitada |
| Rotación de secretos | 🔴 No definida |
| Backup | 🟡 Sólo versionado nativo de Google Sheets (30 días) |
| HTTPS/TLS | 🟢 Provisto por hosting |

---

## 8. POSTURA DE OBSERVABILIDAD

| Aspecto | Estado |
|---------|--------|
| Logs estructurados | 🔴 No |
| Métricas | 🔴 No |
| Traces | 🔴 No |
| Alertas | 🔴 No |
| Audit trail de escrituras | 🔴 No |
| Errores en UI | 🟡 `st.error()` efímero |

---

## 9. POSTURA DE CALIDAD

| Aspecto | Estado |
|---------|--------|
| Tests unitarios | 🔴 0 archivos |
| Tests integración | 🔴 0 |
| Linter / formatter | 🔴 No configurado (no hay ruff/black/flake8) |
| Type hints | 🟡 Esporádicos |
| Pre-commit hooks | 🔴 No |
| CI/CD | 🔴 No detectado |
| Versionado de deps | 🔴 `requirements.txt` sin pinning |

---

## 10. RIESGOS PRIORITARIOS (top 10)

| # | Riesgo | Severidad | Probabilidad |
|---|--------|-----------|--------------|
| 1 | Atomicidad venta+stock no garantizada | 🔴 Alta | Media |
| 2 | Race conditions con múltiples usuarios | 🔴 Alta | Alta (si >1 user) |
| 3 | Quota Google Sheets API (429) escalando | 🟠 Media-Alta | Media |
| 4 | Sin auth → cualquiera con la URL accede | 🔴 Alta | Depende de hosting |
| 5 | Dos session_state paralelos (`db` vs `data_store`) | 🟠 Media | Alta |
| 6 | Sin tests → regresiones silenciosas | 🟠 Media | Alta |
| 7 | Sin audit log → no trazabilidad ante disputa | 🟠 Media | Media |
| 8 | Renombrar producto huérfana ventas | 🟡 Media | Baja |
| 9 | Service account sin rotación | 🟡 Media | Baja |
| 10 | WeasyPrint puede fallar en deploy → fallback no probado | 🟡 Baja | Media |

---

## 11. QUICK WINS (acción inmediata sin migración)

1. Crear `utils.py` y consolidar `clean_currency`, `normalizar_id_producto`, `_find_col`, `money_int/float`, `_norm_col`, `_safe_to_datetime`. (5 copias hoy → 1).
2. Pinear versiones en `requirements.txt`.
3. Activar logging estructurado a archivo o a una tab `Audit_Log` del spreadsheet.
4. Añadir `ruff` + `black` + pre-commit.
5. Añadir validación de teléfono colombiano y email en CRM.
6. Quitar `twilio` de `requirements.txt` (no usado) o implementarlo.
7. Documentar variables de `st.secrets` en `project-secrets/`.
8. Añadir badge de versión y commit hash visible en sidebar para trazabilidad.
9. Reemplazar usos restantes de `ws.find()` por índices precomputados.
10. Crear export diario automático (CSV/Parquet) del spreadsheet a almacenamiento externo.

---

## 12. CONCLUSIÓN

El sistema actual es **funcional y entrega valor real al negocio**, pero su arquitectura (Streamlit + Sheets) está al límite para soportar:

- Más de 1–2 usuarios concurrentes haciendo escritura.
- Crecimiento >50.000 ventas históricas.
- Requerimientos de auditoría / RBAC / multi-tenant.
- E-commerce público integrado.

➡️ **Recomendación:** ejecutar el plan descrito en [MIGRATION_MASTER_PLAN.md](MIGRATION_MASTER_PLAN.md) en modo **strangler fig**, manteniendo Streamlit como sistema principal hasta validar la nueva plataforma.
