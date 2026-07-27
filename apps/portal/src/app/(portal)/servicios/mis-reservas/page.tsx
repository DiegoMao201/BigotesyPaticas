'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { ArrowLeft, Star, X } from 'lucide-react';
import { toast } from 'sonner';
import { myBookings, type MyBooking } from '@/lib/api';
import { formatCOP } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const PARTNER_EMOJI: Record<string, string> = { vet: '🩺', walker: '🐕', shelter: '🏠', groomer: '✂️' };

const STATUS_LABEL: Record<MyBooking['status'], { label: string; cls: string }> = {
  pending: { label: 'Por confirmar', cls: 'bg-amber-50 text-amber-700' },
  confirmed: { label: 'Confirmada', cls: 'bg-primary-50 text-primary-700' },
  completed: { label: 'Completada', cls: 'bg-emerald-50 text-emerald-700' },
  cancelled: { label: 'Cancelada', cls: 'bg-red-50 text-red-600' },
  no_show: { label: 'No asististe', cls: 'bg-gray-100 text-gray-500' },
};

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('es-CO', {
    weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
  });
}

function ReviewForm({ booking, onDone }: { booking: MyBooking; onDone: () => void }) {
  const qc = useQueryClient();
  const [rating, setRating] = useState(0);
  const [hovered, setHovered] = useState(0);
  const [comment, setComment] = useState('');

  const reviewMut = useMutation({
    mutationFn: () => myBookings.review(booking.id, rating, comment || undefined),
    onSuccess: () => {
      toast.success('¡Gracias por calificar!');
      qc.invalidateQueries({ queryKey: ['my-bookings'] });
      onDone();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="card border-2 border-primary-200 flex flex-col gap-3 mt-2">
      <p className="text-sm font-semibold text-foreground">¿Cómo estuvo tu experiencia con {booking.partner_name}?</p>
      <div className="flex justify-center gap-1.5">
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} onMouseEnter={() => setHovered(n)} onMouseLeave={() => setHovered(0)} onClick={() => setRating(n)}>
            <Star className={`w-8 h-8 transition-colors ${n <= (hovered || rating) ? 'fill-amber-400 text-amber-400' : 'fill-gray-200 text-gray-200'}`} />
          </button>
        ))}
      </div>
      {rating > 0 && rating <= 3 && (
        <textarea
          className="input-field resize-none"
          rows={2}
          placeholder="¿Qué podemos mejorar? (opcional)"
          value={comment}
          onChange={(e) => setComment(e.target.value)}
        />
      )}
      <button
        onClick={() => reviewMut.mutate()}
        disabled={!rating || reviewMut.isPending}
        className="btn-primary w-full text-sm"
      >
        Enviar calificación
      </button>
    </div>
  );
}

function BookingRow({ booking, i }: { booking: MyBooking; i: number }) {
  const qc = useQueryClient();
  const [showReview, setShowReview] = useState(false);
  const st = STATUS_LABEL[booking.status];

  const cancelMut = useMutation({
    mutationFn: () => myBookings.cancel(booking.id),
    onSuccess: () => {
      toast.success('Reserva cancelada');
      qc.invalidateQueries({ queryKey: ['my-bookings'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
      <div className="card flex flex-col gap-2">
        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-xl shrink-0 bg-[#E1F5EE] flex items-center justify-center text-xl">
            {PARTNER_EMOJI[booking.partner_type] ?? '🤝'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-semibold text-foreground truncate">{booking.partner_name}</p>
              <span className={`text-[10px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-full ${st.cls}`}>{st.label}</span>
            </div>
            <p className="text-xs text-muted">{booking.service_name ?? 'Servicio'} · {formatDateTime(booking.scheduled_at)}</p>
            {booking.price_snapshot != null && (
              <p className="text-xs text-foreground/70 mt-0.5">{formatCOP(booking.price_snapshot)}</p>
            )}
            {booking.cancelled_reason && <p className="text-[11px] text-red-600 mt-0.5">{booking.cancelled_reason}</p>}
          </div>
        </div>

        {(booking.status === 'pending' || booking.status === 'confirmed') && (
          <button
            onClick={() => cancelMut.mutate()}
            disabled={cancelMut.isPending}
            className="self-start text-xs font-semibold text-red-600 inline-flex items-center gap-1 mt-1"
          >
            <X className="h-3 w-3" /> Cancelar reserva
          </button>
        )}

        {booking.status === 'completed' && !booking.reviewed && !showReview && (
          <button
            onClick={() => setShowReview(true)}
            className="self-start text-xs font-semibold text-primary-700 inline-flex items-center gap-1 mt-1"
          >
            <Star className="h-3 w-3" /> Calificar
          </button>
        )}
        {showReview && <ReviewForm booking={booking} onDone={() => setShowReview(false)} />}
      </div>
    </motion.div>
  );
}

export default function MisReservasPage() {
  const router = useRouter();
  const { data, isLoading } = useQuery({ queryKey: ['my-bookings'], queryFn: () => myBookings.list() });
  const bookings = data ?? [];

  return (
    <div className="flex flex-col gap-5 pb-8">
      <div className="partners-hero px-4 pt-6 pb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-white/10 text-white">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-display text-lg font-bold text-white">Mis reservas con aliados</h1>
        </div>
      </div>

      <div className="px-4 flex flex-col gap-3">
        {isLoading && <LoadingSpinner />}

        {!isLoading && bookings.length === 0 && (
          <div className="card flex flex-col items-center gap-2 py-12 text-center">
            <span className="text-4xl">📅</span>
            <p className="font-semibold text-foreground">Todavía no tienes reservas</p>
            <p className="text-xs text-muted">Agenda con un aliado desde el directorio de servicios</p>
          </div>
        )}

        {bookings.map((b, i) => <BookingRow key={b.id} booking={b} i={i} />)}
      </div>
    </div>
  );
}
