# Bigotes y Paticas

**Plataforma completa de retail para mascotas, en operación real.** Tienda en línea,
portal de fidelización instalable (PWA), panel de administración y API — cuatro
aplicaciones sobre un solo modelo de datos.

Empresa propia de **[Diego Mauricio García R.](https://www.datovatenexuspro.com)**,
Dosquebradas, Risaralda. Es el caso donde no hay que pedirle a nadie que me crea: el
cliente soy yo, y las consecuencias de cada decisión técnica las pago yo.

> **Estado:** en producción. El monorepo (Next.js + FastAPI + PostgreSQL) ya opera; la
> aplicación original en Streamlit queda como pieza de respaldo durante la última fase de
> la migración.

---

## La necesidad

Competir en digital con las cadenas grandes sin el presupuesto de una cadena grande:
vender en línea, fidelizar con puntos y referidos, agendar servicios y administrar todo
desde un solo panel.

**La restricción:** presupuesto y equipo de una pyme real. Cada componente tenía que
pagarse solo. Nada de arquitectura de startup financiada — ingeniería de negocio que
factura.

## Arquitectura

| Aplicación | Qué es |
|---|---|
| [`apps/store`](apps/store) | Tienda en línea, catálogo y contenido indexable |
| [`apps/portal`](apps/portal) | Portal de fidelización instalable (PWA): puntos, referidos, mascotas, citas |
| [`apps/admin`](apps/admin) | Administración de la operación |
| [`apps/aliados`](apps/aliados) | Acceso para aliados |
| [`apps/api`](apps/api) | API en FastAPI sobre PostgreSQL, con contextos separados para CRM, catálogo y ventas |

**Monorepo con Turborepo.** Un solo modelo de datos, contextos separados. Catálogo
sincronizado automáticamente con Meta. SEO técnico completo: más de mil URLs indexables,
datos estructurados válidos y sitemap vivo.

`172` archivos TypeScript/React · `179` Python · Next.js · FastAPI · PostgreSQL · PWA

## Resultado

- **434 clientes** y **1.456 pedidos** gestionados por el sistema.
- Programa de puntos y referidos operando solo: registra, acumula y premia sin
  intervención manual.
- **467 productos** que se actualizan solos.
- Cierre de caja diario sistematizado y agendamiento de servicios en línea.

---

## Reglas de oro para colaboradores (humanos o IA)

1. **No se apaga lo que está operando.** Ningún cambio destructivo en producción.
2. **Toda decisión arquitectónica** se registra en [docs/project-continuity.md](docs/project-continuity.md).
3. **Secretos jamás en el repo.** Solo plantillas `*.example` en [project-secrets/](project-secrets/).
4. **La lógica de negocio crítica** se preserva 1:1 hasta tener pruebas golden.
5. Cualquier cambio de módulo debe ser **reversible en menos de 5 minutos** vía feature flag.

## Documentación

[docs/project-continuity.md](docs/project-continuity.md) — decisiones vigentes y bitácora ·
[docs/SYSTEM_AUDIT.md](docs/SYSTEM_AUDIT.md) — estado real ·
[docs/ARCHITECTURE_ANALYSIS.md](docs/ARCHITECTURE_ANALYSIS.md) — AS-IS y TO-BE ·
[docs/MIGRATION_MASTER_PLAN.md](docs/MIGRATION_MASTER_PLAN.md) — fases

---

**¿Tu operación necesita algo parecido?**
[datovatenexuspro.com](https://www.datovatenexuspro.com) · diegomao.201@gmail.com ·
WhatsApp +57 320 504 6277
