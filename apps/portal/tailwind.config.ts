import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    container: { center: true, padding: '1rem', screens: { sm: '430px' } },
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui'],
        display: ['var(--font-display)', 'ui-sans-serif'],
      },
      colors: {
        // Portal usa el teal como primario (brand BP veterinaria)
        primary: {
          DEFAULT: '#187f77',
          50: '#edfaf9', 100: '#d4f5f3', 200: '#a3eeea',
          300: '#6be2d8', 400: '#34cfc4', 500: '#20b2a8',
          600: '#1a9991', 700: '#187f77', 800: '#125e58',
          900: '#0d4a45', 950: '#061e1c',
        },
        accent: {
          DEFAULT: '#f5a641',
          50: '#fff8ed', 100: '#fff0d4', 200: '#ffdda8',
          300: '#ffc36a', 400: '#ff9f2b', 500: '#f5a641',
          600: '#e07c0a', 700: '#b85a0a', 800: '#934510',
          900: '#773a12',
        },
        // Temas dinámicos por mascota (CSS vars en runtime)
        pet: {
          DEFAULT: 'var(--pet-color, #187f77)',
          light: 'var(--pet-color-light, #edfaf9)',
          dark: 'var(--pet-color-dark, #125e58)',
        },
        background: '#f8f9fa',
        foreground: '#262730',
        muted: '#6b7280',
        border: '#e5e7eb',
        card: '#ffffff',
        // Colores por especie/tema
        teal: { DEFAULT: '#187f77', light: '#edfaf9' },
        coral: { DEFAULT: '#e05252', light: '#fef2f2' },
        amber: { DEFAULT: '#f5a641', light: '#fff8ed' },
        purple: { DEFAULT: '#7c3aed', light: '#f5f3ff' },
        pink: { DEFAULT: '#db2777', light: '#fdf2f8' },
        green: { DEFAULT: '#16a34a', light: '#f0fdf4' },
      },
      borderRadius: {
        xl: '1rem', '2xl': '1.25rem', '3xl': '1.5rem',
      },
      boxShadow: {
        card: '0 2px 12px 0 rgba(24,127,119,0.08)',
        'card-hover': '0 8px 32px 0 rgba(24,127,119,0.16)',
        bottom: '0 -2px 12px 0 rgba(0,0,0,0.06)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'slide-up': {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'pulse-badge': {
          '0%, 100%': { transform: 'scale(1)' },
          '50%': { transform: 'scale(1.15)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.4s ease-out',
        'slide-up': 'slide-up 0.5s cubic-bezier(0.16, 1, 0.3, 1)',
        'pulse-badge': 'pulse-badge 2s ease-in-out infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
export default config;
