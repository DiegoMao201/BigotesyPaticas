'use client';

import { useEffect, useRef, useState } from 'react';
import { DeliveryLocationPicker } from '@/components/maps/DeliveryLocationPicker';
import { useUbicacionEntrega, calcularDomicilio, lineasUbicacion, GRATIS_DESDE, RADIO_MAX_KM, REGLA_TEXTO, type Domicilio, type UbicacionEntrega } from '@/lib/delivery';
import Link from 'next/link';
import Image from 'next/image';
import { useRouter } from 'next/navigation';
import { useMounted } from '@/lib/use-mounted';
import { useCart } from '@/lib/cart-store';
import { formatCurrency } from '@/lib/utils';
import { BUSINESS_INFO } from '@/lib/business-info';
import { MessageCircle, ArrowLeft, Package, ShoppingBag, CheckCircle, ShieldCheck, Truck, Home } from 'lucide-react';
import { EnvioNacional } from '@/components/envio/EnvioNacional';
import { useEnvioNacional, huellaCotizacion } from '@/lib/envio-nacional';
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
  // ENVÍO NACIONAL (16-oct-2026). Dos caminos que no se mezclan: el domicilio
  // propio en Pereira y Dosquebradas (lib/delivery) y la transportadora a otra
  // ciudad (lib/envio-nacional). El modo decide qué formulario se ve, qué vale el
  // envío y cómo se puede pagar.
  const modo = useEnvioNacional((s) => s.modo);
  const setModo = useEnvioNacional((s) => s.setModo);
  const destinoN = useEnvioNacional((s) => s.destino);
  const tarifaN = useEnvioNacional((s) => s.tarifa);
  const cotizadoPara = useEnvioNacional((s) => s.cotizadoPara);
  const nacional = modo === 'nacional';
  const tarifaVigente = nacional && tarifaN && cotizadoPara === huellaCotizacion(items, destinoN) ? tarifaN : null;
  const domLocal = calcularDomicilio(subtotal, ubicacion?.km ?? null);
  const dom: Domicilio = nacional
    ? (tarifaVigente
        ? { tipo: 'tarifa', valor: tarifaVigente.precio, texto: `${tarifaVigente.carrier_nombre} · ${tarifaVigente.dias}` }
        : { tipo: 'pendiente', valor: null, texto: 'Cotiza el envío' })
    : domLocal;
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
  const [errorPago, setErrorPago] = useState('');

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

  // ¿SE LE PUEDE COBRAR POR ADELANTADO? Misma regla que el servidor, que es quien
  // manda: aquí solo sirve para no ofrecerle al cliente algo que luego se le va a
  // negar. Cobrar sin poder entregar es el peor fallo posible — peor que no vender,
  // porque el cliente paga, espera, y hay que devolverle el dinero explicándole por
  // qué. La confianza no se recupera con un reembolso.
  const km = ubicacion?.km ?? null;
  const sinUbicacion = !nacional && km == null;
  const fueraDeZona = !nacional && km != null && km > RADIO_MAX_KM;
  const correoNacionalOk = /^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(destinoN.email.trim());
  const destinoListo = destinoN.departamento !== '' && destinoN.ciudad.trim().length >= 2 && destinoN.calle.trim().length >= 6 && correoNacionalOk;
  // Nacional: solo se paga cuando hay destino completo y una tarifa elegida. Y
  // SOLO en línea: el paquete sale de la ciudad, no hay contraentrega posible.
  const puedePagarEnLinea = nacional ? (destinoListo && !!tarifaVigente) : (!sinUbicacion && !fueraDeZona);
  const metodoEfectivo: 'bold' | 'cash' = nacional ? 'bold' : metodoPago;

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
    setErrorPago('');
    setEnviando(true);
    try {
      const r = await fetch('/api/v1/public/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...cuerpoPedido(), payment_method: 'bold' }),
      });
      const d = await r.json();
      // EL ENVÍO CAMBIÓ DE PRECIO entre que cotizó y pagó (la transportadora cobra
      // lo de hoy). No se cobra de más en silencio: se le dice y vuelve a cotizar.
      if (r.status === 409 && d?.detail?.motivo) {
        useEnvioNacional.getState().setTarifa(null, '');
        setEnviando(false);
        setErrorPago(
          d.detail.motivo === 'precio_cambio'
            ? `El valor del envío cambió a ${formatCurrency(d.detail.precio_nuevo)}. Vuelve a cotizar para verlo antes de pagar.`
            : (d.detail.mensaje ?? 'La tarifa ya no está disponible. Vuelve a cotizar el envío.'),
        );
        document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return;
      }
      if (r.status === 422 || r.status === 503) {
        const det = d?.detail;
        setEnviando(false);
        setErrorPago(typeof det === 'string' ? det : (det?.mensaje ?? 'No pudimos preparar el pago. Revisa los datos e intenta de nuevo.'));
        return;
      }
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
    } catch (e) {
      // ANTES ESTO SALTABA A WHATSAPP EN SILENCIO, y fue justo lo que confundió a
      // Diego en la primera prueba real: tocó "Pagar" y se vio en WhatsApp sin
      // entender por qué. Un fallback que no se explica no es una red de seguridad,
      // es un misterio.
      //
      // Ahora se dice lo que pasó y se deja que decida. El detalle va a la consola
      // para poder diagnosticarlo sin tener que reproducirlo.
      console.error('[pago] no se pudo preparar el cobro:', e);
      setEnviando(false);
      setErrorPago(
        'No pudimos preparar el pago en línea. Puedes intentar de nuevo o pedir contraentrega por WhatsApp.',
      );
    }
  }

  /** Los datos del pedido, iguales para los dos metodos de pago. */
  function cuerpoPedido() {
    if (nacional) {
      return {
        full_name: name.trim(),
        phone: phone.replace(/\D/g, ''),
        items: items.map((i) => ({ product_id: i.productId, quantity: i.quantity })),
        shipping_mode: 'national',
        destino: {
          departamento: destinoN.departamento,
          ciudad: destinoN.ciudad.trim(),
          calle: destinoN.calle.trim(),
          barrio: destinoN.barrio.trim() || null,
          referencia: destinoN.referencia.trim() || null,
          postal: destinoN.postal.trim() || null,
          cedula: destinoN.cedula.trim() || null,
          email: destinoN.email.trim() || null,
          recibe: destinoN.recibe.trim() || null,
          lat: destinoN.lat,
          lng: destinoN.lng,
        },
        envio: tarifaVigente
          ? { carrier: tarifaVigente.carrier, service: tarifaVigente.service, precio: tarifaVigente.precio }
          : null,
        notes: notes.trim() || null,
        ...huellaGoogle(),
      };
    }
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
    if (nacional ? !(destinoListo && tarifaVigente) : !ubicacion) {
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
    // Guarda final: si entre que eligió y confirmó cambió la ubicación, no se
    // intenta cobrar. El servidor lo rechazaría igual, pero es mejor no prometerlo.
    if (nacional) {
      // A otra ciudad no hay WhatsApp que valga: o está todo y se paga, o falta algo.
      if (!validarDatos()) return;
      void pagarEnLinea();
      return;
    }
    if (metodoPago === 'bold' && puedePagarEnLinea) void pagarEnLinea();
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
              {/* LOS PASOS CAMBIAN SEGÚN CÓMO VAYA A PAGAR. Este bloque se quedó
                  describiendo el flujo viejo —"Toca Pedir por WhatsApp"— después de
                  conectar el pago en línea, y un texto que contradice lo que hace el
                  botón de al lado no es solo descuido: Google Merchant Center revisa
                  estas páginas a mano, y una instrucción que no cuadra con el flujo
                  es motivo de rechazo. */}
              {(nacional
                ? [
                    { step: '1', text: 'Revisa tu pedido aquí abajo' },
                    { step: '2', text: 'Escribe tu dirección y cotiza el envío: eliges la transportadora y ves el valor antes de pagar' },
                    { step: '3', text: 'Paga en línea de forma segura — tarjeta, PSE, Nequi o Daviplata' },
                    { step: '4', text: 'Generamos la guía, te la enviamos por WhatsApp y puedes rastrear tu paquete' },
                  ]
                : metodoPago === 'bold' && puedePagarEnLinea
                ? [
                    { step: '1', text: 'Revisa tu pedido aquí abajo' },
                    { step: '2', text: 'Dinos dónde entregamos: tu ubicación o tu dirección en Google Maps' },
                    { step: '3', text: 'Paga en línea de forma segura — tarjeta, PSE, Nequi o Daviplata' },
                    { step: '4', text: 'Alistamos tu pedido de inmediato y te avisamos por WhatsApp cuando salga' },
                  ]
                : [
                    { step: '1', text: 'Revisa tu pedido aquí abajo' },
                    { step: '2', text: 'Dinos dónde entregamos: tu ubicación o tu dirección en Google Maps' },
                    { step: '3', text: 'Toca "Pedir por WhatsApp" — te enviaremos el resumen con el total' },
                    { step: '4', text: 'Confirmamos disponibilidad y coordinamos la entrega. Pagas al recibir' },
                  ]
              ).map((item) => (
                <div key={item.step} className="flex items-start gap-3">
                  <div className="h-6 w-6 rounded-full bg-green-600 text-white text-xs font-bold flex items-center justify-center shrink-0">
                    {item.step}
                  </div>
                  <p className="text-green-700 text-sm">{item.text}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ¿A DÓNDE VA? Domicilio propio o transportadora. Las dos opciones se
              ven completas y con su promesa real: el mismo día aquí, días hábiles
              por transportadora allá. */}
          <div className="grid gap-2 sm:grid-cols-2" role="radiogroup" aria-label="Tipo de entrega">
            <button
              type="button"
              role="radio"
              aria-checked={!nacional}
              onClick={() => { setModo('local'); setPideUbicacion(false); setErrorPago(''); }}
              className={`rounded-2xl border-2 p-4 text-left transition-colors ${!nacional ? 'border-[#187f77] bg-[#187f77]/5' : 'border-border hover:border-[#187f77]/40'}`}
            >
              <div className="flex items-start gap-3">
                <Home className={`h-5 w-5 shrink-0 mt-0.5 ${!nacional ? 'text-[#187f77]' : 'text-muted-foreground'}`} />
                <div>
                  <p className="font-semibold">Pereira o Dosquebradas</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Domicilio propio, el mismo día · gratis desde {formatCurrency(GRATIS_DESDE)}</p>
                </div>
              </div>
            </button>
            <button
              type="button"
              role="radio"
              aria-checked={nacional}
              onClick={() => { setModo('nacional'); setMetodoPago('bold'); setPideUbicacion(false); setErrorPago(''); }}
              className={`rounded-2xl border-2 p-4 text-left transition-colors ${nacional ? 'border-[#187f77] bg-[#187f77]/5' : 'border-border hover:border-[#187f77]/40'}`}
            >
              <div className="flex items-start gap-3">
                <Truck className={`h-5 w-5 shrink-0 mt-0.5 ${nacional ? 'text-[#187f77]' : 'text-muted-foreground'}`} />
                <div>
                  <p className="font-semibold">Otra ciudad de Colombia</p>
                  <p className="text-xs text-muted-foreground mt-0.5">Por transportadora · cotizas y pagas el envío aquí mismo</p>
                </div>
              </div>
            </button>
          </div>

          {/* Entrega: ubicación con Google Maps */}
          <div id="entrega" className={`bg-white border rounded-2xl p-5 flex flex-col gap-4 ${pideUbicacion && (nacional ? !(destinoListo && tarifaVigente) : !ubicacion) ? 'border-amber-400 ring-2 ring-amber-200' : 'border-border'}`}>
            <div>
              <p className="font-semibold text-gray-900">¿Dónde te lo llevamos?</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {nacional ? 'Envío por transportadora a cualquier ciudad de Colombia. El valor depende de la ciudad y del peso.' : REGLA_TEXTO}
              </p>
            </div>
            {nacional ? (
              <EnvioNacional
                items={items}
                pideDatos={pideUbicacion}
                onCambiarALocal={() => { setModo('local'); setPideUbicacion(false); }}
              />
            ) : (
              <DeliveryLocationPicker subtotal={subtotal} />
            )}
            {pideUbicacion && !nacional && !ubicacion && (
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
                <span className="text-muted-foreground">{nacional ? 'Envío por transportadora' : 'Domicilio'}</span>
                <span className={dom.tipo === 'gratis' ? 'text-green-600 font-medium' : dom.tipo === 'pendiente' ? 'text-muted-foreground text-xs' : ''}>
                  {dom.tipo === 'gratis' ? '¡Gratis! 🎉' : dom.tipo === 'tarifa' ? formatCurrency(dom.valor) : dom.texto}
                </span>
              </div>
              {nacional && tarifaVigente && (
                <p className="text-xs text-muted-foreground">{tarifaVigente.carrier_nombre} · {tarifaVigente.dias} · {destinoN.ciudad}</p>
              )}
              {!nacional && subtotal < GRATIS_DESDE && (
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
                disabled={!puedePagarEnLinea && !nacional}
                onClick={() => setMetodoPago('bold')}
                aria-pressed={metodoEfectivo === 'bold'}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  !puedePagarEnLinea && !nacional
                    ? 'cursor-not-allowed border-border bg-muted/40 opacity-70'
                    : metodoEfectivo === 'bold'
                      ? 'border-[#187f77] bg-[#187f77]/5'
                      : 'border-border hover:border-[#187f77]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">Pagar ahora en línea</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {nacional
                        ? (tarifaVigente
                            ? 'Tarjeta, PSE, Nequi o Daviplata · el envío va incluido en el total'
                            : 'Cotiza el envío arriba para ver el total a pagar')
                        : sinUbicacion
                        ? 'Dinos primero dónde entregamos para calcular el domicilio'
                        : fueraDeZona
                          ? `Tu dirección está a ${km!.toFixed(1)} km, fuera de nuestra zona de reparto`
                          : 'Tarjeta, PSE, Nequi o Daviplata · lo alistamos de inmediato'}
                    </p>
                  </div>
                  <CheckCircle
                    className={`h-5 w-5 shrink-0 ${
                      metodoEfectivo === 'bold' && (puedePagarEnLinea || nacional)
                        ? 'text-[#187f77]'
                        : 'text-transparent'
                    }`}
                  />
                </div>
              </button>

              {/* FUERA DE COBERTURA: se explica y se ofrece la salida real. No se
                  deja pagar porque no habría forma de entregar, y cobrar primero y
                  avisar después sería lo peor que podríamos hacer. */}
              {fueraDeZona && (
                <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                  <p className="font-semibold">Estás fuera de nuestra zona de domicilio propio</p>
                  <p className="mt-1 leading-relaxed">
                    Nuestro domicilio llega a la zona urbana de Pereira y Dosquebradas, y tu
                    dirección está a {km!.toFixed(1)} km del local. Pero sí te lo enviamos:
                    elige <strong>«Otra ciudad de Colombia»</strong> y cotiza el envío por
                    transportadora, con el valor a la vista antes de pagar.
                  </p>
                  <button
                    type="button"
                    onClick={() => { setModo('nacional'); setMetodoPago('bold'); document.getElementById('entrega')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); }}
                    className="mt-2 font-semibold underline"
                  >
                    Cotizar envío por transportadora
                  </button>
                </div>
              )}
              <button
                type="button"
                disabled={nacional}
                onClick={() => setMetodoPago('cash')}
                aria-pressed={metodoEfectivo === 'cash'}
                className={`w-full rounded-2xl border-2 p-4 text-left transition-colors ${
                  nacional
                    ? 'cursor-not-allowed border-border bg-muted/40 opacity-70'
                    : metodoPago === 'cash'
                      ? 'border-[#187f77] bg-[#187f77]/5'
                      : 'border-border hover:border-[#187f77]/40'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <p className="font-semibold">Pagar al recibir</p>
                    <p className="mt-0.5 text-xs text-muted-foreground">
                      {nacional
                        ? 'Solo en Pereira y Dosquebradas: los envíos por transportadora se pagan antes de despachar'
                        : 'Contraentrega · coordinamos por WhatsApp'}
                    </p>
                  </div>
                  <CheckCircle
                    className={`h-5 w-5 shrink-0 ${
                      metodoEfectivo === 'cash' ? 'text-[#187f77]' : 'text-transparent'
                    }`}
                  />
                </div>
              </button>
            </div>

            {errorPago && (
              <div className="mb-4 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
                <p>{errorPago}</p>
                {!nacional && (
                  <button
                    type="button"
                    onClick={() => { setErrorPago(''); setMetodoPago('cash'); }}
                    className="mt-2 font-semibold underline"
                  >
                    Pedir contraentrega por WhatsApp
                  </button>
                )}
              </div>
            )}

            {/* THE BIG BUTTON */}
            <button
              onClick={confirmarPedido}
              disabled={enviando}
              className="w-full flex items-center justify-center gap-3 py-4 rounded-2xl font-bold text-white text-lg shadow-lg hover:opacity-90 active:scale-95 transition-all disabled:opacity-60"
              style={{ backgroundColor: metodoEfectivo === 'bold' && (puedePagarEnLinea || nacional) ? '#187f77' : '#25D366' }}
            >
              {metodoEfectivo === 'bold' ? (
                <ShieldCheck className="h-6 w-6" />
              ) : (
                <MessageCircle className="h-6 w-6" />
              )}
              {nacional
                ? (!tarifaVigente
                    ? 'Cotiza el envío para pagar'
                    : enviando
                      ? 'Preparando tu pago…'
                      : `Pagar ${formatCurrency(total)}`)
                : !ubicacion
                ? 'Indica dónde entregamos'
                : enviando
                  ? 'Preparando tu pago…'
                  : metodoPago === 'bold' && puedePagarEnLinea
                    ? `Pagar ${formatCurrency(total)}`
                    : 'Pedir por WhatsApp'}
            </button>

            <p className="text-xs text-center text-muted-foreground mt-3">
              {metodoEfectivo === 'bold'
                ? 'Te llevamos a una página segura para pagar. El cobro lo procesa Bold.'
                : 'Te enviaremos el resumen del pedido por WhatsApp y coordinaremos la entrega contigo.'}
            </p>
          </div>

          {/* Trust signals */}
          <div className="flex flex-col gap-2">
            {[
              nacional
                ? { icon: '🚚', text: 'Envío a toda Colombia por transportadora, con guía para rastrear' }
                : { icon: '🚚', text: 'Domicilio propio en Pereira y Dosquebradas, el mismo día' },
              { icon: '⏱️', text: 'Respuesta en menos de 30 min en horario de atención' },
              // El sello decía "pago contraentrega" incluso con el pago en línea
              // elegido. Prometer una forma de pago y cobrar otra es justo lo que
              // revisa Merchant Center, y para el cliente es peor: contradice lo que
              // acaba de elegir tres dedos más arriba.
              metodoEfectivo === 'bold' && (puedePagarEnLinea || nacional)
                ? { icon: '🔒', text: 'Pago seguro en línea — procesado por Bold' }
                : { icon: '🔒', text: 'Pago contraentrega — pagas al recibir' },
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
              {dom.valor == null ? 'Total productos' : nacional ? 'Total con envío' : 'Total con domicilio'}
            </p>
            <p className="font-bold text-lg leading-tight">{formatCurrency(total)}</p>
          </div>
          <button
            onClick={confirmarPedido}
            disabled={enviando}
            className="flex-1 h-12 flex items-center justify-center gap-2 rounded-2xl font-bold text-white active:scale-[0.98] transition-all disabled:opacity-60"
            style={{ backgroundColor: metodoEfectivo === 'bold' && (puedePagarEnLinea || nacional) ? '#187f77' : '#25D366' }}
          >
            {metodoEfectivo === 'bold' ? (
              <ShieldCheck className="h-5 w-5" />
            ) : (
              <MessageCircle className="h-5 w-5" />
            )}
            {nacional
              ? (!tarifaVigente ? 'Cotiza el envío' : enviando ? 'Preparando…' : 'Pagar ahora')
              : !ubicacion
              ? 'Indica dónde entregamos'
              : enviando
                ? 'Preparando…'
                : metodoPago === 'bold' && puedePagarEnLinea
                  ? 'Pagar ahora'
                  : 'Pedir por WhatsApp'}
          </button>
        </div>
      </div>
    </div>
  );
}
