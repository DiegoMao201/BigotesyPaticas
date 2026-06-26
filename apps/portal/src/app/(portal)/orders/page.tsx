'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Plus } from 'lucide-react';
import { orders } from '@/lib/api';
import { formatCOP, formatRelativeDate } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const STATUS_LABELS: Record<string, { label: string; color: string }> = {
  received:   { label: 'Recibido',    color: 'bg-blue-50 text-blue-700' },
  processing: { label: 'En proceso',  color: 'bg-amber-50 text-amber-700' },
  ready:      { label: 'Listo 🎉',    color: 'bg-green-50 text-green-700' },
  delivered:  { label: 'Entregado',   color: 'bg-gray-100 text-gray-600' },
  cancelled:  { label: 'Cancelado',   color: 'bg-red-50 text-red-700' },
};

export default function OrdersPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['portal-orders', 1],
    queryFn: () => orders.list(1),
  });

  if (isLoading) return <LoadingSpinner />;

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-2xl font-bold text-foreground">Mis pedidos</h1>
        <Link href="/orders/new" className="btn-primary py-2 px-4 text-xs">
          <Plus className="h-4 w-4" /> Pedir
        </Link>
      </div>

      {data?.length === 0 && (
        <div className="card flex flex-col items-center gap-4 py-12 text-center">
          <div className="text-5xl">📦</div>
          <p className="font-semibold text-foreground">No tienes pedidos aún</p>
          <p className="text-muted text-sm">Haz tu primer pedido y te avisamos cuando esté listo.</p>
          <Link href="/orders/new" className="btn-primary">Hacer un pedido</Link>
        </div>
      )}

      <div className="flex flex-col gap-3">
        {data?.map((order, i) => {
          const { label, color } = STATUS_LABELS[order.status] ?? { label: order.status, color: 'bg-gray-100 text-gray-600' };
          return (
            <motion.div
              key={order.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
            >
              <Link href={`/orders/${order.id}`} className="card flex items-center gap-4 py-3">
                <div className="h-12 w-12 rounded-xl bg-primary-50 flex items-center justify-center text-2xl shrink-0">
                  📦
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-foreground text-sm truncate">{order.product_name}</p>
                  <p className="text-xs text-muted">
                    {formatRelativeDate(order.created_at)}
                    {order.unit_price ? ` • ${formatCOP(order.unit_price * order.quantity)}` : ''}
                    {order.quantity > 1 ? ` × ${order.quantity}` : ''}
                  </p>
                  {order.points_earned && (
                    <p className="text-xs text-amber-600 font-semibold">+{order.points_earned} pts</p>
                  )}
                </div>
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full shrink-0 ${color}`}>
                  {label}
                </span>
              </Link>
            </motion.div>
          );
        })}
      </div>
    </div>
  );
}
