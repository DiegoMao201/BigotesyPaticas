# Sesión 3 — Deploy Autónomo Completo

**Fecha**: 2026-05-10  
**Modo**: FULL AUTONOMOUS DEPLOYMENT  
**Resultado**: ✅ Plataforma 100% operativa con datos demo, navegable end-to-end.

## 1. Resumen ejecutivo

Las 3 aplicaciones (`bp-api`, `bp-admin`, `bp-store`) están **deployed, healthy y servidas con HTTPS** detrás de Cloudflare. La storefront es navegable con 4 categorías, 4 marcas y 8 productos demo seedeados automáticamente en cada deploy. Backups diarios de PostgreSQL programados.

## 2. Deploys ejecutados

| App | UUID app | Último deployment | Estado |
|---|---|---|---|
| bp-api | `bcs404cksc0cksc0o0w04cc4` | `sws08sgocos440cso0w8o8ss` | ✅ Running healthy |
| bp-admin | `v0kog0sooooo4kk8ok8wscgg` | `y4co4k4ggosw8ow80kkskwo8` | ✅ Running |
| bp-store | `zgs00cw00ggsw0gcc0wo00kc` | `foc4wo440k8skwsg0w4owgs0` | ✅ Running |
| bp-postgres | `l0k0kck8cwck4goskcs0scsg` | n/a | ✅ Running healthy + backup `0 3 * * *` |
| bp-redis | `wc8kgcsgws8cc00oc4404cks` | n/a | ✅ Running healthy |

## 3. Bug crítico corregido

**Síntoma**: Build de `bp-admin` y `bp-store` fallaba con `Error TS5083: Cannot read file '/tsconfig.base.json'`.

**Causa**: Nixpacks copia únicamente `apps/<app>/` como contexto de build. El `extends: "../../tsconfig.base.json"` apuntaba fuera del contexto.

**Fix**: Inline de las opciones en cada `apps/admin/tsconfig.json` y `apps/store/tsconfig.json`, eliminando el `extends`. Commit `e10199c`.

## 4. Datos demo

Implementado `apps/api/app/cli/seed_catalog.py`:

- **4 categorías**: perros, gatos, accesorios, snacks
- **4 marcas**: Royal Canin, Pro Plan, Hill's Science Diet, Bigotes y Paticas
- **8 productos** publicados (`is_published=True`) con SKUs, slugs, precios COP, categorías y marcas reales

Idempotente vía `select(Model.slug == ...)` antes de insertar. Integrado al `CMD` del Dockerfile de la API (commit `0d420e6`):

```dockerfile
CMD ["sh", "-c", "alembic upgrade head && python -m app.cli.seed && python -m app.cli.seed_catalog && exec gunicorn ..."]
```

## 5. Pipeline de assets

Listo para producción (commit `7a87ad6`):

- `local-assets/` con `.gitignore` para binarios, 6 subcarpetas con `.gitkeep`
- `scripts/media/optimize_images.py` — PIL → WebP variantes (thumb/card/main/zoom), idempotente vía mtime
- `scripts/media/upload_to_spaces.py` — boto3, idempotente vía MD5/ETag, headers `Cache-Control: public, max-age=31536000, immutable`
- `scripts/media/validate_naming.py` — regex kebab-case ASCII
- `scripts/etl/sheets_to_pg.py` — scaffold con decorator `@handler(tab_name)` (mappings reales pendientes)
- `docs/IMAGE_NAMING_GUIDE.md` — convenciones, srcset responsive, anti-patrones

## 6. Auto-deploy (configuración pendiente en GitHub)

**Coolify ya está listo**: secret HMAC compartido configurado en las 3 apps:

```
SECRET = d57670b82d1908af9d239ae8079bf7ae4ec874185fc082e3e02ae5a4d889aaca
URL = https://panel.datovatenexuspro.com/webhooks/source/github/events/manual
```

**Acción manual del usuario** (1 paso, ~2 min):

1. Ir a https://github.com/DiegoMao201/BigotesyPaticas/settings/hooks/new
2. Payload URL: `https://panel.datovatenexuspro.com/webhooks/source/github/events/manual`
3. Content type: `application/json`
4. Secret: `d57670b82d1908af9d239ae8079bf7ae4ec874185fc082e3e02ae5a4d889aaca`
5. Events: `Just the push event`
6. Active: ✅
7. **Add webhook**

A partir de ese momento, cada `git push` a `main` redespliega automáticamente las 3 apps (Coolify detecta la coincidencia de repo+rama).

## 7. Backups

`bp-postgres` → Schedule `0 3 * * *` (diario a las 03:00 hora servidor). Sin S3 storage validado todavía, los backups quedan en el volumen del servidor. Cuando se valide un S3 Storage en Coolify, se puede asociar al schedule existente.

## 8. URLs en producción (todas verificadas con `curl -I`)

| URL | HTTP | Notas |
|---|---|---|
| https://api.bigotesypaticas.com/health | 200 | `{"status":"ok"}` |
| https://api.bigotesypaticas.com/health/ready | 200 | `{"status":"ok","db":"ok"}` |
| https://api.bigotesypaticas.com/docs | 200 | Swagger UI |
| https://api.bigotesypaticas.com/v1/categories | 200 | 4 cats |
| https://api.bigotesypaticas.com/v1/brands | 200 | 4 marcas |
| https://api.bigotesypaticas.com/v1/products | 200 | 8 productos |
| https://api.bigotesypaticas.com/v1/auth/login | 200 | JWT válido |
| https://admin.bigotesypaticas.com/login | 200 | Next.js admin |
| https://bigotesypaticas.com/ | 200 | Storefront home |
| https://www.bigotesypaticas.com/ | 200 | Alias |
| https://bigotesypaticas.com/categorias/{perros,gatos,accesorios,snacks} | 200 | 4/4 |
| https://bigotesypaticas.com/producto/{8 slugs} | 200 | 8/8 |
| https://bigotesypaticas.com/carrito | 200 | |
| https://bigotesypaticas.com/robots.txt + /sitemap.xml | 200 | |

## 9. Commits de esta sesión

- `7a87ad6` — feat(media): pipeline assets + ETL scaffolds + IMAGE_NAMING_GUIDE
- `e10199c` — fix(monorepo): tsconfig self-contained admin/store (Nixpacks)
- `3e00451` — feat(api): seed_catalog demo (8 productos, 4 cats, 4 marcas)
- `0d420e6` — chore(api): seed_catalog en CMD para datos demo automáticos

## 10. Siguientes acciones recomendadas

- [ ] Crear el webhook GitHub (paso #6) — desbloquea auto-deploy
- [ ] Validar un S3 Storage en Coolify y asociarlo al schedule de backups
- [ ] Subir imágenes reales de productos a `local-assets/products/<slug>/` y correr `python scripts/media/optimize_images.py && python scripts/media/upload_to_spaces.py`
- [ ] Implementar mappings reales en `scripts/etl/sheets_to_pg.py` según las tabs del Sheet legacy de Diego
- [ ] Subir favicon a `apps/store/src/app/` y `apps/admin/src/app/`
- [ ] Configurar notificaciones Coolify (email/webhook) para fallos de deploy
