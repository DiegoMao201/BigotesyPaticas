import type { Metadata } from 'next';
import { Inter, Plus_Jakarta_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Header } from '@/components/header';
import { Footer } from '@/components/footer';
import { OrganizationSchema, LocalBusinessSchema } from '@/components/seo/JsonLd';
import { GoogleAnalytics } from '@/components/analytics/GoogleAnalytics';
import { MetaPixel } from '@/components/analytics/MetaPixel';
import { GoogleReviewPrompt } from '@/components/reviews/GoogleReviewPrompt';
import { WhatsAppFloat } from '@/components/widgets/WhatsAppFloat';
import { PWAInstallBanner } from '@/components/widgets/PWAInstallBanner';
import { Toaster } from 'sonner';

const inter = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const jakarta = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-display',
  display: 'swap',
  weight: ['500', '600', '700', '800'],
});
const mono = JetBrains_Mono({ subsets: ['latin'], variable: '--font-mono', display: 'swap' });

export const metadata: Metadata = {
  metadataBase: new URL('https://bigotesypaticas.com'),
  title: {
    default: 'Pet Shop Pereira y Dosquebradas — Bigotes y Paticas | Domicilio 24-72h',
    template: '%s | Bigotes y Paticas Pet Shop',
  },
  description:
    'Pet shop con domicilio en Pereira y Dosquebradas. Concentrados, accesorios y medicamentos veterinarios. Envío gratis desde $30.000 en 24-72h. El mejor petshop de Risaralda.',
  keywords: [
    'pet shop Pereira', 'pet shop Dosquebradas', 'petshop Pereira', 'petshop Dosquebradas',
    'domicilio pet shop Pereira', 'pet shop domicilio', 'petshop domicilio Risaralda',
    'tienda mascotas Pereira', 'tienda mascotas Dosquebradas',
    'mascotas Pereira', 'domicilio mascotas Risaralda',
    'concentrado perro Pereira', 'comida gato Dosquebradas',
    'Hills Pereira', 'Royal Canin Dosquebradas', 'Pro Plan Pereira',
    'accesorios mascotas Pereira', 'medicamentos veterinarios Dosquebradas',
    'veterinaria Pereira', 'concentrado gato Pereira', 'snacks perro Dosquebradas',
  ],
  authors: [{ name: 'Bigotes y Paticas' }],
  creator: 'Bigotes y Paticas',
  publisher: 'Bigotes y Paticas',
  formatDetection: { telephone: false, email: false, address: false },
  icons: {
    icon: [
      { url: '/favicon.ico', sizes: '48x48 32x32 16x16' },
      { url: '/icon-32.png', sizes: '32x32', type: 'image/png' },
      { url: '/icon-192.png', sizes: '192x192', type: 'image/png' },
      { url: '/icon.svg', type: 'image/svg+xml' },
    ],
    apple: [{ url: '/apple-touch-icon.png', sizes: '180x180' }],
    shortcut: ['/favicon.ico'],
  },
  manifest: '/site.webmanifest',
  openGraph: {
    type: 'website',
    locale: 'es_CO',
    url: 'https://bigotesypaticas.com',
    siteName: 'Bigotes y Paticas',
    title: 'Bigotes y Paticas — Pet Shop Pereira y Dosquebradas con domicilio',
    description: 'Pet shop con domicilio en Pereira y Dosquebradas. Más de 900 productos para mascotas. Envío gratis desde $30.000.',
    images: [{
      url: 'https://bigotesypaticas.com/opengraph-image.png',
      width: 1200,
      height: 630,
      alt: 'Bigotes y Paticas — Tienda de mascotas en Pereira y Dosquebradas',
    }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Bigotes y Paticas — Pet Shop Pereira y Dosquebradas',
    description: 'Pet shop con domicilio en Pereira y Dosquebradas. Más de 900 productos. Envío 24-72h.',
    images: ['https://bigotesypaticas.com/opengraph-image.png'],
  },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  alternates: {
    types: { 'application/rss+xml': [{ url: '/feed.xml', title: 'Blog Bigotes y Paticas' }] },
  },
  verification: {
    google: 'Eh5nbpTENsmdblrIL4_gERvjZCRbJtldy266FQVYqLo',
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={`${inter.variable} ${jakarta.variable} ${mono.variable} font-sans`}>
        <GoogleAnalytics />
        <MetaPixel />
        <OrganizationSchema />
        <LocalBusinessSchema />
        <Providers>
          <Header />
          <main className="min-h-[calc(100vh-4rem-1px)]">{children}</main>
          <Footer />
          <GoogleReviewPrompt />
          <WhatsAppFloat />
          <PWAInstallBanner />
          <Toaster position="bottom-left" richColors closeButton />
        </Providers>
      </body>
    </html>
  );
}
