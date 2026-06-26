'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Plus, Calendar } from 'lucide-react';
import { appointments } from '@/lib/api';
import { formatDate } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const STATUS: Record<string, { label: string; color: string }> = {
  pending:   { label: 'Pendiente',   color: 'bg-blue-50 text-blue-700' },
  confirmed: { label: 'Confirmada',  color: 'bg-green-50 text-green-700' },
  completed: { label: 'Completada',  color: 'bg-gray-100 text-gray-600' },
  cancelled: { label: 'Cancelada',   color: 'bg-red-50 text-red-700' },
};

const SERVICE_EMOJIS: Record<string, string> = {
  baño: '🛁', grooming: '✂️', consulta: '🩺', vacuna: '💉',
  desparasitacion: '🪱', peluqueria: '✂️', otro: '📅',
};

export default function AppointmentsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['portal-appointments'],
    queryFn: () => appointments.list(),
  });

  if (isLoading) return <LoadingSpinner />;

  const upcoming = data?.filter((a) => a.status === 'pending' || a.status === 'confirmed') ?? [];
  const past = data?.filter((a) => a.status === 'completed' || a.status === 'cancelled') ?? [];

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-foreground">Citas</h1>
        <Link href="/appointments/new" className="btn-primary py-2 px-4 text-xs">
          <Plus className="h-4 w-4" /> Agendar
        </Link>
      </div>

      {data?.length === 0 && (
        <div className="card flex flex-col items-center gap-4 py-12 text-center">
          <Calendar className="h-12 w-12 text-primary-200" />
          <p className="font-semibold text-foreground">Sin citas programadas</p>
          <p className="text-muted text-sm">Agenda un baño, grooming o consulta veterinaria.</p>
          <Link href="/appointments/new" className="btn-primary">Agendar cita</Link>
        </div>
      )}

      {upcoming.length > 0 && (
        <div>
          <h2 className="font-bold text-foreground mb-3">Próximas</h2>
          <div className="flex flex-col gap-2">
            {upcoming.map((appt, i) => {
              const { label, color } = STATUS[appt.status];
              return (
                <motion.div
                  key={appt.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  className="card flex items-center gap-4 py-3"
                >
                  <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0">
                    {SERVICE_EMOJIS[appt.service_type.toLowerCase()] ?? '📅'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-foreground text-sm capitalize">{appt.service_type}</p>
                    <p className="text-xs text-muted">
                      {formatDate(appt.scheduled_at)} • {new Date(appt.scheduled_at).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${color}`}>{label}</span>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}

      {past.length > 0 && (
        <div>
          <h2 className="font-bold text-foreground mb-3 text-muted">Historial</h2>
          <div className="flex flex-col gap-2">
            {past.slice(0, 5).map((appt) => {
              const { label, color } = STATUS[appt.status];
              return (
                <div key={appt.id} className="card flex items-center gap-4 py-3 opacity-75">
                  <div className="h-10 w-10 rounded-xl bg-gray-50 flex items-center justify-center text-xl shrink-0">
                    {SERVICE_EMOJIS[appt.service_type.toLowerCase()] ?? '📅'}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-foreground text-sm capitalize">{appt.service_type}</p>
                    <p className="text-xs text-muted">{formatDate(appt.scheduled_at)}</p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${color}`}>{label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
