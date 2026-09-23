import type { Metadata, Viewport } from 'next';
import { Inter, Plus_Jakarta_Sans } from 'next/font/google';
import { Toaster } from 'sonner';
import './globals.css';
import { Providers } from './providers';
import { PWAInstallBanner } from '@/components/widgets/PWAInstallBanner';
import { MetaPixel } from '@/components/MetaPixel';

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
  title: { default: 'Mi Portal — Bigotes y Paticas', template: '%s | Bigotes y Paticas' },
  description: 'Gestiona las mascotas, pedidos y citas de Bigotes y Paticas.',
  manifest: '/manifest.json',
  appleWebApp: {
    capable: true,
    statusBarStyle: 'default',
    title: 'Mi Bigotes y Paticas',
  },
  formatDetection: { telephone: false },
  verification: {
    google: 'Eh5nbpTENsmdblrIL4_gERvjZCRbJtldy266FQVYqLo',
  },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '48x48 32x32 16x16' },
      { url: '/icon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      // 22-sep-2026: /icon.svg pesaba 1,97 MB y lo bajaba CADA visitante. No era
      // un SVG: era un PNG de 1024x1024 en base64 dentro de una envoltura <svg>.
      // Mismo bug que en el store, donde costaba 11 s de LCP. Los PNG ya cubren
      // todos los tamanos y el manifest nunca lo uso.
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180' }],
    shortcut: ['/favicon.ico'],
  },
};

export const viewport: Viewport = {
  themeColor: '#187f77',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <meta name="apple-mobile-web-app-title" content="B&P Portal" />
      </head>
      <body className={`${fontSans.variable} ${fontDisplay.variable}`}>
        <MetaPixel />
        <Providers>{children}</Providers>
        <PWAInstallBanner />
        <Toaster
          position="top-center"
          richColors
          toastOptions={{
            classNames: {
              toast: 'rounded-xl font-sans text-sm',
            },
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js');
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
