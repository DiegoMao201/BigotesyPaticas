'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Heart, Package, Calendar, Star, ChevronRight, AlertCircle } from 'lucide-react';
import { auth, pets, loyalty, orders } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { usePetStore, PET_THEME_COLORS } from '@/lib/pet-store';
import { formatCOP, getSpeciesEmoji, formatRelativeDate } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export default function DashboardPage() {
  const { customer } = useAuthStore();
  const { getActivePet, setActivePet, activePetId } = usePetStore();

  const { data: petsData, isLoading: petsLoading } = useQuery({
    queryKey: ['portal-pets'],
    queryFn: pets.list,
  });

  const { data: loyaltyData } = useQuery({
    queryKey: ['portal-loyalty'],
    queryFn: loyalty.balance,
  });

  const { data: recentOrders } = useQuery({
    queryKey: ['portal-orders', 1],
    queryFn: () => orders.list(1),
  });

  const activePet = petsData ? getActivePet(petsData) : null;
  const theme = activePet ? PET_THEME_COLORS[activePet.color_theme] : PET_THEME_COLORS.teal;

  // Alertas de salud próximas/vencidas
  const healthAlerts = activePet?.health_records.filter(
    (hr) => hr.alert_level === 'overdue' || hr.alert_level === 'soon'
  ) ?? [];

  if (petsLoading) return <LoadingSpinner />;

  return (
    <div data-pet-theme={activePet?.color_theme ?? 'teal'} className="flex flex-col gap-5 p-4 pt-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-muted text-sm">¡Hola,</p>
            <h1 className="font-display text-2xl font-bold text-foreground">
              {customer?.full_name?.split(' ')[0] ?? 'amig@'} 🐾
            </h1>
          </div>
          <Link href="/profile">
            <div
              className="h-11 w-11 rounded-full flex items-center justify-center text-white font-bold text-lg"
              style={{ backgroundColor: theme.primary }}
            >
              {customer?.full_name?.[0]?.toUpperCase() ?? '?'}
            </div>
          </Link>
        </div>
      </motion.div>

      {/* Pet selector */}
      {petsData && petsData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex gap-3 overflow-x-auto scrollbar-hide pb-1"
        >
          {petsData.map((pet) => {
            const petTheme = PET_THEME_COLORS[pet.color_theme];
            const isActive = activePet?.id === pet.id;
            return (
              <button
                key={pet.id}
                onClick={() => setActivePet(pet.id)}
                className="flex flex-col items-center gap-1.5 min-w-[72px] transition-transform active:scale-95"
              >
                <div
                  className="h-14 w-14 rounded-2xl flex items-center justify-center text-2xl border-3 transition-all"
                  style={{
                    backgroundColor: isActive ? petTheme.primary : petTheme.light,
                    borderColor: isActive ? petTheme.dark : 'transparent',
                  }}
                >
                  {getSpeciesEmoji(pet.species)}
                </div>
                <span
                  className="text-xs font-semibold truncate w-16 text-center"
                  style={{ color: isActive ? petTheme.dark : '#6b7280' }}
                >
                  {pet.name}
                </span>
              </button>
            );
          })}

          <Link
            href="/pets/new"
            className="flex flex-col items-center gap-1.5 min-w-[72px]"
          >
            <div className="h-14 w-14 rounded-2xl flex items-center justify-center text-2xl bg-border border-2 border-dashed border-muted/50">
              +
            </div>
            <span className="text-xs text-muted font-medium">Agregar</span>
          </Link>
        </motion.div>
      )}

      {/* Sin mascotas → CTA */}
      {petsData?.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card flex flex-col items-center gap-3 py-8 text-center"
        >
          <div className="text-4xl">🐾</div>
          <p className="font-semibold text-foreground">Registra tu primera mascota</p>
          <p className="text-muted text-sm">Lleva el control de su salud y alimentación.</p>
          <Link href="/pets/new" className="btn-primary">
            Agregar mascota
          </Link>
        </motion.div>
      )}

      {/* Health alerts */}
      {healthAlerts.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl border-l-4 p-4 flex gap-3"
          style={{ borderColor: theme.primary, backgroundColor: theme.light }}
        >
          <AlertCircle className="h-5 w-5 mt-0.5 shrink-0" style={{ color: theme.dark }} />
          <div>
            <p className="font-semibold text-sm" style={{ color: theme.dark }}>
              {healthAlerts.length === 1
                ? `${activePet?.name} tiene 1 alerta de salud`
                : `${activePet?.name} tiene ${healthAlerts.length} alertas de salud`}
            </p>
            <p className="text-xs mt-0.5" style={{ color: theme.primary }}>
              {healthAlerts[0].name} —{' '}
              {healthAlerts[0].alert_level === 'overdue' ? 'Vencida' : 'Próxima'}
            </p>
          </div>
          <Link href={`/pets/${activePet?.id}`} className="ml-auto">
            <ChevronRight className="h-5 w-5" style={{ color: theme.primary }} />
          </Link>
        </motion.div>
      )}

      {/* Puntos de fidelidad */}
      {loyaltyData && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="rounded-2xl p-4 flex items-center gap-4"
          style={{ background: `linear-gradient(135deg, ${theme.primary}, ${theme.dark})` }}
        >
          <div className="h-12 w-12 rounded-xl bg-white/20 flex items-center justify-center">
            <Star className="h-6 w-6 text-white" />
          </div>
          <div className="flex-1">
            <p className="text-white/80 text-xs font-medium">Puntos de fidelidad</p>
            <p className="text-white text-2xl font-bold">{loyaltyData.total_active}</p>
            <p className="text-white/70 text-xs">pts activos</p>
          </div>
          <div className="text-right">
            <p className="text-white/80 text-xs">Total ganado</p>
            <p className="text-white font-semibold">{loyaltyData.total_earned_lifetime}</p>
          </div>
        </motion.div>
      )}

      {/* Accesos rápidos */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="grid grid-cols-3 gap-3"
      >
        {[
          { href: '/pets', icon: Heart, label: 'Mascotas', emoji: '🐾' },
          { href: '/orders/new', icon: Package, label: 'Pedir', emoji: '📦' },
          { href: '/appointments', icon: Calendar, label: 'Citas', emoji: '📅' },
        ].map(({ href, label, emoji }) => (
          <Link
            key={href}
            href={href}
            className="card flex flex-col items-center gap-2 py-4 hover:shadow-card-hover transition-shadow active:scale-95"
          >
            <span className="text-2xl">{emoji}</span>
            <span className="text-xs font-semibold text-foreground">{label}</span>
          </Link>
        ))}
      </motion.div>

      {/* Últimos pedidos */}
      {recentOrders && recentOrders.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display font-bold text-foreground">Últimos pedidos</h2>
            <Link href="/orders" className="text-xs font-semibold" style={{ color: theme.primary }}>
              Ver todos
            </Link>
          </div>
          <div className="flex flex-col gap-2">
            {recentOrders.slice(0, 3).map((order) => (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="card flex items-center gap-3 py-3"
              >
                <div className="text-xl">📦</div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground truncate">{order.product_name}</p>
                  <p className="text-xs text-muted">{formatRelativeDate(order.created_at)}</p>
                </div>
                <OrderStatusBadge status={order.status} />
              </Link>
            ))}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function OrderStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string }> = {
    received:   { label: 'Recibido',    color: 'bg-blue-50 text-blue-700' },
    processing: { label: 'En proceso',  color: 'bg-amber-50 text-amber-700' },
    ready:      { label: 'Listo',       color: 'bg-green-50 text-green-700' },
    delivered:  { label: 'Entregado',   color: 'bg-gray-100 text-gray-600' },
    cancelled:  { label: 'Cancelado',   color: 'bg-red-50 text-red-700' },
  };
  const { label, color } = map[status] ?? { label: status, color: 'bg-gray-100 text-gray-600' };
  return (
    <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${color}`}>{label}</span>
  );
}
