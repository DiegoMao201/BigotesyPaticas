import type { Metadata } from 'next';
import { Inter, Plus_Jakarta_Sans, JetBrains_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from '@/components/providers';
import { Header } from '@/components/header';
import { Footer } from '@/components/footer';

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
    default: 'Bigotes y Paticas — Productos premium para mascotas',
    template: '%s · Bigotes y Paticas',
  },
  description:
    'Tienda premium de productos para perros y gatos. Comida, accesorios, juguetes y cuidado, seleccionados con cariño.',
  keywords: ['mascotas', 'perros', 'gatos', 'comida premium', 'accesorios mascotas', 'Colombia'],
  openGraph: {
    title: 'Bigotes y Paticas',
    description: 'Productos premium para mascotas',
    url: 'https://bigotesypaticas.com',
    siteName: 'Bigotes y Paticas',
    locale: 'es_CO',
    type: 'website',
  },
  twitter: { card: 'summary_large_image' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es" suppressHydrationWarning>
      <body className={`${inter.variable} ${jakarta.variable} ${mono.variable} font-sans`}>
        <Providers>
          <Header />
          <main className="min-h-[calc(100vh-4rem-1px)]">{children}</main>
          <Footer />
        </Providers>
      </body>
    </html>
  );
}
