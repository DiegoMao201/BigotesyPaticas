'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  LayoutDashboard, CalendarCheck, Sparkles, CalendarClock, Store, LogOut, ShieldCheck,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-store';

const NAV_ITEMS = [
  { href: '/dashboard', label: 'Inicio', icon: LayoutDashboard },
  { href: '/reservas', label: 'Reservas', icon: CalendarCheck },
  { href: '/servicios', label: 'Servicios', icon: Sparkles },
  { href: '/disponibilidad', label: 'Disponibilidad', icon: CalendarClock },
  { href: '/perfil', label: 'Perfil', icon: Store },
];

const TYPE_EMOJI: Record<string, string> = { vet: '🩺', walker: '🐕', shelter: '🏠', groomer: '✂️' };

export function Sidebar({ mobile, onNavigate }: { mobile?: boolean; onNavigate?: () => void }) {
  const pathname = usePathname();
  const router = useRouter();
  const partnerUser = useAuth((s) => s.partnerUser);
  const clear = useAuth((s) => s.clear);

  function logout() {
    clear();
    router.replace('/login');
  }

  return (
    <aside
      className={cn(
        'flex flex-col h-full bg-white border-r border-border',
        mobile ? 'w-full' : 'hidden lg:flex w-64 shrink-0 sticky top-0 h-screen'
      )}
    >
      <div className="px-5 py-6 border-b border-border">
        <p className="font-display text-lg font-extrabold text-primary-800 leading-tight">
          Panel de Aliados
        </p>
        <p className="text-xs text-muted mt-0.5">Bigotes y Paticas</p>
      </div>

      {partnerUser && (
        <div className="mx-4 mt-4 p-3 rounded-xl bg-primary-50 flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-white flex items-center justify-center text-lg shrink-0">
            {TYPE_EMOJI[partnerUser.partner.partner_type] ?? '🤝'}
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-foreground truncate">{partnerUser.partner.business_name}</p>
            <p className="text-[11px] text-muted flex items-center gap-1">
              {partnerUser.partner.is_published ? (
                <span className="text-emerald-600 font-medium">● Publicado</span>
              ) : (
                <span className="text-amber-600 font-medium">● Pendiente de aprobación</span>
              )}
            </p>
          </div>
        </div>
      )}

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || pathname?.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={cn(
                'flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors',
                active ? 'bg-primary-700 text-white shadow-sm' : 'text-foreground/80 hover:bg-primary-50'
              )}
            >
              <Icon className="h-4 w-4 shrink-0" />
              {label}
            </Link>
          );
        })}
      </nav>

      {partnerUser?.partner.is_verified && (
        <div className="mx-4 mb-2 flex items-center gap-1.5 text-[11px] text-emerald-700 font-medium">
          <ShieldCheck className="h-3.5 w-3.5" /> Aliado verificado
        </div>
      )}

      <div className="px-3 py-4 border-t border-border">
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium text-muted hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="h-4 w-4" /> Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
