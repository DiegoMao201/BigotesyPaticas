'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Heart, Home, Package, Calendar, User } from 'lucide-react';
import { cn } from '@/lib/utils';

const NAV_ITEMS = [
  { href: '/dashboard', icon: Home, label: 'Inicio' },
  { href: '/pets', icon: Heart, label: 'Mascotas' },
  { href: '/orders', icon: Package, label: 'Pedidos' },
  { href: '/appointments', icon: Calendar, label: 'Citas' },
  { href: '/profile', icon: User, label: 'Perfil' },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <nav className="bottom-nav">
      <div className="flex items-center justify-around px-2 py-2">
        {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
          const active = pathname === href || pathname.startsWith(href + '/');
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex flex-col items-center gap-0.5 px-3 py-1 rounded-xl transition-colors',
                active
                  ? 'text-primary-700'
                  : 'text-muted hover:text-primary-600'
              )}
            >
              <Icon
                className={cn('h-5 w-5 transition-transform', active && 'scale-110')}
                strokeWidth={active ? 2.5 : 1.75}
              />
              <span className={cn('text-[10px] font-medium', active && 'font-semibold')}>
                {label}
              </span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
