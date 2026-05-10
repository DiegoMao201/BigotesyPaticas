# FRONTEND_STRATEGY.md

## 1. STACK

- **Next.js 14** (App Router, RSC).
- **TypeScript** estricto (`"strict": true`, `noUncheckedIndexedAccess`).
- **Tailwind CSS** + **shadcn/ui** (Radix + Tailwind primitives).
- **TanStack Query** para fetching/cache cliente.
- **Zustand** para estado UI ligero (carrito, drawers).
- **react-hook-form** + **zod** para formularios y validación.
- **next-intl** preparado para i18n (no activado v1).
- **Auth.js (NextAuth)** o auth propia con cookies httpOnly emitidas por la API.

## 2. APLICACIONES

```
apps/
├── admin/        # Panel administrativo interno (panel.datovatenexuspro.com)
├── store/        # Storefront público B2C
└── streamlit/    # App actual (legacy, mantener vivo)
packages/
├── ui/           # Componentes compartidos (shadcn-based)
├── api-types/    # Tipos generados desde OpenAPI
├── api-client/   # Cliente fetch tipado
└── config/       # eslint/tsconfig/tailwind preset
```

Monorepo con **pnpm workspaces** + **Turborepo**.

## 3. ADMIN PANEL

### Módulos (1 ruta por bounded context)
- `/dashboard` — KPIs cross-módulo.
- `/pos` — POS web (replica de Streamlit).
- `/sales` — listado, detalle, abonos, envíos.
- `/customers` — CRM, mascotas, segmentos RFM.
- `/inventory` — stock, conteo físico, ajustes.
- `/products` — catálogo, precios, categorías.
- `/purchasing` — órdenes, recepción, proveedores.
- `/finance` — gastos, cierres, cuentas por cobrar.
- `/loyalty` — campañas, mensajes, calendario.
- `/settings` — usuarios, roles, feature flags, integraciones.

### Patrones
- Server Components por defecto; Client Components sólo donde haga falta interactividad.
- Server Actions para mutaciones simples; React Query para flujos complejos (POS).
- Layouts compartidos por contexto.
- Tablas con server-side pagination + filtros sincronizados a URL.
- Atajos de teclado en POS (F2 cliente, F3 producto, F8 cobrar, Esc cancelar).
- Escaneo de códigos de barras vía input invisible enfocado.

### Rendimiento
- ISR para vistas que no cambian seguido (`/products` admin lista).
- `revalidateTag` cuando la API publica eventos de invalidación.
- Streaming + Suspense en dashboards.

## 4. STOREFRONT (E-COMMERCE)

### Rutas clave
- `/` — home con destacados.
- `/c/[slug]` — categorías.
- `/p/[slug]` — ficha de producto.
- `/buscar` — búsqueda con FTS de la API.
- `/carrito`, `/checkout`, `/pedido/[id]`.
- `/mi-cuenta` (cliente final).

### Características
- SSR completo + metadatos OG/Twitter por producto.
- Sitemap.xml dinámico desde la API.
- Schema.org Product + Offer + Organization.
- Imágenes optimizadas vía `next/image` con loader hacia MinIO/CDN.
- Stock en tiempo real vía SWR/Query con `staleTime` corto y revalidación al focus.
- Carrito persistido en cookie (anónimo) + sincronizado con backend al login.
- PWA installable (manifest + service worker básico).
- Pagos: integración a definir (Wompi / Mercado Pago / Stripe). Diseño desacoplado mediante `payments adapter`.

### SEO
- Meta dinámica por producto y categoría.
- Slugs estables en `legacy_id_map`.
- Open Graph + Twitter Cards.
- robots.txt y canonical correctos.
- Lighthouse objetivos: Performance ≥ 90, SEO 100, Accessibility ≥ 95.

## 5. AUTENTICACIÓN

- Login interno (`/admin/login`) → POST a la API → cookies httpOnly.
- Storefront usa misma API con scope `customer`.
- Middleware de Next.js protege rutas `/admin/*` con verificación de cookie + permiso.
- 2FA opcional para roles admin/manager (TOTP) — preparado en backend, activable en F5+.

## 6. UX / DISEÑO

- Sistema de diseño en `packages/ui` con tokens (colores, spacing, tipografía).
- Modo claro por defecto; dark mode disponible.
- Componentes accesibles (Radix + WAI-ARIA).
- Mensajería de error y éxito unificada (`<Toast/>`, `<Alert/>`).
- Skeletons en lugar de spinners donde aplique.

## 7. TESTING

- **Vitest** para unit / hooks.
- **React Testing Library** para componentes.
- **Playwright** para E2E (smoke en CI, suite completa nocturna).
- **Storybook** para componentes de `packages/ui`.

## 8. CONTRATOS CON LA API

- Tipos generados desde OpenAPI en cada build (`pnpm gen:api`).
- Cliente tipado expuesto en `packages/api-client`.
- Errores normalizados y mapeados a `<Toast/>` + sentry breadcrumb.
