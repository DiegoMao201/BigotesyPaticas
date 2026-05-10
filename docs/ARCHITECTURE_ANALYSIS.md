# ARCHITECTURE_ANALYSIS.md

## 1. ARQUITECTURA ACTUAL (AS-IS)

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser (usuario interno)               │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Streamlit Runtime (single process, single host)            │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  BigotesyPaticas.py (entry / POS / sync)            │    │
│  ├──────────────┬──────────────┬─────────────┬─────────┤    │
│  │ Analisis_    │ Compras.py   │ Inventario_ │ ...     │    │
│  │ financiero   │              │ Nexus       │         │    │
│  └──────────────┴──────────────┴─────────────┴─────────┘    │
│                                                              │
│  st.session_state.db        st.session_state.data_store     │
│  (POS/Loyalty/Dashboard)    (Compras/Inv/Producto360)       │
│                                                              │
│  gspread client (cached 1h) ──► WeasyPrint / ReportLab      │
└──────────────────────────┬──────────────────────────────────┘
                           │ Google Sheets API
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  Google Spreadsheet (master)                                │
│  Inventario | Clientes | Ventas | Gastos | Cierres |        │
│  Maestro_Proveedores | Historial_Ordenes                    │
└─────────────────────────────────────────────────────────────┘
```

### Características
- **Topología:** monolito de página única (Streamlit) + backend "documental" (Sheets).
- **Estado:** in-memory por sesión + spreadsheet como persistencia.
- **Acoplamiento:** alto (todas las páginas leen el mismo `session_state` y conocen los nombres de columnas).
- **Despliegue:** un único proceso Python; sin separación frontend/backend.
- **Concurrencia:** single-writer asumido (no garantizado).
- **Escalabilidad:** vertical (un host) — horizontal imposible (estado en memoria local).

---

## 2. PRINCIPIOS RECTORES PARA LA NUEVA ARQUITECTURA

1. **Strangler Fig** — la app actual sigue viva; la nueva crece a su lado y absorbe módulos uno a uno.
2. **Domain-Driven Design ligero** — bounded contexts: `pos`, `inventory`, `customers`, `purchasing`, `finance`, `loyalty`, `ecommerce`.
3. **API-first** — toda lógica de negocio detrás de una API HTTP versionada (`/api/v1/...`).
4. **Source of truth única** — PostgreSQL. Google Sheets degrada a herramienta de captura/lectura humana opcional.
5. **Stateless services** — autenticación por JWT/cookie segura; nada de estado en memoria por usuario.
6. **Idempotencia y atomicidad** — toda operación crítica (venta, ajuste de stock, pago) es transaccional y reintenable.
7. **Observabilidad por defecto** — logs estructurados + métricas + traces desde el día 1.
8. **Seguridad por defecto** — auth obligatoria, RBAC, rate limiting, audit log, secrets gestionados.
9. **Mobile-first y SEO-ready** — frontend Next.js con SSR y App Router.
10. **Cero downtime durante la migración** — feature flags, dual-write controlado, rollback documentado.

---

## 3. ARQUITECTURA OBJETIVO (TO-BE)

```
                       ┌──────────────────────┐
                       │   Cloudflare / CDN   │
                       └──────────┬───────────┘
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        │                                                    │
        ▼                                                    ▼
┌──────────────────┐                            ┌──────────────────────┐
│  Storefront      │                            │  Admin Panel         │
│  Next.js 14 SSR  │                            │  Next.js 14 (App)    │
│  (público B2C)   │                            │  panel.datovate...   │
└────────┬─────────┘                            └──────────┬───────────┘
         │                                                  │
         │            REST + Webhooks                       │
         └─────────────────┬────────────────────────────────┘
                           ▼
              ┌────────────────────────────┐
              │   API Gateway / BFF        │
              │   FastAPI (Python)         │
              │   - Auth (JWT + refresh)   │
              │   - RBAC                   │
              │   - Rate limit             │
              │   - OpenAPI docs           │
              └────────────┬───────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│ Domain svcs  │  │ Workers      │  │ Integrations     │
│ (pos, inv,   │  │ (RQ/Celery)  │  │ - Google Sheets  │
│ purchasing,  │  │ - ETL Sheets │  │   ETL legacy     │
│ finance,     │  │ - Reorden    │  │ - WhatsApp Cloud │
│ loyalty)     │  │ - PDF async  │  │ - Pasarela pago  │
└──────┬───────┘  └──────┬───────┘  └─────────┬────────┘
       │                  │                    │
       └──────────┬───────┴─────────┬──────────┘
                  ▼                 ▼
          ┌──────────────┐   ┌──────────────┐
          │ PostgreSQL   │   │ Redis        │
          │ (primary)    │   │ - cache      │
          │ + replicas   │   │ - queues     │
          └──────────────┘   └──────────────┘
                  │
                  ▼
          ┌──────────────┐
          │ Object store │
          │ (S3/MinIO)   │
          │ facturas PDF │
          │ imágenes     │
          └──────────────┘

┌─────────────────────────────────────────────────────────┐
│ Streamlit actual sigue corriendo en paralelo            │
│ leyendo/escribiendo Sheets durante la transición.       │
│ Worker ETL sincroniza Sheets ⇄ PostgreSQL hasta cutover.│
└─────────────────────────────────────────────────────────┘
```

---

## 4. BOUNDED CONTEXTS Y MICRO-MÓDULOS

| Contexto | Responsabilidad | Tablas principales |
|----------|------------------|----------------------|
| `identity` | usuarios, roles, sesiones | `users`, `roles`, `permissions`, `audit_log` |
| `catalog` | productos, categorías, proveedores | `products`, `categories`, `suppliers`, `supplier_products` |
| `inventory` | stock, movimientos, conteos | `stock_movements`, `physical_counts`, `warehouses` |
| `customers` | clientes, mascotas, segmentos RFM | `customers`, `pets`, `customer_segments` |
| `pos` | ventas, líneas, pagos, cierres | `sales`, `sale_items`, `payments`, `cash_closures` |
| `purchasing` | OC, recepciones, gastos | `purchase_orders`, `po_items`, `expenses` |
| `finance` | cuentas por cobrar, KPIs | `accounts_receivable`, `kpi_snapshots` |
| `loyalty` | campañas, mensajes, eventos | `campaigns`, `messages`, `events` |
| `ecommerce` | catálogo público, carritos, órdenes | `cart`, `orders`, `shipments` |

---

## 5. ESTRATEGIA DE COEXISTENCIA (Streamlit ⇄ nueva plataforma)

| Fase | Streamlit | Nueva plataforma | Sheets | Postgres |
|------|-----------|------------------|--------|----------|
| F0 — actual | Read/Write | — | Master | — |
| F1 — sombra | Read/Write | Read-only espejo | Master | Réplica vía ETL |
| F2 — dual-write controlado | Read/Write | Read/Write feature-flagged | Master | Sincronizado |
| F3 — flip por módulo | Read-only en módulos migrados | Read/Write principal | Read-only | Master |
| F4 — cutover total | Apagar o congelar | Master | Backup | Master |

Cada flip es **reversible** vía feature flag y se valida con reconciliación diaria.

---

## 6. DECISIONES ARQUITECTÓNICAS CLAVE (ADR resumido)

| ADR | Decisión | Razón |
|-----|----------|--------|
| 001 | **PostgreSQL** sobre MySQL/SQLite | JSONB, FTS, particionado, ecosistema maduro |
| 002 | **FastAPI** sobre NestJS | Equipo Python, reuso de lógica actual, async nativo |
| 003 | **Next.js 14 App Router** | SSR/SEO, RSC, ecosistema Vercel/Coolify |
| 004 | **TypeScript** estricto | Contratos sólidos con la API |
| 005 | **JWT con refresh tokens en httpOnly cookies** | Seguridad + simplicidad |
| 006 | **Alembic** para migraciones | Estándar de SQLAlchemy |
| 007 | **RQ** (Redis Queue) sobre Celery | Más liviano, suficiente para el caso |
| 008 | **MinIO/S3** para PDFs e imágenes | Desacopla almacenamiento de cómputo |
| 009 | **OpenTelemetry** + Grafana/Loki | Stack open-source homogéneo |
| 010 | **Coolify** sigue siendo el orquestador | Usuario ya lo administra |

---

## 7. NO-OBJETIVOS (out of scope inicial)

- Multi-tenant SaaS (se diseña preparado pero no se activa).
- Internacionalización (i18n) — se queda en español hasta nuevo aviso.
- App móvil nativa — el storefront Next.js + PWA cubre.
- Migración de invoices históricos (queda como proyecto separado).
