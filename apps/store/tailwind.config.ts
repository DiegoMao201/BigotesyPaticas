import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: ['./src/**/*.{ts,tsx}'],
  theme: {
    container: { center: true, padding: '1.5rem', screens: { '2xl': '1400px' } },
    extend: {
      fontFamily: {
        sans: ['var(--font-sans)', 'ui-sans-serif', 'system-ui'],
        display: ['var(--font-display)', 'ui-sans-serif'],
        mono: ['var(--font-mono)', 'monospace'],
      },
      colors: {
        border: 'hsl(var(--border))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        muted: { DEFAULT: 'hsl(var(--muted))', foreground: 'hsl(var(--muted-foreground))' },
        card: { DEFAULT: 'hsl(var(--card))', foreground: 'hsl(var(--card-foreground))' },
        primary: { DEFAULT: 'hsl(var(--primary))', foreground: 'hsl(var(--primary-foreground))' },
        accent: { DEFAULT: 'hsl(var(--accent))', foreground: 'hsl(var(--accent-foreground))' },
        // Brand BP: Teal (identidad oficial Nexus Pro)
        brand: {
          DEFAULT: '#187f77', 50: '#edfaf9', 100: '#d4f5f3', 200: '#a3eeea',
          300: '#6be2d8', 400: '#34cfc4', 500: '#20b2a8', 600: '#1a9991',
          700: '#187f77', 800: '#125e58', 900: '#0d4a45', 950: '#061e1c',
        },
        // Warm: Amber/naranja — acento emocional, CTAs
        warm: {
          DEFAULT: '#f5a641', 50: '#fffbf5', 100: '#fef3e0', 200: '#fde4bb',
          300: '#fad093', 400: '#f7b96a', 500: '#f5a641', 600: '#e5721c',
          700: '#c96114', 800: '#a34f0d', 900: '#7c3d0a',
        },
        cream: '#f8f9fa',
        ink: '#262730',
      },
      borderRadius: {
        lg: 'var(--radius)', md: 'calc(var(--radius) - 2px)', sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'fade-in': { from: { opacity: '0' }, to: { opacity: '1' } },
        'slide-up': { from: { opacity: '0', transform: 'translateY(20px)' }, to: { opacity: '1', transform: 'translateY(0)' } },
        'marquee': { from: { transform: 'translateX(0)' }, to: { transform: 'translateX(-50%)' } },
        'shimmer': { '100%': { transform: 'translateX(100%)' } },
      },
      animation: {
        'fade-in': 'fade-in 0.6s ease-out',
        'slide-up': 'slide-up 0.7s cubic-bezier(0.16, 1, 0.3, 1)',
        'marquee': 'marquee 30s linear infinite',
        'shimmer': 'shimmer 2s infinite',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};
export default config;
