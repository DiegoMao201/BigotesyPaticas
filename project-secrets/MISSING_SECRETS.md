# MISSING_SECRETS.md

> Inventario vivo de secretos / credenciales que la nueva plataforma necesitará.
> Marcar cada item cuando esté provisto. Cualquier ítem en `PUT_VALUE_HERE` puede desacoplarse temporalmente con un mock o adapter.

---

## ESTADO ACTUAL (Streamlit legacy)

| Secreto | Estado | Notas |
|---------|--------|-------|
| `SHEET_URL` | ✅ provisto en `st.secrets` | URL del spreadsheet maestro |
| `google_service_account` | ✅ provisto en `st.secrets` | Service account con permisos read/write sobre el sheet |

Sin secretos faltantes para que la app actual siga corriendo.

---

## NECESARIOS PARA LA NUEVA PLATAFORMA (F1 en adelante)

### 🔴 BLOQUEANTES para arrancar la API
| Variable | Dónde se obtiene | Estado | Bypass temporal |
|----------|------------------|--------|------------------|
| `POSTGRES_PASSWORD` | Generar con `openssl rand -base64 32` | ❌ pendiente | Usar SQLite local sólo para prototipo |
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` | ❌ pendiente | Generar al primer deploy |
| `SHEET_URL` (replicada para ETL) | Reusar la del Streamlit legacy | ✅ disponible | – |
| `GOOGLE_SERVICE_ACCOUNT_JSON` (read-only para ETL) | Crear en Google Cloud Console → IAM → Service Accounts → Keys | ❌ pendiente | Reusar SA actual con read/write hasta crear el RO |

### 🟠 NECESARIOS para fase F4 (e-commerce / pagos)
| Variable | Dónde | Estado | Bypass |
|----------|-------|--------|--------|
| `PAYMENTS_PROVIDER` | Decisión de negocio (Wompi / MP / Stripe) | ❌ pendiente decisión | Dejar checkout en modo "transferencia" mientras se elige |
| `PAYMENTS_API_KEY/SECRET` | Dashboard del proveedor elegido | ❌ pendiente | Usar adapter mock con `payments_provider=mock` |
| `PAYMENTS_WEBHOOK_SECRET` | Mismo dashboard | ❌ pendiente | Idem |
| `WHATSAPP_API_TOKEN` | Meta for Developers → WhatsApp Cloud API | ❌ pendiente | Seguir generando links `wa.me/...` como hoy |
| `WHATSAPP_PHONE_NUMBER_ID` | Idem | ❌ pendiente | Idem |

### 🟡 RECOMENDADOS (observabilidad y storage)
| Variable | Dónde | Estado | Bypass |
|----------|-------|--------|--------|
| `S3_ACCESS_KEY/SECRET` | MinIO en Coolify (auto-genera) | ❌ pendiente | Almacenar PDFs en filesystem local del worker |
| `SENTRY_DSN` | sentry.io o instancia self-hosted | ❌ pendiente | Logs a stdout + Loki bastan en F1 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Tempo/Jaeger en Coolify | ❌ pendiente | Desactivar tracing inicial |

---

## INFRAESTRUCTURA PENDIENTE (no son secretos pero son necesarios)

| Recurso | Estado | Acción |
|---------|--------|--------|
| Instancia PostgreSQL en Coolify | ❌ | Provisionar PG16 + replica + WAL archiving |
| Instancia Redis | ❌ | Provisionar Redis 7 |
| MinIO / S3 | ❌ | Provisionar bucket `bigotesypaticas` |
| Dominios DNS (`api.`, `tienda.`, `staging.`) | ❌ | Configurar en proveedor DNS |
| GHCR access token | ❌ | Crear en GitHub para publicar imágenes |
| Coolify API token | ❌ | Generar en Coolify para CI/CD |

---

## REGLAS

1. **Mientras un secreto esté pendiente**, el módulo correspondiente debe:
   - Detectar la ausencia (`if not os.getenv("...")`).
   - Activar un adapter mock o desactivarse limpiamente con log de WARNING.
   - **Nunca** detener la app entera por una credencial opcional faltante.
2. Cuando un secreto se provea, mover su línea en este archivo a "✅" y registrar la fecha.
3. El usuario es la única persona que puede aprobar el provisionamiento de credenciales reales en producción.
