'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Package, MapPin, MessageCircle, CheckCircle2, Clock, Truck, Star } from 'lucide-react';
import Image from 'next/image';
import { orders } from '@/lib/api';
import { formatCOP } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const WORKFLOW_STEPS = [
  { key: 'received',           label: 'Recibido',      emoji: '📬' },
  { key: 'under_review',       label: 'Revisando',     emoji: '🔍' },
  { key: 'awaiting_customer',  label: 'Tu aprobación', emoji: '💬' },
  { key: 'ready_to_invoice',   label: 'Aprobado',      emoji: '✅' },
  { key: 'invoiced',           label: 'Facturado',     emoji: '🧾' },
  { key: 'in_preparation',     label: 'Preparando',    emoji: '🔧' },
  { key: 'ready_for_delivery', label: 'Listo',         emoji: '📦' },
  { key: 'in_transit',         label: 'En camino',     emoji: '🚚' },
  { key: 'delivered',          label: 'Entregado',     emoji: '🎉' },
];

const PAYMENT_LABELS: Record<string, string> = {
  cash: '💵 Efectivo contra entrega',
  card: '💳 Tarjeta al recibir',
  nequi: '📱 Nequi',
  daviplata: '📱 Daviplata',
  transfer: '🏦 Transferencia bancaria',
};

function stepIndex(ws: string): number {
  return WORKFLOW_STEPS.findIndex((s) => s.key === ws);
}

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const { data: order, isLoading } = useQuery({
    queryKey: ['portal-order-timeline', id],
    queryFn: () => orders.timeline(id),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!order) return <p className="p-6 text-center text-muted">Pedido no encontrado.</p>;

  const ws = order.workflow_status ?? order.status;
  const isCancelled = ws === 'cancelled' || order.status === 'cancelled';
  const isDelivered = ws === 'delivered' || order.status === 'delivered';
  const isAwaiting = ws === 'awaiting_customer';
  const currentStep = stepIndex(ws);

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b px-4 pt-10 pb-4 sticky top-0 z-10">
        <div className="flex items-center gap-3 mb-1">
          <button onClick={() => router.back()} className="p-2 rounded-xl bg-gray-100 text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <div>
            <h1 className="font-bold text-gray-900">Mi pedido</h1>
            <p className="text-xs text-gray-400">{new Date(order.created_at).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })}</p>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4 p-4">
        {/* Status hero */}
        {isCancelled ? (
          <div className="bg-red-50 border border-red-200 rounded-2xl p-5 text-center">
            <p className="text-4xl mb-2">❌</p>
            <p className="font-bold text-red-800 text-lg">Pedido cancelado</p>
            {order.customer_facing_notes && (
              <p className="text-sm text-red-600 mt-2">{order.customer_facing_notes}</p>
            )}
          </div>
        ) : isDelivered ? (
          <div className="bg-green-50 border border-green-200 rounded-2xl p-5 text-center">
            <p className="text-4xl mb-2">🎉</p>
            <p className="font-bold text-green-800 text-lg">¡Pedido entregado!</p>
            {order.delivered_at && (
              <p className="text-xs text-green-600 mt-1">
                {new Date(order.delivered_at).toLocaleDateString('es-CO', { day: 'numeric', month: 'long' })}
              </p>
            )}
          </div>
        ) : (
          <div className={`rounded-2xl p-5 ${isAwaiting ? 'bg-amber-50 border-2 border-amber-300' : 'bg-teal-50 border border-teal-100'}`}>
            <div className="text-center mb-4">
              <p className="text-3xl mb-1">{WORKFLOW_STEPS[currentStep]?.emoji ?? '🐾'}</p>
              <p className={`font-bold text-lg ${isAwaiting ? 'text-amber-800' : 'text-teal-800'}`}>
                {WORKFLOW_STEPS[currentStep]?.label ?? ws}
              </p>
              {isAwaiting && (
                <p className="text-sm text-amber-700 mt-1">
                  Revisamos tu pedido y puede haber cambios. Revisa abajo y confirma por WhatsApp.
                </p>
              )}
              {order.customer_facing_notes && (
                <div className="mt-2 bg-white rounded-xl p-3 text-sm text-gray-700 text-left">
                  💬 {order.customer_facing_notes}
                </div>
              )}
            </div>

            {/* Progress bar */}
            <div className="flex items-center gap-1 mt-3 overflow-x-auto pb-1">
              {WORKFLOW_STEPS.filter((s) => !['awaiting_customer'].includes(s.key)).map((step, idx, arr) => {
                const realIdx = stepIndex(step.key);
                const done = currentStep >= realIdx && !isCancelled;
                const active = currentStep === realIdx;
                return (
                  <div key={step.key} className="flex items-center gap-1 shrink-0">
                    <div className={`h-2 w-2 rounded-full transition-colors ${done ? 'bg-teal-500' : 'bg-gray-200'} ${active ? 'ring-2 ring-teal-300 ring-offset-1 scale-125' : ''}`} />
                    {idx < arr.length - 1 && (
                      <div className={`h-0.5 w-6 rounded ${done && currentStep > realIdx ? 'bg-teal-500' : 'bg-gray-200'}`} />
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* WhatsApp CTA for awaiting_customer */}
        {isAwaiting && (
          <a
            href={`https://wa.me/573111234567?text=${encodeURIComponent('Hola! Quiero confirmar mi pedido.')}`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-2 py-3.5 rounded-2xl font-bold text-white"
            style={{ backgroundColor: '#25D366' }}
          >
            <MessageCircle className="h-5 w-5" />
            Confirmar cambios por WhatsApp
          </a>
        )}

        {/* Items */}
        <div className="bg-white rounded-2xl p-4 flex flex-col gap-3">
          <p className="font-semibold text-gray-900 text-sm">📦 Productos</p>
          {order.items.map((item) => (
            <div key={item.id} className={`flex items-center gap-3 ${item.is_substituted ? 'bg-amber-50 rounded-xl p-2 -mx-1' : ''}`}>
              <div className="h-14 w-14 rounded-xl bg-gray-50 flex items-center justify-center overflow-hidden shrink-0">
                {item.image_url ? (
                  <Image
                    src={item.image_url}
                    alt={item.name ?? ''}
                    width={56}
                    height={56}
                    className="h-full w-full object-contain p-1"
                  />
                ) : (
                  <Package className="h-6 w-6 text-gray-300" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-sm text-gray-900 leading-snug">{item.name}</p>
                {item.is_substituted && (
                  <p className="text-xs text-amber-600">↔ Cambio: antes era {item.substituted_from_name}</p>
                )}
                <p className="text-xs text-gray-400">x{item.quantity} · {formatCOP(item.unit_price)} c/u</p>
              </div>
              <p className="text-sm font-bold text-gray-900 shrink-0">{formatCOP(item.subtotal)}</p>
            </div>
          ))}

          {/* Totals */}
          <div className="border-t pt-3 flex flex-col gap-1.5">
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Subtotal</span>
              <span className="text-gray-900">{formatCOP(order.subtotal)}</span>
            </div>
            {order.discount_amount > 0 && (
              <div className="flex justify-between text-sm">
                <span className="text-green-600">Descuento</span>
                <span className="text-green-600">-{formatCOP(order.discount_amount)}</span>
              </div>
            )}
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Envío</span>
              <span className="text-gray-900">{order.shipping === 0 ? 'Gratis 🎉' : formatCOP(order.shipping)}</span>
            </div>
            <div className="flex justify-between font-bold text-base border-t pt-2 mt-1">
              <span>Total</span>
              <span className="text-teal-700">{formatCOP(order.total)}</span>
            </div>
          </div>
        </div>

        {/* Delivery info */}
        <div className="bg-white rounded-2xl p-4 flex flex-col gap-2">
          <p className="font-semibold text-gray-900 text-sm mb-1">📋 Detalle</p>
          {order.shipping_address && (
            <div className="flex items-start gap-2 text-sm text-gray-700">
              <MapPin className="h-4 w-4 text-gray-400 mt-0.5 shrink-0" />
              {order.shipping_address}
            </div>
          )}
          {order.payment_method && (
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-gray-400 text-xs">💳</span>
              {PAYMENT_LABELS[order.payment_method] ?? order.payment_method}
            </div>
          )}
          {order.invoice_number && (
            <div className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-gray-400 text-xs">🧾</span>
              Factura: {order.invoice_number}
            </div>
          )}
        </div>

        {/* Timeline */}
        {order.timeline.length > 0 && (
          <div className="bg-white rounded-2xl p-4">
            <p className="font-semibold text-gray-900 text-sm mb-3">🕐 Seguimiento</p>
            <div className="relative flex flex-col gap-3">
              <div className="absolute left-3 top-3 bottom-3 w-0.5 bg-gray-100" />
              {order.timeline.map((entry, idx) => (
                <div key={idx} className="flex gap-3 relative">
                  <div className="h-6 w-6 rounded-full bg-teal-100 flex items-center justify-center shrink-0 z-10 mt-0.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-teal-600" />
                  </div>
                  <div className="flex-1 pb-1">
                    <p className="text-sm font-semibold text-gray-900">{entry.label}</p>
                    {entry.notes && <p className="text-xs text-gray-500 mt-0.5">{entry.notes}</p>}
                    <p className="text-[10px] text-gray-400 mt-0.5">
                      {new Date(entry.created_at).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Rate order (if delivered) */}
        {isDelivered && (
          <div className="bg-teal-50 border border-teal-100 rounded-2xl p-4 text-center">
            <Star className="h-8 w-8 text-amber-400 fill-amber-400 mx-auto mb-2" />
            <p className="font-semibold text-teal-800 mb-1">¿Cómo fue tu experiencia?</p>
            <p className="text-xs text-teal-600 mb-3">Tu opinión nos ayuda a mejorar 🐾</p>
            <a
              href="https://g.page/r/CfL67OgLB-10EBM/review"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block bg-teal-600 text-white rounded-xl px-5 py-2.5 text-sm font-bold"
            >
              Calificar en Google
            </a>
          </div>
        )}
      </div>
    </div>
  );
}
