'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard, Package, ShoppingCart, Boxes, Users, BarChart3,
  Settings, LogOut, AlertTriangle, TrendingUp, CreditCard, Tag,
  Building2, ChevronRight, ShoppingBag, Wallet, Truck, ReceiptText, Brain, PawPrint,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuth } from '@/lib/auth-store';
import { setToken } from '@/lib/api';
import { useRouter } from 'next/navigation';

const NAV_GROUPS = [
  {
    label: 'Principal',
    items: [
      { href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { href: '/analytics', label: 'Analítica', icon: BarChart3 },
      { href: '/intelligence', label: 'Inteligencia', icon: Brain, highlight: true },
      { href: '/pet-monitor', label: 'Portal Monitor', icon: PawPrint, highlight: true },
    ],
  },
  {
    label: 'Comercial',
    items: [
      { href: '/pos', label: 'Punto de Venta', icon: ShoppingBag, highlight: true },
      { href: '/sales', label: 'Ventas', icon: ShoppingCart },
      { href: '/customers', label: 'Clientes', icon: Users },
    ],
  },
  {
    label: 'Catálogo',
    items: [
      { href: '/products', label: 'Productos', icon: Package },
      { href: '/inventory', label: 'Inventario', icon: Boxes },
    ],
  },
  {
    label: 'Finanzas',
    items: [
      { href: '/finance', label: 'P&L y Cash Flow', icon: TrendingUp },
      { href: '/expenses', label: 'Gastos', icon: Wallet },
      { href: '/cash-closings', label: 'Cierres de Caja', icon: ReceiptText },
    ],
  },
  {
    label: 'Compras',
    items: [
      { href: '/purchases', label: 'Compras', icon: ReceiptText },
      { href: '/replenishment', label: 'Reabastecimiento', icon: Truck, highlight: true },
      { href: '/suppliers', label: 'Proveedores', icon: Building2 },
    ],
  },
  {
    label: 'Sistema',
    items: [
      { href: '/settings', label: 'Configuración', icon: Settings },
    ],
  },
];

export function Sidebar({
  mobile = false,
  onNavigate,
}: {
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const user = useAuth((s) => s.user);
  const clear = useAuth((s) => s.clear);

  function logout() {
    setToken(null);
    clear();
    onNavigate?.();
    router.push('/login');
  }

  return (
    <aside
      className={cn(
        'shrink-0 border-r border-border bg-card/95 backdrop-blur-sm flex flex-col',
        mobile ? 'w-72 h-full' : 'hidden lg:flex w-64 h-screen sticky top-0',
      )}
    >
      {/* Logo */}
      <div className="p-5 border-b border-border/60">
        <Link href="/dashboard" className="flex items-center gap-3 group" onClick={onNavigate}>
          <div className="w-9 h-9 rounded-xl gradient-brand flex items-center justify-center text-white text-lg shadow-elegant group-hover:shadow-glow transition-shadow">
            🐾
          </div>
          <div>
            <div className="font-display font-bold text-sm leading-tight">Bigotes y Paticas</div>
            <div className="text-[10px] text-brand-600 uppercase tracking-widest font-medium">Nexus Pro</div>
          </div>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-3 space-y-4 overflow-y-auto scrollbar-thin">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <div className="px-3 mb-1.5 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
              {group.label}
            </div>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const active = pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={onNavigate}
                    className={cn(
                      'flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all group',
                      active
                        ? 'bg-brand/10 text-brand-700'
                        : item.highlight
                          ? 'gradient-brand text-white shadow-sm hover:opacity-90'
                          : 'text-muted-foreground hover:text-foreground hover:bg-accent/60',
                    )}
                  >
                    <div className="flex items-center gap-2.5">
                      <Icon className={cn('h-4 w-4', active ? 'text-brand-700' : item.highlight && !active ? 'text-white' : '')} />
                      {item.label}
                    </div>
                    {active && <ChevronRight className="h-3 w-3 text-brand-400" />}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="p-3 border-t border-border/60 space-y-2">
        {user && (
          <div className="flex items-center gap-3 px-3 py-2 rounded-lg bg-brand/5">
            <div className="w-8 h-8 rounded-full gradient-brand flex items-center justify-center text-white text-xs font-bold shrink-0">
              {(user.full_name ?? user.email ?? '?').charAt(0).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="font-medium text-sm truncate">{user.full_name ?? user.email}</div>
              <div className="text-[11px] text-muted-foreground truncate">{user.email}</div>
            </div>
          </div>
        )}
        <button
          onClick={logout}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
        >
          <LogOut className="h-4 w-4" />
          Cerrar sesión
        </button>
      </div>
    </aside>
  );
}
