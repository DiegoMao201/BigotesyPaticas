# Bigotes y Paticas — Storefront (Next.js 14)

E-commerce premium con estética inspirada en Apple, Linear y Tesla.

## Desarrollo

```bash
pnpm install
cp .env.example .env.local
pnpm dev   # http://localhost:3000
```

## Features

- App Router + RSC + Server Components data fetching
- Tailwind con design tokens propios (paleta brand naranja)
- Dark mode via next-themes
- Carrito persistente con Zustand
- SEO: metadata API, sitemap, robots
- Animaciones con framer-motion

## Rutas

- `/` Home con hero, categorías, destacados, CTA
- `/categorias/[slug]` Listado por categoría
- `/producto/[slug]` PDP con galería, descripción, add to cart
- `/carrito` Carrito con resumen
- `/checkout` Placeholder (pasarela próximo sprint)
- `/cuenta` Cuenta de cliente
- `/nosotros` Página institucional

## Deploy en Coolify

- Build pack: Nixpacks
- Build command: `pnpm build`
- Start command: `pnpm start`
- Port: 3000
- Domain: `bigotesypaticas.com`
- ENV: `NEXT_PUBLIC_API_BASE_URL`
