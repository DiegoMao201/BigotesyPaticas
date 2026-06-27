'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useCart } from '@/lib/cart-store';
import { formatCurrency } from '@/lib/utils';
import { BUSINESS_INFO } from '@/lib/business-info';
import { MessageCircle, ArrowLeft, Package, ShoppingBag, CheckCircle } from 'lucide-react';

const FREE_SHIPPING_THRESHOLD = 30_000;
const SHIPPING_COST = 8_000;

function buildWhatsAppMessage(
  items: { name: string; quantity: number; price: number }[],
  subtotal: number,
  shipping: number,
  total: number,
  name: string,
  address: string,
  notes: string,
): string {
  const header = `Hola! Quiero hacer un pedido 🐾\n`;
  const itemLines = items
    .map((i) => `• ${i.name} x${i.quantity} — ${formatCurrency(i.price * i.quantity)}`)
    .join('\n');
  const shippingLine = shipping === 0 ? '🎉 Envío gratis' : `Envío: ${formatCurrency(shipping)}`;
  const totalLine = `*TOTAL: ${formatCurrency(total)}*`;
  const customerLine = name ? `\n\n👤 Nombre: ${name}` : '';
  const addressLine = address ? `\n📍 Dirección: ${address}` : '';
  const notesLine = notes ? `\n📝 Notas: ${notes}` : '';
  return `${header}\n${itemLines}\n\n${shippingLine}\n${totalLine}${customerLine}${addressLine}${notesLine}`;
}

export default function CheckoutPage() {
  const router = useRouter();
  const items = useCart((s) => s.items);
  const subtotal = useCart((s) => s.subtotal());
  const shipping = subtotal >= FREE_SHIPPING_THRESHOLD ? 0 : SHIPPING_COST;
  const total = subtotal + shipping;

  const [name, setName] = useState('');
  const [address, setAddress] = useState('');
  const [notes, setNotes] = useState('');

  if (items.length === 0) {
    return (
      <div className="container-tight py-16 text-center">
        <ShoppingBag className="h-16 w-16 mx-auto text-muted-foreground/30 mb-4" />
        <h1 className="text-2xl font-display font-bold mb-2">Tu carrito está vacío</h1>
        <p className="text-muted-foreground mb-6">Agrega productos antes de continuar.</p>
        <Link href="/" className="inline-flex items-center gap-2 bg-brand text-white px-6 py-3 rounded-xl font-semibold hover:bg-brand/90 transition-colors">
          <Package className="h-4 w-4" /> Ver productos
        </Link>
      </div>
    );
  }

  const phone = (BUSINESS_INFO.whatsapp ?? '573206876633').replace(/\D/g, '');
  const waMsg = buildWhatsAppMessage(items, subtotal, shipping, total, name, address, notes);
  const waUrl = `https://wa.me/${phone}?text=${encodeURIComponent(waMsg)}`;

  async function openWhatsApp() {
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({ text: waMsg });
        return;
      } catch { /* fall through */ }
    }
    window.open(waUrl, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="container-tight py-4 flex items-center gap-3">
          <Link href="/carrito" className="p-2 rounded-xl hover:bg-gray-100 transition-colors text-gray-600">
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <h1 className="font-display font-bold text-xl">Finalizar pedido</h1>
        </div>
      </div>

      <div className="container-tight py-8 grid gap-6 lg:grid-cols-[1fr_380px]">
        {/* Left: form */}
        <div className="flex flex-col gap-5">
          {/* How it works */}
          <div className="bg-green-50 border border-green-200 rounded-2xl p-5">
            <p className="font-semibold text-green-800 mb-3 flex items-center gap-2">
              <MessageCircle className="h-5 w-5" />
              ¿Cómo funciona el pedido?
            </p>
            <div className="flex flex-col gap-2">
              {[
                { step: '1', text: 'Revisa tu pedido aquí abajo' },
                { step: '2', text: 'Opcionalmente escribe tu nombre y dirección' },
                { step: '3', text: 'Toca "Pedir por WhatsApp" — te enviaremos el resumen con el total' },
                { step: '4', text: 'Confirmamos disponibilidad y coordinamos la entrega' },
              ].map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                    {item.step}
                  </div>
                  <p className="text-green-700 text-sm">{item.text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* Optional form */}
          <div className="bg-white border border-border rounded-2xl p-5 flex flex-col gap-4">
            <p className="font-semibold text-gray-900">Datos de entrega (opcional)</p>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Tu nombre</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="¿Cómo te llamamos?"
                className="w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">Dirección de entrega</label>
              <input
                type="text"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                placeholder="Barrio, calle, número..."
                className="w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50"
              />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground block mb-1">¿Alguna nota? (sabor, talla, etc.)</label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Ej: Preferible en presentación de 3 kg..."
                rows={2}
                className="w-full rounded-xl border border-border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand/50 resize-none"
              />
            </div>
          </div>

          {/* Items list */}
          <div className="bg-white border border-border rounded-2xl p-5">
            <p className="font-semibold text-gray-900 mb-3">Tu pedido</p>
            <div className="flex flex-col gap-3">
              {items.map((item) => (
                <div key={item.productId} className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-xl bg-gray-50 flex items-center justify-center overflow-hidden shrink-0">
                    {item.image
                      // eslint-disable-next-line @next/next/no-img-element
                      ? <img src={item.image} alt={item.name} className="h-full w-full object-contain p-1" />
                      : <Package className="h-5 w-5 text-gray-300" />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 leading-snug line-clamp-1">{item.name}</p>
                    <p className="text-xs text-muted-foreground">x{item.quantity} · {formatCurrency(item.price)} c/u</p>
                  </div>
                  <p className="text-sm font-bold text-gray-900 shrink-0">{formatCurrency(item.price * item.quantity)}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: summary + CTA */}
        <div className="flex flex-col gap-4 lg:sticky lg:top-24 h-fit">
          <div className="bg-white border border-border rounded-2xl p-5">
            <h2 className="font-display font-semibold text-lg mb-4">Resumen</h2>
            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Subtotal ({items.length} item{items.length !== 1 ? 's' : ''})</span>
                <span>{formatCurrency(subtotal)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Envío</span>
                <span className={shipping === 0 ? 'text-green-600 font-medium' : ''}>
                  {shipping === 0 ? '¡Gratis! 🎉' : formatCurrency(shipping)}
                </span>
              </div>
              {shipping > 0 && (
                <p className="text-xs text-muted-foreground">
                  Agrega {formatCurrency(FREE_SHIPPING_THRESHOLD - subtotal)} más para envío gratis
                </p>
              )}
            </div>
            <div className="border-t border-border pt-4 flex justify-between font-bold text-lg mb-5">
              <span>Total</span>
              <span className="text-gradient">{formatCurrency(total)}</span>
            </div>

            {/* THE BIG BUTTON */}
            <button
              onClick={openWhatsApp}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl font-bold text-white text-lg shadow-lg hover:opacity-90 active:scale-95 transition-all"
              style={{ backgroundColor: '#25D366' }}
            >
              <MessageCircle className="h-6 w-6" />
              Pedir por WhatsApp
            </button>

            <p className="text-xs text-center text-muted-foreground mt-3">
              Te enviaremos el resumen del pedido por WhatsApp y coordinaremos la entrega contigo.
            </p>
          </div>

          {/* Trust signals */}
          <div className="flex flex-col gap-2">
            {[
              { icon: '🚚', text: 'Entrega en Pereira y Dosquebradas' },
              { icon: '⏱️', text: 'Respuesta en menos de 30 min en horario de atención' },
              { icon: '🔒', text: 'Pago contraentrega — pagas al recibir' },
            ].map((item) => (
              <div key={item.text} className="flex items-center gap-2 text-sm text-muted-foreground">
                <span>{item.icon}</span>
                {item.text}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
