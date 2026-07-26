'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Heart, Home, Package, Calendar, User } from 'lucide-react';
import { motion } from 'framer-motion';
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
              className="relative flex flex-col items-center gap-0.5 px-3 py-1"
            >
              {/* Indicador activo con layoutId para animación fluida */}
              {active && (
                <motion.div
                  layoutId="nav-active-bg"
                  className="absolute inset-0 rounded-xl bg-primary-50"
                  transition={{ type: 'spring', damping: 20, stiffness: 300 }}
                />
              )}
              <motion.div
                whileTap={{ scale: 0.85 }}
                transition={{ type: 'spring', damping: 15 }}
                className="relative z-10 flex flex-col items-center gap-0.5"
              >
                <Icon
                  className={cn(
                    'h-5 w-5 transition-colors',
                    active ? 'text-primary-700' : 'text-muted'
                  )}
                  strokeWidth={active ? 2.5 : 1.75}
                />
                <span className={cn(
                  'text-[10px] transition-colors',
                  active ? 'font-semibold text-primary-700' : 'font-medium text-muted'
                )}>
                  {label}
                </span>
              </motion.div>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
