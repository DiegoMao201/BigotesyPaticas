'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, X } from 'lucide-react';
import { Sidebar } from '@/components/sidebar';
import { useAuth } from '@/lib/auth-store';

export default function PartnerLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuth((s) => s.token);
  const hasHydrated = useAuth((s) => s.hasHydrated);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    // Esperamos a que zustand-persist rehidrate desde localStorage antes de
    // decidir si redirigir — si no, cualquier recarga de página (F5, o abrir
    // el link directo) manda al login aunque sí haya una sesión guardada.
    if (hasHydrated && !token) router.replace('/login');
  }, [hasHydrated, token, router]);

  // eslint-disable-next-line no-console
  console.log('[DEBUG PartnerLayout render]', { hasHydrated, hasToken: !!token });

  if (!hasHydrated || !token) return null;

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between border-b border-border bg-white/95 backdrop-blur px-4 py-3">
          <button
            onClick={() => setMobileOpen(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-1.5 text-sm"
          >
            <Menu className="h-4 w-4" /> Menú
          </button>
          <p className="text-sm font-semibold text-primary-800">Panel de Aliados</p>
          <div className="w-16" />
        </header>

        <main className="overflow-x-hidden">
          <div className="container max-w-6xl px-4 sm:px-6 py-6 sm:py-8 animate-slide-up">{children}</div>
        </main>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Cerrar menú"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative h-full w-72 max-w-[85vw] bg-white shadow-2xl">
            <button
              className="absolute right-2 top-2 rounded-lg p-1.5 text-muted hover:bg-primary-50"
              onClick={() => setMobileOpen(false)}
            >
              <X className="h-4 w-4" />
            </button>
            <Sidebar mobile onNavigate={() => setMobileOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
