'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';
import { auth, orders } from '@/lib/api';
import { formatCOP } from '@/lib/utils';

const PAYMENT_METHODS = [
  { value: 'cash', label: '💵 Efectivo contra entrega' },
  { value: 'card', label: '💳 Tarjeta al recibir' },
  { value: 'nequi', label: '📱 Nequi' },
  { value: 'daviplata', label: '📱 Daviplata' },
  { value: 'transfer', label: '🏦 Transferencia bancaria' },
];

function isOutOfHours() {
  const now = new Date();
  const day = now.getDay(); // 0=dom, 6=sab
  const hour = now.getHours();
  if (day === 0) return true; // domingo
  return hour < 10 || hour >= 19;
}

function nextBusinessDay() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  while (d.getDay() === 0) d.setDate(d.getDate() + 1);
  return d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
}

export default function PedidoPage() {
  const router = useRouter();
  const items = usePortalCart((s) => s.items);
  const subtotal = usePortalCart((s) => s.subtotal());
  const pointsToEarn = usePortalCart((s) => s.pointsToEarn());
  const isFreeShipping = usePortalCart((s) => s.isFreeShipping());
  const clearCart = usePortalCart((s) => s.clear);

  const { data: me } = useQuery({ queryKey: ['portal-me'], queryFn: auth.me });
  const [shippingAddress, setShippingAddress] = useState('');
  const [paymentMethod, setPaymentMethod] = useState('cash');
  const [generalNotes, setGeneralNotes] = useState('');

  const shipping = isFreeShipping ? 0 : 8000;
  const total = subtotal + shipping;

  const mutation = useMutation({
    mutationFn: (payload: Parameters<typeof orders.createMulti>[0]) =>
      orders.createMulti(payload),
    onSuccess: (order) => {
      clearCart();
      toast.success('¡Pedido confirmado! 🎉');
      router.push(`/orders/${order.id}`);
    },
    onError: (err: Error) => {
      toast.error(err.message ?? 'Error al crear el pedido');
    },
  });

  if (items.length === 0) {
    router.replace('/orders/new');
    return null;
  }

  const canSubmit = shippingAddress.trim().length > 5 && paymentMethod && !mutation.isPending;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({
      items: items.map((i) => ({
        product_id: i.product_id,
        quantity: i.quantity,
        notes: i.notes,
      })),
      shipping_address: shippingAddress,
      payment_method: paymentMethod,
      general_notes: generalNotes || undefined,
    });
  }

  return (
    <div className="flex flex-col min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-teal-600 pt-10 pb-6 px-4">
        <div className="flex items-center gap-3 mb-2">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-xl bg-white/20 text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-bold text-xl text-white">Confirmar tu pedido</h1>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-4 flex flex-col gap-5 pb-10">
        {/* Fuera de horario */}
        {isOutOfHours() && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 text-sm text-amber-800">
            📦 Estamos cerrados ahora. Tu pedido será procesado el{' '}
            <strong>{nextBusinessDay()}</strong> cuando abramos (10am-7pm L-S). Si necesitas
            algo urgente, escríbenos por WhatsApp.
          </div>
        )}

        {/* Sección 1: Items del carrito */}
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <h2 className="font-bold text-base mb-3">Tu pedido ({items.length} producto{items.length !== 1 ? 's' : ''})</h2>
          <div className="space-y-3">
            {items.map((item) => (
              <div key={item.product_id} className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-xl bg-gray-100 overflow-hidden shrink-0">
                  {item.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-xl">🐾</div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium line-clamp-1">{item.name}</p>
                  <p className="text-xs text-gray-500">{item.quantity} × {formatCOP(item.unit_price)}</p>
                </div>
                <p className="text-sm font-bold">{formatCOP(item.unit_price * item.quantity)}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Sección 2: Dirección de entrega */}
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <h2 className="font-bold text-base mb-3">📍 Dirección de entrega</h2>
          {me?.address && (
            <button
              type="button"
              onClick={() => setShippingAddress(me.address ?? '')}
              className="w-full text-left text-sm bg-teal-50 border border-teal-200 rounded-xl p-3 mb-3 hover:bg-teal-100 transition"
            >
              <span className="font-semibold text-teal-700">Usar mi dirección guardada:</span>
              <br />
              <span className="text-gray-600">{me.address}</span>
            </button>
          )}
          <textarea
            required
            value={shippingAddress}
            onChange={(e) => setShippingAddress(e.target.value)}
            placeholder="Ej: Cra 10 # 20-30, Apto 301, Dosquebradas, Risaralda"
            rows={3}
            className="w-full rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        {/* Sección 3: Método de pago */}
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <h2 className="font-bold text-base mb-3">💳 Método de pago</h2>
          <div className="space-y-2">
            {PAYMENT_METHODS.map((pm) => (
              <label
                key={pm.value}
                className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition ${paymentMethod === pm.value ? 'border-teal-500 bg-teal-50' : 'border-gray-200 hover:bg-gray-50'}`}
              >
                <input
                  type="radio"
                  name="payment"
                  value={pm.value}
                  checked={paymentMethod === pm.value}
                  onChange={() => setPaymentMethod(pm.value)}
                  className="accent-teal-600"
                />
                <span className="text-sm font-medium">{pm.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Sección 4: Notas generales */}
        <div className="bg-white rounded-2xl shadow-sm p-4">
          <h2 className="font-bold text-base mb-3">📝 Notas del pedido (opcional)</h2>
          <textarea
            value={generalNotes}
            onChange={(e) => setGeneralNotes(e.target.value)}
            placeholder="Ej: Tocar el timbre, dejar con el portero, etc."
            rows={2}
            className="w-full rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
          />
        </div>

        {/* Sección 5: Resumen final */}
        <div className="bg-white rounded-2xl shadow-sm p-4 space-y-2">
          <h2 className="font-bold text-base mb-3">💰 Resumen</h2>
          <div className="flex justify-between text-sm text-gray-600">
            <span>Subtotal</span>
            <span>{formatCOP(subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm text-gray-600">
            <span>Envío</span>
            <span>{shipping === 0 ? '¡Gratis! 🎉' : formatCOP(shipping)}</span>
          </div>
          <div className="flex justify-between font-bold text-lg border-t pt-2 mt-2">
            <span>Total</span>
            <span className="text-teal-700">{formatCOP(total)}</span>
          </div>
          <p className="text-xs text-teal-600 text-center pt-1">
            🌟 Ganarás <strong>{pointsToEarn} Puntos Bigotes</strong> con este pedido
          </p>
        </div>

        {/* Botón submit */}
        <button
          type="submit"
          disabled={!canSubmit}
          className="w-full py-4 bg-teal-600 hover:bg-teal-700 disabled:opacity-50 text-white font-bold rounded-2xl transition flex items-center justify-center gap-2"
        >
          {mutation.isPending ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Confirmando pedido...
            </>
          ) : (
            'Confirmar pedido ✓'
          )}
        </button>
      </form>
    </div>
  );
}
