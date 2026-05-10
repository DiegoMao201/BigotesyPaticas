# Incidente 2026-05-10 — Secretos reales pegados en `.env.production.example`

## Resumen

Durante la sesión del 2026-05-10, se detectó que el archivo `project-secrets/.env.production.example` (versionado en git) fue editado con **valores reales de producción** apendiados al final de las plantillas con placeholders.

## Secretos expuestos en disco local (ANTES de cualquier commit)

| Tipo | Servicio |
|------|----------|
| Private key + cliente | Google Service Account (`robot-portal-ferreinox@formulario-de-datos-465801.iam.gserviceaccount.com`) |
| App Password | Gmail (`bigotesypaticasdosquebradas@gmail.com`) |
| Password | Postgres (DB existente y DB nueva) |
| API key | OpenRouter (`sk-or-v1-...`) |
| Access/Secret keys | DigitalOcean Spaces |
| `DATABASE_URL` | Conexión completa con password embebido |
| `AUTH_SECRET` | NextAuth dev-secret |

## Estado de exposición

- ✅ **No se commitearon ni pushearon a GitHub.** El último commit en `origin/main` es `e99f6dd` y NO contiene los secretos (verificado con `git log` + diff).
- ⚠️ **Existieron en el filesystem local**, en el portapapeles, y en cualquier herramienta del editor que haya leído el archivo.

## Mitigación inmediata aplicada

1. Los valores reales se movieron a `project-secrets/.env.production` (que está en `.gitignore` desde antes).
2. `project-secrets/.env.production.example` se restauró con placeholders limpios.
3. Se añadió `.gitleaks.toml` con reglas custom para detectar futuros pegados accidentales (Google private key, OpenRouter, DO Spaces, Gmail App Passwords).
4. Se añadió hook pre-commit `gitleaks` que bloquea commits con secretos.
5. Se añadió job `secrets-scan` en CI (`.github/workflows/ci.yml`) que escanea cada PR.

## Acciones recomendadas al usuario (NO ejecutadas — requieren intervención humana)

| Prioridad | Acción |
|-----------|--------|
| 🔴 Alta | **Rotar el Google Service Account**: crear nueva key en GCP Console → IAM → Service Accounts → cargarla en Streamlit Cloud y/o Coolify → eliminar la key vieja |
| 🔴 Alta | **Rotar el password de Postgres** del usuario `postgres` en la instancia NYC1 |
| 🔴 Alta | **Revocar y regenerar las DigitalOcean Spaces keys** |
| 🟠 Media | Generar un nuevo Gmail App Password y revocar el anterior |
| 🟠 Media | Rotar la OpenRouter API key |
| 🟡 Baja | Cambiar `AUTH_SECRET` (era dev-secret de todos modos) |

Comandos de ayuda:
```bash
# Generar nuevos secretos
openssl rand -base64 32                              # passwords / AUTH_SECRET / JWT_SECRET
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

## Lecciones / cambios estructurales

- Los `.example` sólo contienen placeholders. Cualquier valor real va a `.env*` (gitignored) o directamente a Coolify/Streamlit Cloud.
- `gitleaks` es ahora obligatorio (pre-commit + CI).
- Para futuras sesiones de IA: si el usuario pega secretos, alertar y mover a archivo gitignored automáticamente, como se hizo aquí.

## Verificación final

```bash
git log --all --full-history -- project-secrets/.env.production.example | head
git show e99f6dd:project-secrets/.env.production.example | grep -E "BEGIN PRIVATE|sk-or-v1" || echo "OK: no secrets in commit history"
```
