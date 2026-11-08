'use client';

import Link from 'next/link';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import { motion } from 'framer-motion';
import { ChevronRight, ShoppingBag } from 'lucide-react';
import { orders, type Order } from '@/lib/api';
import { usePortalCart } from '@/lib/cart-store';
import { formatCOP, formatRelativeDate } from '@/lib/utils';

/**
 * MIS PEDIDOS (8-nov-2026). Antes: una caja naranja con emoji igual en todos los
 * pedidos. Ahora cada pedido muestra las fotos de lo que se pidió, una barra con el
 * paso en que va (como el seguimiento de las apps de domicilio) y el total. El que
 * está en curso sube arriba y se destaca.
 */
const PASOS = ['received', 'processing', 'ready', 'delivered'] as const;
const ETIQUETA: Record<string, string> = {
  received: 'Recibido',
  processing: 'Preparando',
  ready: 'Listo',
  delivered: 'Entregado',
  cancelled: 'Cancelado',
};

function Fotos({ imgs }: { imgs: string[] }) {
  if (!imgs.length) {
    return (
      <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-2xl bg-primary-50 text-primary-700">
        <ShoppingBag className="h-6 w-6" />
      </div>
    );
  }
  return (
    <div className="flex shrink-0 -space-x-3">
      {imgs.slice(0, 3).map((src, i) => (
        <div key={src} className="relative h-14 w-14 overflow-hidden rounded-2xl bg-white ring-2 ring-white shadow-sm" style={{ zIndex: 3 - i }}>
          <Image src={src} alt="" fill sizes="56px" className="object-contain p-1" />
        </div>
      ))}
    </div>
  );
}

function Progreso({ status }: { status: string }) {
  if (status === 'cancelled') return null;
  const idx = PASOS.indexOf(status as (typeof PASOS)[number]);
  return (
    <div className="mt-3 flex gap-1.5">
      {PASOS.map((p, i) => (
        <div key={p} className="h-1.5 flex-1 overflow-hidden rounded-full bg-gray-100">
          <motion.div
            className="h-full rounded-full bg-primary-600"
            initial={{ width: 0 }}
            animate={{ width: i <= idx ? '100%' : '0%' }}
            transition={{ duration: 0.5, delay: 0.1 + i * 0.12, ease: [0.22, 1, 0.36, 1] }}
          />
        </div>
      ))}
    </div>
  );
}

function Tarjeta({ o, i, destacado }: { o: Order; i: number; destacado?: boolean }) {
  const enCurso = !['delivered', 'cancelled'].includes(o.status);
  const total = o.total ?? (o.unit_price ? o.unit_price * o.quantity : null);
  const n = o.items_count ?? o.quantity;
  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.04, ease: [0.22, 1, 0.36, 1] }}>
      <Link
        href={`/orders/${o.id}`}
        className={`block rounded-[1.35rem] bg-white p-4 shadow-[0_1px_2px_rgba(16,24,40,.04),0_4px_16px_rgba(16,24,40,.06)] active:scale-[0.99] transition-transform ${
          destacado ? 'ring-2 ring-primary-600/30' : ''
        }`}
      >
        <div className="flex items-center gap-3">
          <Fotos imgs={o.images ?? []} />
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <span
                className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${
                  o.status === 'cancelled' ? 'bg-red-50 text-red-600' : enCurso ? 'bg-primary-50 text-primary-700' : 'bg-gray-100 text-gray-600'
                }`}
              >
                {ETIQUETA[o.status] ?? o.status}
              </span>
              <span className="text-[11px] text-muted">{formatRelativeDate(o.created_at)}</span>
            </div>
            <p className="mt-1 truncate text-sm font-semibold text-foreground">
              {o.product_name.startsWith('Pedido multi') ? `${n} productos` : o.product_name}
            </p>
            <p className="text-xs text-muted">
              {total ? formatCOP(total) : ''}
              {o.points_earned ? <span className="ml-2 font-semibold text-amber-600">+{o.points_earned} pts</span> : null}
            </p>
          </div>
          <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
        </div>
        {enCurso && <Progreso status={o.status} />}
      </Link>
    </motion.div>
  );
}

export default function OrdersPage() {
  // VUELVE DE PAGAR: se vacía el carrito del portal. El pago ocurre en
  // bigotesypaticas.com (otro dominio, otro almacenamiento) y vuelve con ?pagado=.
  const paramsPago = useSearchParams();
  const vaciarCarrito = usePortalCart((st) => st.clear);
  useEffect(() => {
    if (paramsPago.get('pagado')) {
      vaciarCarrito();
      toast.success('¡Pago confirmado! Tu pedido ya está en camino 🎉');
      window.history.replaceState({}, '', '/orders');
    }
  }, [paramsPago, vaciarCarrito]);

  const { data = [], isLoading } = useQuery({ queryKey: ['portal-orders', 1], queryFn: () => orders.list(1) });
  const enCurso = data.filter((o) => !['delivered', 'cancelled'].includes(o.status));
  const anteriores = data.filter((o) => ['delivered', 'cancelled'].includes(o.status));

  return (
    <div className="min-h-[100dvh] bg-[#f6f7f5] px-4 pb-32 pt-[max(1.25rem,env(safe-area-inset-top))]">
      <div className="mb-5 flex items-end justify-between pr-12">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.14em] text-primary-700">Pedidos</p>
          <h1 className="font-display text-[26px] font-extrabold leading-tight tracking-tight">Mis pedidos</h1>
        </div>
        <Link href="/orders/new" className="flex items-center gap-1.5 rounded-full bg-gray-900 px-4 py-2.5 text-sm font-bold text-white shadow-[0_6px_16px_rgba(0,0,0,.2)] active:scale-95 transition-transform">
          <ShoppingBag className="h-4 w-4" /> Tienda
        </Link>
      </div>

      {isLoading && (
        <div className="space-y-3">
          {[0, 1, 2].map((k) => <div key={k} className="h-24 animate-pulse rounded-[1.35rem] bg-white" />)}
        </div>
      )}

      {!isLoading && data.length === 0 && (
        <div className="flex flex-col items-center rounded-[1.5rem] bg-white px-6 py-12 text-center shadow-[0_4px_16px_rgba(16,24,40,.06)]">
          <span className="text-5xl">🛍️</span>
          <p className="mt-3 font-display text-lg font-bold">Aún no tienes pedidos</p>
          <p className="mt-1 text-sm text-muted">Pide hoy y te lo llevamos gratis en Pereira y Dosquebradas.</p>
          <Link href="/orders/new" className="mt-5 rounded-full bg-primary-700 px-6 py-3 text-sm font-bold text-white">Ir a la tienda</Link>
        </div>
      )}

      {enCurso.length > 0 && (
        <section className="mb-6">
          <h2 className="mb-2.5 font-display text-[15px] font-bold text-foreground">En curso</h2>
          <div className="space-y-3">{enCurso.map((o, i) => <Tarjeta key={o.id} o={o} i={i} destacado />)}</div>
        </section>
      )}

      {anteriores.length > 0 && (
        <section>
          <h2 className="mb-2.5 font-display text-[15px] font-bold text-foreground">Anteriores</h2>
          <div className="space-y-3">{anteriores.map((o, i) => <Tarjeta key={o.id} o={o} i={i + enCurso.length} />)}</div>
        </section>
      )}

    </div>
  );
}
