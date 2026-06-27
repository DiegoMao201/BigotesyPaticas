import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Buscar productos — Bigotes y Paticas',
  robots: { index: false, follow: true },
};

export default function BuscarLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
