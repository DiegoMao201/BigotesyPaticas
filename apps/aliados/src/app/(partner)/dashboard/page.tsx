'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { CalendarCheck, Clock, Star, ArrowRight, Sparkles, CalendarClock, Store } from 'lucide-react';
import { partner } from '@/lib/api';

const QUICK_LINKS = [
  { href: '/servicios', label: 'Mis servicios', sub: 'Crea y edita lo que ofreces', icon: Sparkles, grad: 'linear-gradient(135deg,#1ea89e,#085041)' },
  { href: '/disponibilidad', label: 'Disponibilidad', sub: 'Configura tu horario semanal', icon: CalendarClock, grad: 'linear-gradient(135deg,#f5b942,#b8760a)' },
  { href: '/perfil', label: 'Mi perfil', sub: 'Datos, ubicación y contacto', icon: Store, grad: 'linear-gradient(150deg,#0d4a45,#062e2a)' },
];

export default function DashboardPage() {
  const { data, isLoading } = useQuery({ queryKey: ['partner-dashboard'], queryFn: () => partner.dashboard() });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground">
          Hola, {data?.partner.business_name ?? '...'}
        </h1>
        <p className="text-muted text-sm mt-1">Este es el resumen de tu actividad como aliado.</p>
      </div>

      {!isLoading && !data?.partner.is_published && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 flex items-center gap-3">
          <Clock className="h-5 w-5 text-amber-600 shrink-0" />
          <p className="text-sm text-amber-800">
            Tu negocio está <strong>pendiente de aprobación</strong>. Aprovecha para completar tu
            perfil, servicios y disponibilidad — se publicará automáticamente apenas el equipo lo revise.
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg,#f5b942,#b8760a)' }}>
            <Clock className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-display font-extrabold text-foreground">{data?.pending_bookings ?? '–'}</p>
            <p className="text-xs text-muted">Reservas por confirmar</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg,#1ea89e,#085041)' }}>
            <CalendarCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-display font-extrabold text-foreground">{data?.today_bookings ?? '–'}</p>
            <p className="text-xs text-muted">Reservas hoy</p>
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: 'linear-gradient(135deg,#f59e0b,#d97706)' }}>
            <Star className="h-5 w-5" />
          </div>
          <div>
            <p className="text-2xl font-display font-extrabold text-foreground">
              {data && data.partner.rating_count > 0 ? data.partner.rating_avg.toFixed(1) : '–'}
            </p>
            <p className="text-xs text-muted">
              {data && data.partner.rating_count > 0 ? `${data.partner.rating_count} reseñas` : 'Sin reseñas todavía'}
            </p>
          </div>
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display font-bold text-foreground">Reservas recientes</h2>
          <Link href="/reservas" className="text-sm text-primary-700 font-semibold inline-flex items-center gap-1 hover:underline">
            Ver todas <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>
        <div className="card text-sm text-muted">
          Ve a <Link href="/reservas" className="text-primary-700 font-semibold">Reservas</Link> para confirmar,
          completar o gestionar lo que los clientes te están enviando.
        </div>
      </div>

      <div>
        <h2 className="font-display font-bold text-foreground mb-3">Configura tu negocio</h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {QUICK_LINKS.map(({ href, label, sub, icon: Icon, grad }) => (
            <Link key={href} href={href} className="card flex flex-col gap-3 hover:shadow-card-hover transition-shadow">
              <div className="h-11 w-11 rounded-xl flex items-center justify-center text-white" style={{ background: grad }}>
                <Icon className="h-5 w-5" />
              </div>
              <div>
                <p className="font-display font-bold text-foreground text-[15px]">{label}</p>
                <p className="text-muted text-xs mt-0.5">{sub}</p>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
