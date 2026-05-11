/**
 * Bigotes y Paticas — Design System Tokens
 *
 * Fuente de verdad para colores, tipografía, espaciado y shadows.
 * Sincronizados con Tailwind via tailwind-preset.ts y con globals.css via CSS vars.
 *
 * Paleta extraída del sistema Nexus Pro (Streamlit legacy):
 *   Primary  #187f77  (teal — confianza, salud, naturaleza, premium)
 *   Accent   #f5a641  (amber — calidez, juego, mascotas)
 *   Dark     #0d4a45  (deepTeal — contraste, headings)
 */

// ─────────────────────────────────────────────
// COLORES PRIMITIVOS
// ─────────────────────────────────────────────
export const palette = {
  // Teal — identidad corporativa Nexus Pro / Bigotes y Paticas
  teal: {
    950: '#061e1c',
    900: '#0d4a45',  // deepTeal — headings, dark mode bg
    800: '#125e58',  // secondary — hover states
    700: '#187f77',  // PRIMARY — botones, links, brand
    600: '#1a9991',  // hover primary
    500: '#20b2a8',  // lighter accents
    400: '#34cfc4',  // icons, badges
    300: '#6be2d8',  // tags, chips
    200: '#a3eeea',  // borders on dark
    100: '#d4f5f3',  // bg tints
    50:  '#edfaf9',  // subtle bg
  },

  // Amber/Warm — calidez, call-to-action, acento emocional
  amber: {
    900: '#7c3d0a',
    800: '#a34f0d',
    700: '#c96114',
    600: '#e5721c',
    500: '#f5a641',  // ACCENT — CTAs, badges, highlights
    400: '#f7b96a',  // hover accent
    300: '#fad093',  // soft accent
    200: '#fde4bb',  // bg accent
    100: '#fef3e0',  // subtle bg
    50:  '#fffbf5',
  },

  // Neutros
  gray: {
    950: '#0f0f0f',
    900: '#1a1a1a',
    800: '#262730',  // text primary (Nexus Pro)
    700: '#3a3d4d',
    600: '#5a5f7a',
    500: '#7a7f99',
    400: '#9ba0b8',
    300: '#c4c8db',
    200: '#e0e3f0',
    100: '#f0f2f9',
    50:  '#f8f9fa',  // background (Nexus Pro)
  },

  // Semáforo
  success: { DEFAULT: '#10b981', light: '#d1fae5', dark: '#065f46' },
  warning: { DEFAULT: '#f59e0b', light: '#fef3c7', dark: '#92400e' },
  error:   { DEFAULT: '#ef4444', light: '#fee2e2', dark: '#991b1b' },
  info:    { DEFAULT: '#3b82f6', light: '#dbeafe', dark: '#1e3a8a' },

  // Base
  white: '#ffffff',
  black: '#000000',
} as const;

// ─────────────────────────────────────────────
// SEMÁNTICOS (alias de uso recomendado)
// ─────────────────────────────────────────────
export const semantic = {
  brand:     palette.teal[700],
  brandHover: palette.teal[600],
  brandDark:  palette.teal[900],
  brandLight: palette.teal[100],
  accent:     palette.amber[500],
  accentHover: palette.amber[400],
  background: palette.gray[50],
  surface:    palette.white,
  textPrimary:   palette.gray[800],
  textSecondary: palette.gray[500],
  textMuted:     palette.gray[400],
  border:     palette.gray[200],
  borderStrong: palette.gray[300],
} as const;

// ─────────────────────────────────────────────
// TIPOGRAFÍA
// ─────────────────────────────────────────────
export const typography = {
  fonts: {
    sans:    ['Inter', 'system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
    display: ['Plus Jakarta Sans', 'system-ui', 'sans-serif'],
    mono:    ['JetBrains Mono', 'Fira Code', 'monospace'],
    // Legacy Streamlit
    legacy:  ['Quicksand', 'system-ui', 'sans-serif'],
  },
  scale: {
    xs:   '0.75rem',   // 12px
    sm:   '0.875rem',  // 14px
    base: '1rem',      // 16px
    lg:   '1.125rem',  // 18px
    xl:   '1.25rem',   // 20px
    '2xl': '1.5rem',   // 24px
    '3xl': '1.875rem', // 30px
    '4xl': '2.25rem',  // 36px
    '5xl': '3rem',     // 48px
    '6xl': '3.75rem',  // 60px
    '7xl': '4.5rem',   // 72px
  },
  weight: { normal: '400', medium: '500', semibold: '600', bold: '700', extrabold: '800' },
  leading: { tight: '1.1', snug: '1.3', normal: '1.5', relaxed: '1.75' },
  tracking: { tighter: '-0.05em', tight: '-0.025em', normal: '0', wide: '0.025em', wider: '0.1em' },
} as const;

// ─────────────────────────────────────────────
// ESPACIADO (base 4px)
// ─────────────────────────────────────────────
export const spacing = {
  px:  '1px',
  0:   '0',
  0.5: '0.125rem', // 2px
  1:   '0.25rem',  // 4px
  2:   '0.5rem',   // 8px
  3:   '0.75rem',  // 12px
  4:   '1rem',     // 16px
  5:   '1.25rem',  // 20px
  6:   '1.5rem',   // 24px
  8:   '2rem',     // 32px
  10:  '2.5rem',   // 40px
  12:  '3rem',     // 48px
  16:  '4rem',     // 64px
  20:  '5rem',     // 80px
  24:  '6rem',     // 96px
  32:  '8rem',     // 128px
} as const;

// ─────────────────────────────────────────────
// RADII
// ─────────────────────────────────────────────
export const radius = {
  none: '0',
  sm:   '0.375rem',  // 6px
  md:   '0.5rem',    // 8px
  lg:   '0.75rem',   // 12px
  xl:   '1rem',      // 16px
  '2xl': '1.5rem',   // 24px
  '3xl': '2rem',     // 32px
  full: '9999px',
} as const;

// ─────────────────────────────────────────────
// SOMBRAS
// ─────────────────────────────────────────────
export const shadows = {
  sm:     '0 1px 2px rgba(13,74,69,0.06)',
  md:     '0 4px 12px rgba(13,74,69,0.08), 0 1px 3px rgba(13,74,69,0.04)',
  lg:     '0 8px 32px rgba(13,74,69,0.10), 0 2px 8px rgba(13,74,69,0.04)',
  xl:     '0 20px 60px rgba(13,74,69,0.14), 0 4px 16px rgba(13,74,69,0.06)',
  elegant: '0 1px 2px rgba(26,20,16,0.04), 0 24px 48px -16px rgba(24,127,119,0.18)',
  glow:    '0 0 0 1px rgba(24,127,119,0.1), 0 24px 64px -16px rgba(24,127,119,0.32)',
  amber:   '0 8px 32px rgba(245,166,65,0.25)',
  inner:   'inset 0 2px 4px rgba(13,74,69,0.06)',
} as const;

// ─────────────────────────────────────────────
// GRADIENTES
// ─────────────────────────────────────────────
export const gradients = {
  brand:       'linear-gradient(135deg, #187f77 0%, #1a9991 50%, #20b2a8 100%)',
  brandDark:   'linear-gradient(135deg, #0d4a45 0%, #125e58 100%)',
  brandReverse: 'linear-gradient(135deg, #20b2a8 0%, #187f77 100%)',
  accent:      'linear-gradient(135deg, #e5721c 0%, #f5a641 60%, #f7b96a 100%)',
  hero:        'linear-gradient(160deg, #edfaf9 0%, #d4f5f3 40%, #fef3e0 100%)',
  dark:        'linear-gradient(135deg, #061e1c 0%, #0d4a45 100%)',
  text:        'linear-gradient(135deg, #187f77, #0d4a45 60%, #125e58)',
} as const;

// ─────────────────────────────────────────────
// ANIMACIONES
// ─────────────────────────────────────────────
export const animations = {
  duration: { fast: '150ms', base: '250ms', slow: '400ms', slower: '600ms' },
  easing: {
    out:     'cubic-bezier(0.16, 1, 0.3, 1)',
    in:      'cubic-bezier(0.4, 0, 1, 1)',
    inOut:   'cubic-bezier(0.4, 0, 0.2, 1)',
    bounce:  'cubic-bezier(0.34, 1.56, 0.64, 1)',
    spring:  'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  },
} as const;

// ─────────────────────────────────────────────
// BREAKPOINTS
// ─────────────────────────────────────────────
export const breakpoints = {
  sm: '640px',
  md: '768px',
  lg: '1024px',
  xl: '1280px',
  '2xl': '1400px',
} as const;

// Export unificado
export const tokens = {
  palette,
  semantic,
  typography,
  spacing,
  radius,
  shadows,
  gradients,
  animations,
  breakpoints,
} as const;

export default tokens;
