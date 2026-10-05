'use client';

import { useEffect, useRef, useState } from 'react';
import { DeliveryLocationPicker } from '@/components/maps/DeliveryLocationPicker';
import { useUbicacionEntrega, calcularDomicilio, lineasUbicacion, GRATIS_DESDE, REGLA_TEXTO, type Domicilio, type UbicacionEntrega } from '@/lib/delivery';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useMounted } from '@/lib/use-mounted';
import { useCart } from '@/lib/cart-store';
import { formatCurrency } from '@/lib/utils';
import { BUSINESS_INFO } from '@/lib/business-info';
import { MessageCircle, ArrowLeft, Package, ShoppingBag, CheckCircle, ShieldCheck } from 'lucide-react';
import { useMetaPixelEvent } from '@/hooks/useMetaPixelEvent';
import { trackBeginCheckout, huellaGoogle, recordarGclid } from '@/lib/analytics';

// El mensaje lleva la dirección que dio Google Maps y el enlace con el punto exacto,
// para que el domiciliario llegue sin preguntar (Diego, 27-sep-2026).
function buildWhatsAppMessage(
  items: { name: string; quantity: number; price: number }[],
  subtotal: number,
  dom: Domicilio,
  ubicacion: UbicacionEntrega | null,
  name: string,
  tel: string,
  notes: string,
): string {
  const header = `Hola! Quiero hacer un pedido 🐾\n`;
  const itemLines = items
    .map((i) => `• ${i.name} x${i.quantity} — ${formatCurrency(i.price * i.quantity)}`)
    .join('\n');
  const subtotalLine = `Subtotal: ${formatCurrency(subtotal)}`;
  const shippingLine =
    dom.tipo === 'gratis' ? '🎉 Domicilio GRATIS'
    : dom.tipo === 'tarifa' ? `🛵 Domicilio: ${formatCurrency(dom.valor)}`
    : '🛵 Domicilio: por confirmar según mi ubicación';
  const totalLine = dom.valor == null
    ? `*TOTAL: ${formatCurrency(subtotal)} + domicilio*`
    : `*TOTAL: ${formatCurrency(subtotal + dom.valor)}*`;
  const customerLine = name ? `\n\n👤 Nombre: ${name}` : '\n';
  const telLine = tel ? `\n📱 Celular: ${tel}` : '';
  const notesLine = notes ? `\n📝 Notas: ${notes}` : '';
  return `${header}\n${itemLines}\n\n${subtotalLine}\n${shippingLine}\n${totalLine}${customerLine}${telLine}${lineasUbicacion(ubicacion)}${notesLine}`;
}

export default function CheckoutPage() {
  const router = useRouter();
  const mounted = useMounted();
  const items = useCart((s) => s.items);
  const subtotal = useCart((s) => s.subtotal());
  const ubicacion = useUbicacionEntrega((s) => s.ubicacion);
  const dom = calcularDomicilio(subtotal, ubicacion?.km ?? null);
  const shipping = dom.valor ?? 0;
  const total = subtotal + shipping;
  const { track } = useMetaPixelEvent();   // antes se llamaba DESPUÉS de un return (regla de hooks)

  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [notes, setNotes] = useState('');
  const [pideUbicacion, setPideUbicacion] = useState(false);
  const [errorTel, setErrorTel] = useState(false);
  const [errorNombre, setErrorNombre] = useState(false);
  const yaMedido = useRef(false);
  const yaGuardado = useRef('');
  // Como quiere pagar. Arranca en 'bold' porque cobrar al momento es lo que de
  // verdad cambia el negocio: hasta hoy TODO era contraentrega y la venta no se
  // cerraba hasta que alguien contestaba el WhatsApp. Contraentrega sigue ahi,
  // completa, a un toque — pero deja de ser la unica salida.
  const [metodoPago, setMetodoPago] = useState<'bold' | 'cash'>('bold');
  const [enviando, setEnviando] = useState(false);

  // begin_checkout: el paso del embudo que faltaba. Una sola vez por visita a esta
  // página, y solo cuando el carrito ya se hidrató (antes de eso items está vacío).
  useEffect(() => {
    recordarGclid();
    if (yaMedido.current || !mounted || items.length === 0) return;
    yaMedido.current = true;
    trackBeginCheckout(
      items.map((i) => ({ id: i.productId, name: i.name, price: i.price, quantity: i.quantity })),
      subtotal + (dom.valor ?? 0),
    );
    // subtotal/dom cambian con el carrito; la bandera garantiza un solo evento
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, items.length]);

  // el carrito vive en el navegador: hasta montar no se sabe si está vacío (ver use-mounted)
  if (!mounted) return <div className="container-tight py-24 min-h-[60vh]" />;

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

  // el número de la TIENDA (al que se le escribe); el del cliente es el estado `phone`
  const telTienda = (BUSINESS_INFO.whatsapp ?? '573206876633').replace(/\D/g, '');
  const waMsg = buildWhatsAppMessage(items, subtotal, dom, ubicacion, name, phone, notes);
  const waUrl = `https://wa.me/${telTienda}?text=${encodeURIComponent(waMsg)}`;

  const celularOk = /^3\d{9}$/.test(phone.replace(/\D/g, ''));

  /**
   * Guarda el pedido en el admin sin estorbarle a la venta.
   *
   * Dos decisiones acá, y las dos son a propósito:
   *
   * 1. NO se espera la respuesta. En celular, abrir WhatsApp saca al cliente de la
   *    página, y un `await` antes de `window.open` hace que Safari bloquee la apertura
   *    por perder el gesto del usuario. `keepalive` deja que la petición termine aunque
   *    el navegador ya se fue.
   * 2. Si falla, NO se avisa ni se detiene nada. Perder una venta por un error de
   *    registro sería mucho peor que no registrarla: el pedido igual llega completo
   *    al WhatsApp de Diego, que es como ha funcionado siempre.
   */
  function guardarPedido() {
    // Candado: tocar el botón dos veces (o volver a WhatsApp y reintentar) no puede
    // crear dos pedidos en el admin. Si el carrito o los datos cambian, sí se guarda
    // de nuevo, porque entonces es un pedido distinto.
    const firma = JSON.stringify([
      items.map((i) => [i.productId, i.quantity]),
      phone.replace(/\D/g, ''),
      ubicacion?.lat ?? null,
      ubicacion?.lng ?? null,
      notes.trim(),
    ]);
    if (yaGuardado.current === firma) return;
    yaGuardado.current = firma;

    try {
      fetch('/api/v1/public/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        keepalive: true,
        body: JSON.stringify({
          full_name: name.trim(),
          phone: phone.replace(/\D/g, ''),
          items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
          direccion: ubicacion?.direccion ?? null,
          lat: ubicacion?.lat ?? null,
          lng: ubicacion?.lng ?? null,
          km: ubicacion?.km ?? null,
          notes: notes.trim() || null,
          ...huellaGoogle(),
        }),
      }).catch(() => {});
    } catch {
      // nada: el pedido sigue por WhatsApp
    }
  }

  /** Crea el pedido y lleva a la pagina de pago. */
  async function pagarEnLinea() {
    if (!validarDatos()) return;
    setEnviando(true);
    try {
      const r = await fetch('/api/v1/public/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...cuerpoPedido(), payment_method: 'bold' }),
      });
      const d = await r.json();
      const ref = d?.bold?.order_reference;
      if (!r.ok || !ref) throw new Error('sin referencia');

      track('InitiateCheckout', {
        content_ids: items.map((i) => i.productId),
        value: total,
        currency: 'COP',
        num_items: items.length,
      });
      // A la pagina de pago. El carrito NO se vacia todavia: si el cliente se
      // arrepiente a medio pagar, volver y encontrar el carrito vacio seria perder
      // la venta por un detalle. Se vacia cuando el pago se confirma.
      router.push(`/pagar/${ref}`);
    } catch {
      // Si algo falla, no se deja al cliente sin salida: se cae al flujo de
      // siempre, que es el que nunca ha dejado de funcionar.
      setEnviando(false);
      setMetodoPago('cash');
      openWhatsApp();
    }
  }

  /** Los datos del pedido, iguales para los dos metodos de pago. */
  function cuerpoPedido() {
    return {
      full_name: name.trim(),
      phone: phone.replace(/\D/g, ''),
      items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
      direccion: ubicacion?.direccion ?? null,
      lat: ubicacion?.lat ?? null,
      lng: ubicacion?.lng ?? null,
      km: ubicacion?.km ?? null,
      notes: notes.trim() || null,
      ...huellaGoogle(),
    };
  }

  /** Ubicacion, nombre y celular: sin esto el pedido no se puede entregar. */
  function validarDatos(): boolean {
    if (!ubicacion) {
      setPideUbicacion(true);
      document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return false;
    }
    const faltaNombre = name.trim().length < 2;
    if (faltaNombre || !celularOk) {
      setErrorNombre(faltaNombre);
      setErrorTel(!celularOk);
      document.getElementById(faltaNombre ? 'nombre' : 'celular')?.focus();
      document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return false;
    }
    return true;
  }

  /** El boton unico: cobra en linea o manda a WhatsApp, segun lo elegido. */
  function confirmarPedido() {
    if (metodoPago === 'bold') void pagarEnLinea();
    else void openWhatsApp();
  }

  async function openWhatsApp() {
    // sin ubicación no sale el pedido: es lo que el domiciliario necesita
    if (!ubicacion) {
      setPideUbicacion(true);
      document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }
    // Nombre y celular: el celular es por donde se confirma el pedido (Diego, 2-oct-2026)
    // y sin nombre el pedido no se puede registrar ni entregar.
    const faltaNombre = name.trim().length < 2;
    if (faltaNombre || !celularOk) {
      setErrorNombre(faltaNombre);
      setErrorTel(!celularOk);
      document.getElementById(faltaNombre ? 'nombre' : 'celular')?.focus();
      document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
      return;
    }

    guardarPedido();
    track('InitiateCheckout', {
      content_ids: items.map((i) => i.productId),
      value: total,
      currency: 'COP',
      num_items: items.length,
    });
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({ text: waMsg });
        return;
      } catch { /* fall through */ }
    }
    window.open(waUrl, '_blank', 'noopener,noreferrer');
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-gray-50 to-white pb-28 lg:pb-0">
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
                { step: '2', text: 'Dinos dónde entregamos: tu ubicación o tu dirección en Google Maps' },
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

          {/* Cobertura */}
          <div className="bg-blue-50 border border-blue-100 rounded-2xl p-4 flex gap-3 items-start">
            <span className="text-xl shrink-0">📍</span>
            <div>
              <p className="font-semibold text-blue-900 text-sm">Cobertura actual</p>
              <p className="text-blue-700 text-xs mt-0.5">
                Pereira y Dosquebradas zona urbana, entrega el mismo día.
              </p>
              <p className="text-blue-600 text-xs mt-1">
                ¿Estás fuera de esta zona?{' '}
                <a
                  href="https://wa.me/573206876633?text=Hola!%20Quiero%20consultar%20cobertura%20de%20domicilio%20a%20mi%20zona."
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline font-medium"
                >
                  Escríbenos por WhatsApp
                </a>{' '}
                y coordinamos un envío especial.
              </p>
            </div>
          </div>

          {/* Entrega: ubicación con Google Maps */}
          <div id="entrega" className={`bg-white border rounded-2xl p-5 flex flex-col gap-4 ${pideUbicacion && !ubicacion ? 'border-amber-400 ring-2 ring-amber-200' : 'border-border'}`}>
            <div>
              <p className="font-semibold text-gray-900">¿Dónde te lo llevamos?</p>
              <p className="text-xs text-muted-foreground mt-0.5">{REGLA_TEXTO}</p>
            </div>
            <DeliveryLocationPicker subtotal={subtotal} />
            {pideUbicacion && !ubicacion && (
              <p className="text-sm font-medium text-amber-700">Indícanos dónde entregar para enviar el pedido.</p>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="nombre" className="text-xs font-medium text-muted-foreground block mb-1">
                  Tu nombre
                </label>
                <input
                  id="nombre"
                  type="text"
                  value={name}
                  onChange={(e) => { setName(e.target.value); setErrorNombre(false); }}
                  placeholder="¿Cómo te llamamos?"
                  autoComplete="name"
                  className={`w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 ${
                    errorNombre ? 'border-amber-400 ring-2 ring-amber-200' : 'border-border focus:ring-brand/50'
                  }`}
                />
                {errorNombre && (
                  <p className="text-xs font-medium text-amber-700 mt-1">Escribe tu nombre, por favor.</p>
                )}
              </div>
              {/* El celular es obligatorio: por ahí se confirma el pedido y la entrega. */}
              <div>
                <label htmlFor="celular" className="text-xs font-medium text-muted-foreground block mb-1">
                  Tu celular (WhatsApp)
                </label>
                <input
                  id="celular"
                  type="tel"
                  inputMode="numeric"
                  value={phone}
                  onChange={(e) => { setPhone(e.target.value); setErrorTel(false); }}
                  placeholder="320 687 6633"
                  autoComplete="tel"
                  maxLength={17}
                  className={`w-full rounded-xl border px-4 py-2.5 text-sm focus:outline-none focus:ring-2 ${
                    errorTel ? 'border-amber-400 ring-2 ring-amber-200' : 'border-border focus:ring-brand/50'
                  }`}
                />
                {errorTel ? (
                  <p className="text-xs font-medium text-amber-700 mt-1">
                    Escribe un celular de 10 dígitos, por ejemplo 320 687 6633.
                  </p>
                ) : (
                  <p className="text-[11px] text-muted-foreground mt-1">Para confirmarte el pedido y la entrega.</p>
                )}
              </div>
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
                  <div className="relative h-12 w-12 rounded-xl bg-gray-50 flex items-center justify-center overflow-hidden shrink-0">
                    {item.image
                      ? <Image src={item.image} alt={item.name} fill sizes="48px" className="object-contain p-1" />
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
                <span className="text-muted-foreground">Domicilio</span>
                <span className={dom.tipo === 'gratis' ? 'text-green-600 font-medium' : dom.tipo === 'pendiente' ? 'text-muted-foreground text-xs' : ''}>
                  {dom.tipo === 'gratis' ? '¡Gratis! 🎉' : dom.tipo === 'tarifa' ? formatCurrency(dom.valor) : dom.texto}
                </span>
              </div>
              {subtotal < GRATIS_DESDE && (
                <p className="text-xs text-muted-foreground">
                  Agrega {formatCurrency(GRATIS_DESDE - subtotal)} más y el domicilio es gratis
                </p>
              )}
            </div>
            <div className="border-t border-border pt-4 flex justify-between font-bold text-lg mb-5">
              <span>Total{dom.valor == null ? ' productos' : ''}</span>
              <span className="text-gradient">{formatCurrency(total)}</span>
            </div>

            {/* COMO PAGA. Las dos opciones se ven completas: esconder la
                contraentrega detras de un desplegable la haria parecer un castigo,
                y es la forma en que esta tienda ha vendido siempre. */}
            <div className="mb-5 space-y-2">
              <p className="text-sm font-semibold">¿Cómo quieres pagar?</p>
              <button
                type="button"
                onClick={() => setMetodoPago('bold')}
                aria-pressed={metodoPago === 'bold'}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  metodoPago === 'bold'
                    ? 'border-[#187f77] bg-[#187f77]/5'
                    : 'border-border hover:border-[#187f77]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">Pagar ahora en línea</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Tarjeta, PSE, Nequi o Daviplata · lo alistamos de inmediato
                    </p>
                  </div>
                  <CheckCircle
                    className={`h-5 w-5 shrink-0 ${
                      metodoPago === 'bold' ? 'text-[#187f77]' : 'text-transparent'
                    }`}
                  />
                </div>
              </button>
              <button
                type="button"
                onClick={() => setMetodoPago('cash')}
                aria-pressed={metodoPago === 'cash'}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  metodoPago === 'cash'
                    ? 'border-[#187f77] bg-[#187f77]/5'
                    : 'border-border hover:border-[#187f77]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">Pagar al recibir</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      Contraentrega · coordinamos por WhatsApp
                    </p>
                  </div>
                  <CheckCircle
                    className={`h-5 w-5 shrink-0 ${
                      metodoPago === 'cash' ? 'text-[#187f77]' : 'text-transparent'
                    }`}
                  />
                </div>
              </button>
            </div>

            {/* THE BIG BUTTON */}
            <button
              onClick={confirmarPedido}
              disabled={enviando}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl font-bold text-white text-lg shadow-lg hover:opacity-90 active:scale-95 transition-all disabled:opacity-60"
              style={{ backgroundColor: metodoPago === 'bold' ? '#187f77' : '#25D366' }}
            >
              {metodoPago === 'bold' ? (
                <ShieldCheck className="h-6 w-6" />
              ) : (
                <MessageCircle className="h-6 w-6" />
              )}
              {!ubicacion
                ? 'Indica dónde entregamos'
                : enviando
                  ? 'Preparando tu pago…'
                  : metodoPago === 'bold'
                    ? `Pagar ${formatCurrency(total)}`
                    : 'Pedir por WhatsApp'}
            </button>

            <p className="text-xs text-center text-muted-foreground mt-3">
              {metodoPago === 'bold'
                ? 'Te llevamos a una página segura para pagar. El cobro lo procesa Bold.'
                : 'Te enviaremos el resumen del pedido por WhatsApp y coordinaremos la entrega contigo.'}
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

      {/* Celular: total y botón siempre a la vista (antes quedaban al final de la página) */}
      <div className="lg:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 backdrop-blur border-t border-border px-4 pt-3 pb-[max(0.75rem,env(safe-area-inset-bottom))]">
        <div className="flex items-center gap-3">
          <div className="min-w-0">
            <p className="text-[11px] text-muted-foreground leading-none">
              {dom.valor == null ? 'Total productos' : 'Total con domicilio'}
            </p>
            <p className="font-bold text-lg leading-tight">{formatCurrency(total)}</p>
          </div>
          <button
            onClick={confirmarPedido}
            disabled={enviando}
            className="flex-1 h-12 flex items-center justify-center gap-2 rounded-2xl font-bold text-white active:scale-[0.98] transition-all disabled:opacity-60"
            style={{ backgroundColor: metodoPago === 'bold' ? '#187f77' : '#25D366' }}
          >
            {metodoPago === 'bold' ? (
              <ShieldCheck className="h-5 w-5" />
            ) : (
              <MessageCircle className="h-5 w-5" />
            )}
            {!ubicacion
              ? 'Indica dónde entregamos'
              : enviando
                ? 'Preparando…'
                : metodoPago === 'bold'
                  ? 'Pagar ahora'
                  : 'Pedir por WhatsApp'}
          </button>
        </div>
      </div>
    </div>
  );
}
