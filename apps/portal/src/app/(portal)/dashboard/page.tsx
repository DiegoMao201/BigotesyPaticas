'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, Package, Calendar, ChevronRight, RefreshCw } from 'lucide-react';
import { pets, loyalty, orders, intelligence } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { usePetStore } from '@/lib/pet-store';
import { formatCOP, formatRelativeDate, getSpeciesEmoji } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { SmartCards } from '@/components/portal/SmartCards';
import { ProfileCompletion } from '@/components/portal/ProfileCompletion';

// Mapa de colores por tema — referencia visual del mockup
const THEME: Record<string, { accent: string; light: string; dark: string; text: string; grad: string }> = {
  teal:   { accent: '#187f77', light: '#E1F5EE', dark: '#085041', text: '#085041', grad: 'linear-gradient(135deg,#187f77,#085041)' },
  coral:  { accent: '#D85A30', light: '#FAECE7', dark: '#712B13', text: '#712B13', grad: 'linear-gradient(135deg,#D85A30,#712B13)' },
  amber:  { accent: '#BA7517', light: '#FAEEDA', dark: '#633806', text: '#633806', grad: 'linear-gradient(135deg,#BA7517,#633806)' },
  purple: { accent: '#534AB7', light: '#EEEDFE', dark: '#3C3489', text: '#3C3489', grad: 'linear-gradient(135deg,#534AB7,#3C3489)' },
  pink:   { accent: '#D4537E', light: '#FBEAF0', dark: '#72243E', text: '#72243E', grad: 'linear-gradient(135deg,#D4537E,#72243E)' },
  green:  { accent: '#639922', light: '#EAF3DE', dark: '#27500A', text: '#27500A', grad: 'linear-gradient(135deg,#639922,#27500A)' },
};

function greeting(name: string) {
  const h = new Date().getHours();
  const saludo = h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
  return { saludo, nombre: name?.split(' ')[0] ?? 'amig@' };
}

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  received:   { label: 'Recibido',    color: 'bg-blue-50 text-blue-700' },
  processing: { label: 'En proceso',  color: 'bg-amber-50 text-amber-700' },
  ready:      { label: 'Listo 🎉',    color: 'bg-green-50 text-green-700' },
  delivered:  { label: 'Entregado',   color: 'bg-gray-100 text-gray-600' },
  cancelled:  { label: 'Cancelado',   color: 'bg-red-50 text-red-600' },
};

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
    staleTime: 30 * 1000,
  });

  const { data: recentOrders } = useQuery({
    queryKey: ['portal-orders', 1],
    queryFn: () => orders.list(1),
    refetchInterval: 20 * 1000,
    staleTime: 15 * 1000,
  });

  const { data: smartCards } = useQuery({
    queryKey: ['portal-smart-cards'],
    queryFn: intelligence.smartCards,
    staleTime: 15 * 1000,
  });

  const activePet = petsData ? getActivePet(petsData) : null;
  const theme = THEME[activePet?.color_theme ?? 'teal'];
  const { saludo, nombre } = greeting(customer?.full_name ?? '');
  const urgentAlerts = smartCards?.filter((c) => c.urgency === 'high').length ?? 0;

  if (petsLoading) return <LoadingSpinner />;

  // Premio próximo (cada 1500 pts = $15,000 off)
  const pts = loyaltyData?.total_active ?? 0;
  const PRIZE_THRESHOLD = 1500;
  const ptsToNextPrize = PRIZE_THRESHOLD - (pts % PRIZE_THRESHOLD);
  const prizeProgress = ((pts % PRIZE_THRESHOLD) / PRIZE_THRESHOLD) * 100;

  return (
    <div
      data-pet-theme={activePet?.color_theme ?? 'teal'}
      className="flex flex-col gap-5 p-4 pt-6 pb-6"
    >
      {/* ── Header ────────────────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-start justify-between"
      >
        <div>
          <p className="text-muted text-sm font-medium">{saludo},</p>
          <h1
            className="font-display text-[22px] font-semibold leading-tight"
            style={{ color: theme.dark }}
          >
            {nombre} 🐾
          </h1>
          {urgentAlerts > 0 && (
            <p className="text-xs mt-0.5 font-medium" style={{ color: theme.accent }}>
              Tienes {urgentAlerts} alerta{urgentAlerts !== 1 ? 's' : ''} pendiente{urgentAlerts !== 1 ? 's' : ''}
            </p>
          )}
        </div>

        <Link href="/profile">
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="h-11 w-11 rounded-full flex items-center justify-center text-white font-bold text-lg shadow-sm"
            style={{ background: theme.grad }}
          >
            {customer?.full_name?.[0]?.toUpperCase() ?? '?'}
          </motion.div>
        </Link>
      </motion.div>

      {/* ── Selector de mascotas ───────────────────────────────────────── */}
      {petsData && petsData.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.07 }}
          className="flex gap-3 overflow-x-auto scrollbar-hide pb-1"
        >
          <AnimatePresence>
            {petsData.map((pet, idx) => {
              const t = THEME[pet.color_theme] ?? THEME.teal;
              const isActive = (activePetId === pet.id) || (!activePetId && idx === 0);
              return (
                <motion.button
                  key={pet.id}
                  onClick={() => setActivePet(pet.id)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.93 }}
                  animate={{ scale: isActive ? 1.05 : 1 }}
                  transition={{ type: 'spring', stiffness: 400, damping: 22 }}
                  className="flex flex-col items-center gap-1.5 min-w-[72px]"
                >
                  <div
                    className="h-14 w-14 rounded-2xl flex items-center justify-center text-[26px] transition-all"
                    style={{
                      background: isActive ? t.grad : t.light,
                      boxShadow: isActive
                        ? `0 4px 16px ${t.accent}40`
                        : 'none',
                      border: isActive ? `2px solid ${t.dark}` : '2px solid transparent',
                    }}
                  >
                    {getSpeciesEmoji(pet.species)}
                  </div>
                  <span
                    className="text-xs font-semibold truncate w-16 text-center"
                    style={{ color: isActive ? t.dark : '#6b7280' }}
                  >
                    {pet.name}
                  </span>
                </motion.button>
              );
            })}
          </AnimatePresence>

          <Link href="/pets/new" className="flex flex-col items-center gap-1.5 min-w-[72px]">
            <div className="h-14 w-14 rounded-2xl flex items-center justify-center text-2xl bg-white border-2 border-dashed border-gray-200 text-gray-400 hover:border-gray-300 transition-colors">
              +
            </div>
            <span className="text-xs text-muted font-medium">Agregar</span>
          </Link>
        </motion.div>
      )}

      {/* ── Sin mascotas → CTA ────────────────────────────────────────── */}
      {petsData?.length === 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="card-glass flex flex-col items-center gap-3 py-8 text-center"
        >
          <div className="text-5xl">🐾</div>
          <p className="font-display font-semibold text-foreground">Registra tu primera mascota</p>
          <p className="text-muted text-sm">Lleva el control de su salud y alimentación.</p>
          <Link href="/pets/new" className="btn-primary">Agregar mascota</Link>
        </motion.div>
      )}

      {/* ── Info activa de la mascota ─────────────────────────────────── */}
      <AnimatePresence mode="wait">
        {activePet && (
          <motion.div
            key={activePet.id}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.22 }}
          >
            <Link href={`/pets/${activePet.id}`}>
              <div
                className="rounded-2xl p-4 flex items-start gap-4"
                style={{ background: theme.grad, boxShadow: `0 4px 20px ${theme.accent}30` }}
              >
                <div
                  className="h-12 w-12 rounded-2xl flex items-center justify-center text-2xl shrink-0"
                  style={{ background: 'rgba(255,255,255,0.2)' }}
                >
                  {getSpeciesEmoji(activePet.species)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-white font-display font-bold text-lg leading-tight">
                    {activePet.name}
                    {activePet.breed ? ` · ${activePet.breed}` : ''}
                    {activePet.age_years ? ` · ${activePet.age_years} año${activePet.age_years !== 1 ? 's' : ''}` : ''}
                  </p>
                  {/* Alertas de salud inline */}
                  {activePet.health_records
                    .filter((hr) => hr.alert_level === 'overdue' || hr.alert_level === 'soon')
                    .slice(0, 2)
                    .map((hr) => (
                      <p key={hr.id} className="text-white/80 text-xs mt-1 flex items-center gap-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-amber-300 shrink-0" />
                        {hr.name} · {hr.alert_level === 'overdue' ? 'Vencida' : `Vence en ${hr.days_until_due} días`}
                      </p>
                    ))}
                  {activePet.food_brand && (
                    <p className="text-white/65 text-xs mt-1">{activePet.food_brand}</p>
                  )}
                </div>
                <ChevronRight className="h-5 w-5 text-white/70 mt-1 shrink-0" />
              </div>
            </Link>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Puntos Bigotes ────────────────────────────────────────────── */}
      {loyaltyData !== undefined && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15 }}
          className="rounded-2xl p-4"
          style={{
            background: 'linear-gradient(135deg, #0f2027, #203a43, #2c5364)',
            boxShadow: '0 4px 24px rgba(0,0,0,0.18)',
          }}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2.5">
              <div className="h-9 w-9 rounded-xl bg-white/15 flex items-center justify-center">
                <Star className="h-4 w-4 text-amber-400 fill-amber-400" />
              </div>
              <div>
                <p className="text-white/70 text-[10px] font-semibold uppercase tracking-wide">Puntos Bigotes</p>
                <p className="text-white text-2xl font-bold leading-none count-up">{loyaltyData.total_active.toLocaleString('es-CO')}</p>
              </div>
            </div>
            <div className="text-right">
              <p className="text-white/60 text-[10px] uppercase tracking-wide">Próximo premio</p>
              <p className="text-amber-400 font-bold text-sm">$15.000 off</p>
              <p className="text-white/50 text-[10px]">{ptsToNextPrize} pts más</p>
            </div>
          </div>
          {/* Barra de progreso */}
          <div className="h-2 rounded-full bg-white/10 overflow-hidden mt-1">
            <motion.div
              className="h-full rounded-full"
              style={{ background: 'linear-gradient(90deg, #f5a641, #fbbf24)' }}
              initial={{ width: 0 }}
              animate={{ width: `${prizeProgress}%` }}
              transition={{ duration: 1, ease: 'easeOut', delay: 0.3 }}
            />
          </div>
        </motion.div>
      )}

      {/* ── Smart Cards ───────────────────────────────────────────────── */}
      <SmartCards max={3} />

      {/* ── Profile Completion ────────────────────────────────────────── */}
      <ProfileCompletion />

      {/* ── Accesos rápidos ───────────────────────────────────────────── */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
        className="grid grid-cols-3 gap-3"
      >
        {[
          { href: '/pets', emoji: '🐾', label: 'Mascotas' },
          { href: '/orders/new', emoji: '📦', label: 'Pedir' },
          { href: '/appointments/new', emoji: '📅', label: 'Cita' },
        ].map(({ href, emoji, label }, i) => (
          <motion.div
            key={href}
            whileHover={{ y: -2, scale: 1.02 }}
            whileTap={{ scale: 0.96 }}
            transition={{ type: 'spring', stiffness: 400 }}
          >
            <Link
              href={href}
              className="card-glass flex flex-col items-center gap-2 py-5 transition-shadow hover:shadow-card-hover"
            >
              <span className="text-2xl">{emoji}</span>
              <span className="text-xs font-semibold" style={{ color: theme.dark }}>{label}</span>
            </Link>
          </motion.div>
        ))}
      </motion.div>

      {/* ── Actividad reciente ────────────────────────────────────────── */}
      {recentOrders && recentOrders.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.32 }}
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-display font-bold text-foreground text-base">Actividad reciente</h2>
            <Link
              href="/orders"
              className="text-xs font-semibold flex items-center gap-0.5"
              style={{ color: theme.accent }}
            >
              Ver todo <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="flex flex-col gap-2.5">
            {recentOrders.slice(0, 3).map((order, i) => {
              const { label, color } = STATUS_LABELS[order.status] ?? { label: order.status, color: 'bg-gray-100 text-gray-600' };
              return (
                <motion.div
                  key={order.id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.35 + i * 0.06 }}
                >
                  <Link href={`/orders/${order.id}`} className="card-glass flex items-center gap-3.5 py-3">
                    <div
                      className="h-10 w-10 rounded-xl flex items-center justify-center text-xl shrink-0"
                      style={{ background: theme.light }}
                    >
                      📦
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-foreground truncate">{order.product_name}</p>
                      <p className="text-xs text-muted">{formatRelativeDate(order.created_at)}</p>
                      {order.points_earned && (
                        <p className="text-[10px] text-amber-600 font-semibold">+{order.points_earned} puntos</p>
                      )}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full ${color}`}>{label}</span>
                      {order.unit_price && (
                        <span className="text-[10px] text-muted">{formatCOP(order.unit_price * order.quantity)}</span>
                      )}
                    </div>
                  </Link>
                </motion.div>
              );
            })}
          </div>

          {/* Repetir último pedido CTA */}
          {recentOrders[0] && (
            <Link
              href="/orders/new"
              className="mt-3 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all active:scale-95"
              style={{ background: theme.light, color: theme.dark }}
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Repetir: {recentOrders[0].product_name.split(' ').slice(0, 3).join(' ')}
            </Link>
          )}
        </motion.div>
      )}
    </div>
  );
}
