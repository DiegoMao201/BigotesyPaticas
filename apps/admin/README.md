# Bigotes y Paticas — Admin Panel (Next.js 14)

## Desarrollo

```bash
pnpm install
cp .env.example .env.local
pnpm dev   # http://localhost:3001
```

## Producción

```bash
pnpm build && pnpm start
```

## Stack

- Next.js 14 App Router + React 18 + TypeScript estricto
- Tailwind 3 + design tokens propios + tailwindcss-animate
- TanStack Query · Zustand · NextThemes · Sonner
- Recharts · Framer Motion · Lucide

## Estructura

```
src/
  app/
    layout.tsx               # Root con Providers
    page.tsx                 # Redirect → /dashboard
    globals.css
    (auth)/login/page.tsx    # Login con bg gradient mesh
    (dashboard)/
      layout.tsx             # Auth guard + Sidebar
      dashboard/page.tsx
      products/page.tsx
      sales/page.tsx
      inventory/page.tsx
      customers/page.tsx
      analytics/page.tsx
      settings/page.tsx
  components/
    providers.tsx            # QueryClient + ThemeProvider + Toaster
    sidebar.tsx
    ui/{button,card,input}.tsx
  lib/
    api.ts                   # Cliente HTTP tipado
    auth-store.ts            # Zustand session
    utils.ts                 # cn, formatCurrency, formatDate
```

## Deploy en Coolify

- Build pack: Nixpacks (auto Next.js)
- Build command: `pnpm build`
- Start command: `pnpm start`
- Port: 3001
- ENV: `NEXT_PUBLIC_API_BASE_URL`, `SESSION_SECRET`
