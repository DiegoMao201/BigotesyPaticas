'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarCheck, Check, X, Clock, UserX, MessageCircle } from 'lucide-react';
import { toast } from 'sonner';
import { partner, type BookingItem } from '@/lib/api';
import { formatDateTime, formatCOP } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const TABS: { value: string; label: string }[] = [
  { value: 'pending', label: 'Por confirmar' },
  { value: 'confirmed', label: 'Confirmadas' },
  { value: 'completed', label: 'Completadas' },
  { value: 'cancelled', label: 'Canceladas' },
];

const STATUS_BADGE: Record<BookingItem['status'], { variant: 'default' | 'success' | 'warning' | 'danger' | 'neutral'; label: string }> = {
  pending: { variant: 'warning', label: 'Por confirmar' },
  confirmed: { variant: 'default', label: 'Confirmada' },
  completed: { variant: 'success', label: 'Completada' },
  cancelled: { variant: 'danger', label: 'Cancelada' },
  no_show: { variant: 'neutral', label: 'No llegó' },
};

function BookingCard({ booking }: { booking: BookingItem }) {
  const qc = useQueryClient();
  const invalidate = () => qc.invalidateQueries({ queryKey: ['partner-bookings'] });

  const confirmMut = useMutation({
    mutationFn: () => partner.bookings.confirm(booking.id),
    onSuccess: () => { toast.success('Reserva confirmada'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const completeMut = useMutation({
    mutationFn: () => partner.bookings.complete(booking.id),
    onSuccess: () => { toast.success('Reserva marcada como completada'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const noShowMut = useMutation({
    mutationFn: () => partner.bookings.noShow(booking.id),
    onSuccess: () => { toast.success('Marcada como no-show'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });
  const cancelMut = useMutation({
    mutationFn: () => partner.bookings.cancel(booking.id, 'Cancelada por el aliado'),
    onSuccess: () => { toast.success('Reserva cancelada'); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const st = STATUS_BADGE[booking.status];

  return (
    <div className="card flex flex-col gap-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-semibold text-foreground">{formatDateTime(booking.scheduled_at)}</p>
          <p className="text-xs text-muted mt-0.5">{booking.duration_min} min</p>
        </div>
        <Badge variant={st.variant}>{st.label}</Badge>
      </div>

      {booking.price_snapshot != null && (
        <p className="text-sm text-foreground/80">Valor: <strong>{formatCOP(booking.price_snapshot)}</strong></p>
      )}
      {booking.notes_customer && (
        <p className="text-sm text-foreground/70 flex items-start gap-1.5">
          <MessageCircle className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted" /> {booking.notes_customer}
        </p>
      )}
      {booking.cancelled_reason && (
        <p className="text-xs text-red-600">Motivo: {booking.cancelled_reason}</p>
      )}

      {(booking.status === 'pending' || booking.status === 'confirmed') && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-border">
          {booking.status === 'pending' && (
            <Button size="sm" onClick={() => confirmMut.mutate()} disabled={confirmMut.isPending}>
              <Check className="h-3.5 w-3.5" /> Confirmar
            </Button>
          )}
          {booking.status === 'confirmed' && (
            <Button size="sm" onClick={() => completeMut.mutate()} disabled={completeMut.isPending}>
              <CalendarCheck className="h-3.5 w-3.5" /> Completar
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={() => noShowMut.mutate()} disabled={noShowMut.isPending}>
            <UserX className="h-3.5 w-3.5" /> No llegó
          </Button>
          <Button size="sm" variant="danger" onClick={() => cancelMut.mutate()} disabled={cancelMut.isPending}>
            <X className="h-3.5 w-3.5" /> Cancelar
          </Button>
        </div>
      )}
    </div>
  );
}

export default function ReservasPage() {
  const [tab, setTab] = useState('pending');

  const { data, isLoading } = useQuery({
    queryKey: ['partner-bookings', tab],
    queryFn: () => partner.bookings.list(tab),
  });

  const bookings = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
          <CalendarCheck className="h-6 w-6 text-primary-700" /> Reservas
        </h1>
        <p className="text-muted text-sm mt-1">Lo que los clientes te están agendando.</p>
      </div>

      <div className="flex gap-2 border-b border-border overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.value}
            onClick={() => setTab(t.value)}
            className={
              'shrink-0 px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ' +
              (tab === t.value ? 'border-primary-700 text-primary-700' : 'border-transparent text-muted hover:text-foreground')
            }
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading && <p className="text-sm text-muted">Cargando…</p>}

      {!isLoading && bookings.length === 0 && (
        <div className="card text-center py-10 text-muted text-sm flex flex-col items-center gap-2">
          <Clock className="h-8 w-8 text-muted/50" />
          No hay reservas en este estado todavía.
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {bookings.map((b) => (
          <BookingCard key={b.id} booking={b} />
        ))}
      </div>
    </div>
  );
}
