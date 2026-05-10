# SECRETS_SETUP.md

> Guía operativa para gestionar secretos en BigotesyPaticas.
> **Nunca commitear archivos `.env`, `.env.local`, `.env.production` ni JSON de service accounts.** Sólo plantillas `*.example`.

---

## 1. ARCHIVOS DE ESTE DIRECTORIO

| Archivo | Estado git | Propósito |
|---------|------------|-----------|
| `.env.example` | ✅ commit | Plantilla genérica con todas las variables soportadas |
| `.env.local.example` | ✅ commit | Plantilla para desarrollo local |
| `.env.production.example` | ✅ commit | Plantilla para producción (Coolify) |
| `SECRETS_SETUP.md` | ✅ commit | Esta guía |
| `MISSING_SECRETS.md` | ✅ commit | Inventario de secretos faltantes y dónde obtenerlos |
| `.env`, `.env.local`, `.env.production` | ❌ NUNCA commit | Valores reales (vivirán fuera del repo) |
| `google-service-account*.json` | ❌ NUNCA commit | Credenciales OAuth |

---

## 2. STREAMLIT LEGACY

La app actual lee secretos desde `st.secrets`. Hay dos modos:

### 2.1 Streamlit Cloud
Configurar en `Settings → Secrets`:

```toml
SHEET_URL = "https://docs.google.com/spreadsheets/d/<ID>/edit"

[google_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "...@....iam.gserviceaccount.com"
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

### 2.2 Local
Crear `.streamlit/secrets.toml` con el mismo contenido (ya está en `.gitignore`).

---

## 3. NUEVA PLATAFORMA (FastAPI + Next.js)

### 3.1 Local
1. Copiar `project-secrets/.env.local.example` → `.env.local` en la raíz del repo (o por app cuando exista monorepo).
2. Reemplazar `PUT_VALUE_HERE` con valores reales.
3. Para Google Sheets dev: usar un spreadsheet de pruebas (NUNCA el de producción).

### 3.2 Producción (Coolify)
- Cargar variables en Coolify por cada servicio (api, admin-web, store-web, worker, scheduler).
- Usar la UI de Coolify, no archivos planos en el host.
- Activar "encrypted at rest" en Coolify.

---

## 4. GENERAR SECRETOS NUEVOS

| Secreto | Cómo generar |
|---------|--------------|
| `JWT_SECRET` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_PASSWORD` | `openssl rand -base64 32` |
| `S3_ACCESS_KEY` / `S3_SECRET_KEY` | UI de MinIO o `mc admin user add` |
| `WHATSAPP_API_TOKEN` | Meta for Developers → WhatsApp → System User token |
| `PAYMENTS_*` | Dashboard del proveedor (Wompi, Mercado Pago, Stripe) |
| `SENTRY_DSN` | Sentry project settings → Client Keys |

---

## 5. ROTACIÓN

| Secreto | Frecuencia | Procedimiento |
|---------|------------|---------------|
| Google Service Account | trimestral | Crear key nueva en GCP Console → cargar en Coolify → eliminar key vieja |
| `JWT_SECRET` | cuatrimestral | Rotar con ventana de gracia (aceptar firma vieja N días) |
| Postgres `app_rw` | semestral | `ALTER USER app_rw WITH PASSWORD 'nuevo';` + actualizar Coolify |
| S3 keys | semestral | Crear par nuevo en MinIO → switch → revocar viejo |
| Webhooks (`PAYMENTS_WEBHOOK_SECRET`) | al detectar incidente | Coordinar con el proveedor |

---

## 6. POLÍTICA

- **Mínimo privilegio:** cada servicio recibe sólo los secretos que necesita.
- **Logs nunca imprimen secretos** — usar redacción automática (`structlog` filter).
- **`gitleaks` corre en pre-commit y en CI** para bloquear secretos accidentalmente añadidos.
- **Si un secreto se filtra:** rotar de inmediato, registrar incidente en `docs/RUNBOOKS.md` (a crear), revisar logs de uso.

---

## 7. CHECKLIST RÁPIDO

- [ ] Copiar `.env.example` → `.env` y completar.
- [ ] Para Streamlit Cloud: configurar secrets en su UI.
- [ ] Para Coolify: cargar `.env.production.example` adaptado, NO subir el archivo al host.
- [ ] Verificar `gitleaks` corre en pre-commit.
- [ ] Confirmar que `.env*` (excepto `.example`) están ignorados por git (`git check-ignore -v .env`).
