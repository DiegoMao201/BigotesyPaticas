# DESIGN_SYSTEM.md — Bigotes y Paticas

> Sistema de diseño para portal cliente (web + iOS + Android empaquetado con Capacitor) y app aliados. **Objetivo:** que la app se sienta a la altura de Airbnb, Apple Health, Linear o Duolingo — moderna, cálida, profesional, sin ruido visual.

---

## 1. FILOSOFÍA VISUAL

**Cinco principios no negociables:**

1. **Whitespace es la feature.** El 40% de cada pantalla es aire. Nunca rellenar por rellenar.
2. **Tipografía dominante.** Un solo H1 grande por pantalla manda la jerarquía. Nada de "banner + subheading + hero + subtítulo" apilados.
3. **Color-coding por dominio.** Cada dominio (mascota, salud, SOS, adopción, servicios, tienda) tiene su ramp. El usuario reconoce la pantalla por el color antes de leer.
4. **Cero shadows dramáticas, cero gradientes.** Surface plana + border 0.5-1px + tipografía + color. Estilo Linear / Notion / Apple Human Interface actual.
5. **Micro-interacciones por defecto.** Todo lo que se puede animar suavemente, se anima. Nunca cambios abruptos.

**Referencias visuales exactas:**

- Airbnb móvil (2024+) — grid de cards, hero photography, filtros pill.
- Apple Health — tipografía enorme para métricas, timeline vertical.
- Linear — sidebar, densidad tipográfica, transiciones sutiles.
- Duolingo — mascota + gamification para el módulo de loyalty (puntos).
- Instagram Stories — cámara + reportar SOS en un flujo de 3 taps.
- Google Maps — directorio de veterinarias/paseadores.

---

## 2. PALETA (mapeada al `color_theme` que ya existe en `portal.pets`)

Cada mascota ya tiene un `color_theme` de 6 opciones. Reusa esos colores como sistema global:

| Ramp | Uso semántico | Light 50 | Solid 400 | Dark 800 |
|---|---|---|---|---|
| **Teal** | Marca principal, éxito, salud | `#E1F5EE` | `#1D9E75` | `#085041` |
| **Coral** | SOS, alertas urgentes, CTAs de venta | `#FAECE7` | `#D85A30` | `#712B13` |
| **Amber** | Recompensas, puntos, promos | `#FAEEDA` | `#EF9F27` | `#633806` |
| **Purple** | Perfil, cuenta, ajustes | `#EEEDFE` | `#7F77DD` | `#3C3489` |
| **Pink** | Adopción, comunidad, corazón | `#FBEAF0` | `#D4537E` | `#72243E` |
| **Green** | Confirmaciones, timeline, historial | `#EAF3DE` | `#97C459` | `#27500A` |

**Regla:** un color por pantalla como acento. Nunca mezclar 3+ en la misma vista.

**Neutrales (usa CSS vars de Tailwind, ya viene):**
- `bg`: `#FAFAF9` (surface page)
- `card`: `#FFFFFF`
- `border`: `#E7E5E4` (0.5px o 1px máximo)
- `text-primary`: `#1C1917`
- `text-secondary`: `#57534E`
- `text-muted`: `#A8A29E`

**Dark mode obligatorio.** Fondos: `#0C0A09` / `#1C1917` / `#292524`. Textos y borders invierten.

---

## 3. TIPOGRAFÍA

**Familia:** `Inter Variable` (ya cargable desde Google Fonts) + `SF Pro Display` fallback en iOS nativo.

| Rol | Tamaño | Peso | Line-height |
|---|---|---|---|
| Display (nombre de mascota, pantalla hero) | 32px | 600 | 1.1 |
| H1 (título de pantalla) | 24px | 600 | 1.2 |
| H2 (sección) | 18px | 500 | 1.3 |
| H3 (card title) | 15px | 500 | 1.4 |
| Body | 14px | 400 | 1.5 |
| Small (metadata, timestamps) | 12px | 400 | 1.4 |
| Caption / label | 10px | 500 tracking `0.5px` uppercase | 1.2 |
| Metric number (huellitas, peso) | 28-36px | 600 tabular-nums | 1 |

**Regla:** en cada pantalla hay un elemento tipográfico que domina (32px+). Todo lo demás se subordina.

---

## 4. SPACING Y RADIUS

**Escala 4pt.** Solo estos valores: `4 · 8 · 12 · 16 · 20 · 24 · 32 · 48 · 64`. Nada intermedio.

**Radius:**
- Buttons pequeños: 8px
- Inputs: 10px
- Cards: 16px
- Cards hero / avatares grandes: 20-24px
- FAB (floating action button): 28px
- Bottom sheet: 24px arriba, 0 abajo
- Pills / badges: 999px

**Padding de cards estándar:** 16px interno.
**Gap entre cards en una lista:** 8px.
**Padding lateral de la pantalla:** 16px (móvil) / 24px (web tablet).

---

## 5. COMPONENTES CLAVE

### 5.1 Botones

| Variante | Uso | Estilo |
|---|---|---|
| Primary | 1 solo por pantalla | Fondo teal-600 (`#0F6E56`), texto blanco, radius 12px, alto 48px móvil |
| Secondary | Acciones secundarias | Fondo transparente, border 1px `border`, texto primary |
| Ghost | Terciarias | Solo texto teal-600, sin fondo |
| Destructive | Cancelar cita, borrar mascota | Fondo coral-100, texto coral-800 |
| Icon-only | Bottom nav, header | 44×44px hit area mínimo |

**Estados:** hover (opacity 0.9), pressed (scale 0.98), disabled (opacity 0.4).

### 5.2 Cards

**Anatomía estándar:**
- Fondo blanco
- Border 0.5px `#E7E5E4`
- Radius 16px
- Padding 16px
- Sin shadow (o `0 1px 2px rgba(0,0,0,0.04)` máximo)

**Variante "colored" (para el módulo dominante):**
- Fondo `ramp-50` (ej. `#EEEDFE` para perfil)
- Sin border
- Texto en `ramp-800`

### 5.3 Bottom Navigation (5 tabs)

```
Inicio | Cerca de mí | Mascotas | Tienda | Perfil
```

- Alto: 64px + safe-area-bottom
- Icons outline 24px (Lucide o Phosphor)
- Label 10px, mostrar SOLO en tab activa
- Tab activa: icon fill teal-600 + fondo circular teal-50 detrás del icon

### 5.4 Floating Action Button (FAB) — solo SOS

Posición: bottom-right, sobre bottom-nav. Coral-600, radius 28px, icon `alert-triangle` blanco, sombra sutil. Vibra levemente al primer render (Framer Motion) para llamar atención.

### 5.5 Inputs

- Alto 48px móvil / 40px web
- Border 1px, radius 10px
- Placeholder `text-muted`
- Focus: border teal-600 + ring 3px `teal-50`
- Label flotante arriba del input, 12px, `text-secondary`

### 5.6 Chips / Filters

- Radius 999px, padding 8px 12px, font-size 13px
- Inactive: border 0.5px, texto primary
- Active: fondo teal-600, texto blanco, sin border

### 5.7 Bottom Sheet (modal móvil)

- Radius top 24px
- Handle bar 4×36px `border` en el top
- Snap points: 50%, 90%, dismiss al swipe down
- Overlay `rgba(0,0,0,0.4)` atrás

### 5.8 Empty states

**Nunca dejar una pantalla vacía sin invitación.**

Estructura: ilustración custom (50-80px) + H2 acción-orientada + body 1 línea + botón primary.

Ejemplo: `/pets` sin mascotas →
- Ilustración: silueta de perrito
- H2: "Agrega tu primer peludo"
- Body: "Registra su carnet de vacunas y agenda citas en segundos"
- Botón: "Agregar mascota"

---

## 6. ICONOGRAFÍA

**Librería única:** `lucide-react` (5000+ iconos, outline, consistentes). Alternativa: `phosphor-react` (mismo estilo).

**Nunca mezclar librerías.** Nunca emojis en UI (solo en contenido generado por el usuario).

Tamaños permitidos: `16 · 20 · 24 · 28` px. Stroke-width uniforme 1.5.

---

## 7. MOTION / ANIMACIONES

**Librería:** `framer-motion` (RN y web). Nativo en iOS via Capacitor conserva 60fps.

**Duraciones:**
- Micro (hover, tap): 150ms
- Standard (page transition, sheet open): 300ms
- Ambient (entrada de card): 400-500ms con stagger 50ms

**Easing:** `cubic-bezier(0.4, 0, 0.2, 1)` (Material standard) para todo, excepto entradas de card que usan `cubic-bezier(0.34, 1.56, 0.64, 1)` (leve overshoot).

**Patrones obligatorios:**
- Cards de lista aparecen con stagger + fade + slide-up 8px
- Tap en card → scale 0.98
- Push notification recibido → shake sutil del icono correspondiente en bottom nav
- SOS creado → confetti coral discreto por 1s (celebrar el acto de reportar)

---

## 8. ILUSTRACIONES Y ASSETS

**Estilo:** trazos simples, flat, dos colores máximo (uno del ramp del módulo + gris), sin gradientes.

**Fuentes recomendadas:**
- [Blush](https://blush.design/) — mascotas custom
- [Undraw](https://undraw.com/) — genérico con color configurable
- [Storyset](https://storyset.com/) — animados para empty states

**Assets prioritarios que hay que producir:**
1. Ilustración "sin mascotas registradas"
2. Ilustración "sin citas próximas"
3. Ilustración "sin SOS activos cerca de ti"
4. Ilustración "adopción encontró hogar"
5. Splash screen animado (logo pulsando)
6. Onboarding 3 slides (bienvenida, mascotas, SOS)

---

## 9. LAYOUT DE PANTALLAS CLAVE

### 9.1 Home (`/dashboard`)

```
[status bar]
[header: "Buenos días, Diego" + avatar]
[huellitas card — teal solid con número grande]
[quick actions row: SOS · Agendar · Adoptar · Tienda]
[section: Para ti — feed personalizado]
  [card: próxima vacuna de Tuki]
  [card: mascota perdida cerca]
  [card: promo contextual]
[bottom nav]
```

### 9.2 Mascota detail (`/pets/[id]`)

Hero header con `color_theme` de la mascota → avatar grande centrado → nombre 24px → stats row (peso, chip, vacunas) → timeline vertical de salud → CTA "Agendar cita".

### 9.3 SOS activo (`/sos/[id]`)

Alert banner coral arriba → mapa 100-140px con marker → card de la mascota (foto + nombre + descripción + badge URGENTE) → recompensa card amber → lista de avistamientos → CTAs "Yo la vi" (primary teal) + "Compartir" (secondary).

### 9.4 Reportar SOS (`/sos/reportar`)

Full-screen cámara nativa → shutter → preview + form corto (nombre, especie, última vez visto con auto-geolocation, teléfono contacto, recompensa opcional) → confirmar. Máximo 3 taps desde bottom nav hasta enviar.

### 9.5 Directorio servicios (`/servicios`)

Search bar arriba → chips de categoría (Veterinaria / Paseador / Baño / Guardería) → toggle vista lista/mapa → cards con foto del aliado + rating + distancia + botón "Agendar".

### 9.6 Adopción (`/adopcion`)

Filtros pill row (especie, tamaño, edad, ciudad) → grid 2 columnas de cards con foto de animal + nombre + edad + refugio + botón heart para guardar.

### 9.7 Perfil (`/profile`)

Header purple con avatar → stats de huellitas y órdenes → lista de rows (mis mascotas, mis citas, mis pedidos, preferencias, direcciones, ayuda, cerrar sesión). Estilo iOS Settings.

---

## 10. ACCESIBILIDAD (obligatorio)

- Contraste WCAG AA mínimo en todo texto (`text-secondary` sobre `bg` = 4.5:1).
- Hit areas mínimas 44×44px.
- Todos los inputs con label asociado.
- Iconos-only con `aria-label`.
- Soporte de dynamic type de iOS (respeta preferencia de tamaño de fuente del sistema).
- Modo alto contraste testeado.

---

## 11. STACK DE IMPLEMENTACIÓN RECOMENDADO

Ya sobre el `apps/portal` existente:

- **Tailwind CSS** — con config extendida para los 6 ramps y radius escala.
- **shadcn/ui** — base de componentes (Dialog, Sheet, Popover, Toast) — copiar y adaptar, no importar como lib.
- **Radix Primitives** — accesibilidad de menús, tabs, tooltips (viene con shadcn).
- **framer-motion** — animaciones.
- **lucide-react** — iconos.
- **@vis.gl/react-google-maps** — mapas (misma key que ya usan en store).
- **cmdk** — command palette para power users (fase posterior).

---

## 12. PROMPT PARA CLAUDE CODE EN VS CODE

Copia y pega esto tal cual en Claude Code cuando estés listo para elevar el nivel visual del portal:

---

```
Lee docs/DESIGN_SYSTEM.md y docs/MOBILE_COMMUNITY_MASTER_PLAN.md completos.

Contexto: la app SOS ya funciona en producción. Ahora quiero elevar todo el portal (apps/portal) al nivel visual de Airbnb / Apple Health / Linear siguiendo el design system que acabo de crear. La UX no cambia; cambia la piel.

Tarea concreta, en este orden:

1. Extiende tailwind.config.ts de apps/portal con los 6 ramps del sistema (teal, coral, amber, purple, pink, green), la escala tipográfica exacta, la escala 4pt de spacing, y los radius (8, 10, 12, 16, 20, 24, 28). Define también los tokens de dark mode.

2. Crea apps/portal/src/components/ui/ con estos componentes primitivos siguiendo shadcn/ui pero adaptados al design system:
   - Button (variants: primary, secondary, ghost, destructive; sizes: sm, md, lg, icon)
   - Card (variants: default, colored)
   - Input, Textarea, Select
   - Chip
   - Badge
   - BottomSheet
   - BottomNav (con las 5 tabs del sistema)
   - FAB
   - EmptyState (recibe icon, title, body, cta como props)
   - MetricCard (para huellitas, peso, etc)

3. Crea apps/portal/src/components/motion/ con:
   - PageTransition (fade + slide-up al montar)
   - StaggeredList (aplica stagger a los hijos)
   - TapScale (wrapper que escala 0.98 al presionar)

4. Refactoriza estas pantallas para usar los nuevos componentes SIN cambiar la lógica de negocio:
   - app/(portal)/dashboard/page.tsx  — usar el layout de la sección 9.1
   - app/(portal)/pets/[id]/page.tsx  — hero con color_theme (sección 9.2)
   - app/(portal)/sos/[id]/page.tsx   — layout de sección 9.3

5. Añade lucide-react como única librería de iconos. Reemplaza cualquier emoji o icono de otra librería.

6. Añade framer-motion. Aplica PageTransition al layout de (portal) y StaggeredList a las listas de mascotas, órdenes, citas.

7. Genera 4 empty state SVGs simples inline en apps/portal/src/components/illustrations/ para: no-pets, no-appointments, no-sos-nearby, adoption-success. Estilo trazos flat, 2 colores del ramp correspondiente.

8. Verifica que el build de web sigue pasando (pnpm build en apps/portal) y que no rompiste ninguna pantalla existente que no fue refactorizada.

Antes de mergear, muestra screenshots (o descripción textual detallada) de las 3 pantallas refactorizadas para que yo apruebe.

Modelo recomendado: Sonnet para todo el trabajo, cambia a Opus solo si te trabas más de 2 veces en el mismo bug.
```

---

## 13. BITÁCORA

- **2026-07-26** — Design system creado. Mapeado al `color_theme` existente en `portal.pets`. Stack recomendado: Tailwind + shadcn/ui + framer-motion + lucide. Prompt de implementación listo para Claude Code.
