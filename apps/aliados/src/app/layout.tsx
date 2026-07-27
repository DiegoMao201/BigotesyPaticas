import type { Metadata, Viewport } from 'next';
import { Inter, Plus_Jakarta_Sans } from 'next/font/google';
import { Toaster } from 'sonner';
import './globals.css';
import { Providers } from './providers';

const fontSans = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  display: 'swap',
});

const fontDisplay = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
});

export const metadata: Metadata = {
  title: { default: 'Panel de Aliados — Bigotes y Paticas', template: '%s | Aliados Bigotes y Paticas' },
  description: 'Gestiona tu perfil, servicios, disponibilidad y reservas como aliado de Bigotes y Paticas.',
  icons: {
    icon: [{ url: '/favicon.ico', sizes: '48x48 32x32 16x16' }],
  },
};

export const viewport: Viewport = {
  themeColor: '#187f77',
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={`${fontSans.variable} ${fontDisplay.variable}`}>
        <Providers>{children}</Providers>
        <Toaster
          position="top-center"
          richColors
          toastOptions={{ classNames: { toast: 'rounded-xl font-sans text-sm' } }}
        />
      </body>
    </html>
  );
}
