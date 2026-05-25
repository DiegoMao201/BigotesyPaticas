'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Menu, X } from 'lucide-react';
import { Sidebar } from '@/components/sidebar';
import { useAuth } from '@/lib/auth-store';

export default function DashboardLayout({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuth((s) => s.token);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    if (!token) router.replace('/login');
  }, [token, router]);

  useEffect(() => {
    if (!token) setMobileOpen(false);
  }, [token]);

  return (
    <div className="flex min-h-screen bg-background">
      <Sidebar />

      <div className="flex-1 min-w-0">
        <header className="lg:hidden sticky top-0 z-30 flex items-center justify-between border-b border-border bg-background/95 backdrop-blur px-3 py-2">
          <button
            onClick={() => setMobileOpen(true)}
            className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-1.5 text-sm"
            aria-label="Abrir menu"
          >
            <Menu className="h-4 w-4" /> Menu
          </button>
          <div className="text-sm font-semibold">Bigotes y Paticas</div>
          <div className="w-[72px]" />
        </header>

        <main className="overflow-x-hidden">
          <div className="container max-w-7xl px-3 sm:px-6 py-4 sm:py-8 animate-slide-up">{children}</div>
        </main>
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button
            aria-label="Cerrar menu"
            className="absolute inset-0 bg-black/40"
            onClick={() => setMobileOpen(false)}
          />
          <div className="relative h-full w-72 max-w-[85vw] bg-background shadow-2xl">
            <button
              className="absolute right-2 top-2 rounded-md p-1.5 text-muted-foreground hover:bg-accent"
              onClick={() => setMobileOpen(false)}
              aria-label="Cerrar"
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
