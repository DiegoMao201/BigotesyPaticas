'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { orders } from '@/lib/api';
import { formatCOP, formatDate } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const STATUS_STEPS = ['received', 'processing', 'ready', 'delivered'] as const;

const STATUS_LABELS: Record<string, { label: string; emoji: string }> = {
  received:   { label: 'Recibido',   emoji: '📬' },
  processing: { label: 'En proceso', emoji: '⚙️' },
  ready:      { label: 'Listo',      emoji: '✅' },
  delivered:  { label: 'Entregado',  emoji: '🎉' },
  cancelled:  { label: 'Cancelado',  emoji: '❌' },
};

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: order, isLoading } = useQuery({
    queryKey: ['portal-order', id],
    queryFn: () => orders.get(id),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!order) return <p className="p-6 text-muted">Pedido no encontrado.</p>;

  const { label, emoji } = STATUS_LABELS[order.status] ?? { label: order.status, emoji: '📦' };
  const currentStep = STATUS_STEPS.indexOf(order.status as typeof STATUS_STEPS[number]);

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Detalle del pedido</h1>
      </div>

      {/* Estado actual */}
      <div className="card flex flex-col items-center gap-2 py-6 text-center">
        <div className="text-5xl">{emoji}</div>
        <p className="font-display font-bold text-foreground text-lg">{label}</p>
        {order.points_earned && (
          <p className="text-sm text-amber-600 font-semibold">+{order.points_earned} puntos ganados</p>
        )}
      </div>

      {/* Progress tracker (solo si no está cancelado) */}
      {order.status !== 'cancelled' && (
        <div className="card">
          <div className="flex items-center justify-between relative">
            <div
              className="absolute left-0 top-4 h-0.5 bg-gray-200 z-0"
              style={{ width: '100%' }}
            />
            <div
              className="absolute left-0 top-4 h-0.5 bg-primary-700 z-0 transition-all"
              style={{ width: `${Math.max(0, (currentStep / (STATUS_STEPS.length - 1)) * 100)}%` }}
            />
            {STATUS_STEPS.map((step, i) => {
              const done = i <= currentStep;
              return (
                <div key={step} className="flex flex-col items-center gap-1.5 z-10">
                  <div
                    className={`h-8 w-8 rounded-full flex items-center justify-center text-xs font-bold transition-colors ${
                      done ? 'bg-primary-700 text-white' : 'bg-gray-200 text-gray-400'
                    }`}
                  >
                    {i + 1}
                  </div>
                  <span className={`text-[10px] font-medium ${done ? 'text-primary-700' : 'text-gray-400'}`}>
                    {STATUS_LABELS[step].label}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Info del pedido */}
      <div className="card flex flex-col divide-y divide-border">
        {[
          { label: 'Producto', value: order.product_name },
          { label: 'Cantidad', value: `×${order.quantity}` },
          { label: 'Precio unitario', value: order.unit_price ? formatCOP(order.unit_price) : '—' },
          { label: 'Total', value: order.unit_price ? formatCOP(order.unit_price * order.quantity) : '—' },
          { label: 'Fecha', value: formatDate(order.created_at) },
          { label: 'Notas', value: order.notes ?? '—' },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between py-3">
            <span className="text-sm text-muted">{label}</span>
            <span className="text-sm font-medium text-foreground">{value}</span>
          </div>
        ))}
      </div>

      <p className="text-xs text-muted text-center">
        Un asesor te contactará por WhatsApp para coordinar tu pedido.
      </p>
    </div>
  );
}
