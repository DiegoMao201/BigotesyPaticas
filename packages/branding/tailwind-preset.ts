/**
 * Tailwind CSS preset que extiende los tokens de branding BP.
 * Úsalo en tailwind.config.ts de cada app:
 *
 *   import bpPreset from '@bp/branding/tailwind-preset';
 *   const config: Config = { presets: [bpPreset], ... };
 */
import { palette, radius, animations } from './tokens';

const bpPreset = {
  theme: {
    extend: {
      fontFamily: {
        sans:    ['var(--font-sans)', 'Inter', 'system-ui', 'sans-serif'],
        display: ['var(--font-display)', 'Plus Jakarta Sans', 'system-ui'],
        mono:    ['var(--font-mono)', 'JetBrains Mono', 'monospace'],
      },
      colors: {
        // Brand palette — Teal (primario oficial Bigotes y Paticas / Nexus Pro)
        brand: {
          DEFAULT: palette.teal[700], // #187f77
          50:  palette.teal[50],
          100: palette.teal[100],
          200: palette.teal[200],
          300: palette.teal[300],
          400: palette.teal[400],
          500: palette.teal[500],
          600: palette.teal[600],
          700: palette.teal[700],
          800: palette.teal[800],
          900: palette.teal[900],
          950: palette.teal[950],
        },
        // Warm palette — Amber/Orange (acento emocional / CTA)
        warm: {
          DEFAULT: palette.amber[500], // #f5a641
          50:  palette.amber[50],
          100: palette.amber[100],
          200: palette.amber[200],
          300: palette.amber[300],
          400: palette.amber[400],
          500: palette.amber[500],
          600: palette.amber[600],
          700: palette.amber[700],
          800: palette.amber[800],
          900: palette.amber[900],
        },
        // System semantic
        success: { DEFAULT: '#10b981', light: '#d1fae5', dark: '#065f46' },
        warning: { DEFAULT: '#f59e0b', light: '#fef3c7', dark: '#92400e' },
        error:   { DEFAULT: '#ef4444', light: '#fee2e2', dark: '#991b1b' },
        ink:     '#262730',
        cream:   '#f8f9fa',
      },
      borderRadius: {
        sm:   radius.sm,
        md:   radius.md,
        lg:   radius.lg,
        xl:   radius.xl,
        '2xl': radius['2xl'],
        '3xl': radius['3xl'],
      },
      keyframes: {
        'fade-in':   { from: { opacity: '0' }, to: { opacity: '1' } },
        'slide-up':  { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'slide-in':  { from: { opacity: '0', transform: 'translateX(-16px)' }, to: { opacity: '1', transform: 'translateX(0)' } },
        'scale-in':  { from: { opacity: '0', transform: 'scale(0.95)' }, to: { opacity: '1', transform: 'scale(1)' } },
        'marquee':   { from: { transform: 'translateX(0)' }, to: { transform: 'translateX(-50%)' } },
        'shimmer':   { '100%': { transform: 'translateX(100%)' } },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(24,127,119,0.4)' },
          '50%': { boxShadow: '0 0 0 12px rgba(24,127,119,0)' },
        },
      },
      animation: {
        'fade-in':   'fade-in 0.5s ease-out',
        'slide-up':  'slide-up 0.6s cubic-bezier(0.16, 1, 0.3, 1)',
        'slide-in':  'slide-in 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-in':  'scale-in 0.4s cubic-bezier(0.16, 1, 0.3, 1)',
        'marquee':   'marquee 30s linear infinite',
        'shimmer':   'shimmer 2s infinite',
        'pulse-glow': 'pulse-glow 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
      boxShadow: {
        elegant:  '0 1px 2px rgba(13,74,69,0.04), 0 24px 48px -16px rgba(24,127,119,0.18)',
        glow:     '0 0 0 1px rgba(24,127,119,0.1), 0 24px 64px -16px rgba(24,127,119,0.32)',
        'warm-glow': '0 8px 32px rgba(245,166,65,0.25)',
        'card':   '0 1px 3px rgba(13,74,69,0.06), 0 4px 16px rgba(13,74,69,0.04)',
      },
    },
  },
} as const;

export default bpPreset;
