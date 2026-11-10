'use client';

import { openWhatsApp as openWhatsAppLink } from '@/lib/whatsapp';
import { useState } from 'react';
import { X, Copy, MessageCircle, CheckCircle } from 'lucide-react';

interface Scenario {
  id: string;
  label: string;
  emoji: string;
  description: string;
  message: string;
}

// Datos de pago dictados por Diego (10-nov-2026). Cambiar solo con su confirmación.
const PAGOS = [
  { id: 'llave', icono: '🔑', titulo: 'Llave Bre-B', valor: '@bigotesypaticas', nota: 'Desde cualquier banco o billetera' },
  { id: 'bancolombia', icono: '🏦', titulo: 'Bancolombia · Ahorros', valor: '852511671', nota: 'Transferencia' },
  { id: 'nequi', icono: '📱', titulo: 'Nequi', valor: '3206876633', nota: 'Transferencia' },
  { id: 'link', icono: '💳', titulo: 'Link de pago', valor: 'https://bigotesypaticas.com/pagar', nota: 'Tarjeta, PSE, Nequi o Daviplata' },
];

// Mismos enlaces que el correo de gracias (correo_satisfaccion.py): la ficha de Google y,
// para los productos, Mis pedidos del portal, que alimenta el feed de reseñas de Merchant.
const CALIFICAR = [
  { id: 'google', icono: '⭐', titulo: 'Ficha de Google', valor: 'https://g.page/r/CfL67OgLB-10EBM/review', nota: 'Calificar la tienda' },
  { id: 'productos', icono: '🛍️', titulo: 'Productos comprados', valor: 'https://mi.bigotesypaticas.com/orders', nota: 'Mis pedidos en el portal · suma puntos' },
];

/** Tarjetas para copiar un dato suelto, según el mensaje elegido. */
const DATOS: Record<string, typeof PAGOS> = { medios_pago: PAGOS, calificar: CALIFICAR };

const SCENARIOS: Scenario[] = [
  {
    id: 'medios_pago',
    label: 'Medios de pago',
    emoji: '💳',
    description: 'Llave, cuentas y link de pago',
    message:
      '¡Hola! 🐾 Estos son los *medios de pago* de *Bigotes y Paticas*:\n\n' +
      '🔑 *Llave Bre-B:* @bigotesypaticas\n\n' +
      '🏦 *Bancolombia* · Cuenta de ahorros\n' +
      '  852511671\n\n' +
      '📱 *Nequi:* 320 687 6633\n\n' +
      '💳 *Link de pago* (tarjeta, PSE, Nequi o Daviplata):\n' +
      '  https://bigotesypaticas.com/pagar\n\n' +
      '✅ Cuando pagues, envíanos el comprobante por aquí y te confirmamos. ¡Gracias! 💛',
  },
  {
    id: 'calificar',
    label: 'Pedir calificación',
    emoji: '⭐',
    description: 'Reseña en Google y de los productos',
    message:
      '¡Hola! 🐾 Gracias de corazón por confiar en *Bigotes y Paticas* 💛\n\n' +
      'Si te gustó la atención, ¿nos regalas un minuto para calificarnos? ' +
      'Tu opinión nos ayuda a seguir mejorando y a que más familias con mascotas encuentren una tienda especializada que las atienda como se merecen.\n\n' +
      '⭐ *En Google:*\n' +
      'https://g.page/r/CfL67OgLB-10EBM/review\n\n' +
      '🛍️ *Tus productos* (en Mis pedidos, y ganas Puntos Bigotes):\n' +
      'https://mi.bigotesypaticas.com/orders\n\n' +
      '¡Mil gracias! Un abrazo para tu peludito 🐶🐱',
  },
  {
    id: 'info_general',
    label: 'Info de la tienda',
    emoji: '🏠',
    description: 'Cuando preguntan qué es Bigotes y Paticas',
    message:
      '¡Hola! 🐾 Somos *Bigotes y Paticas*, tu pet shop de confianza en Dosquebradas y Pereira.\n\n' +
      '🛒 *Tienda online:* https://bigotesypaticas.com\n' +
      '  +500 productos: concentrados, accesorios, medicamentos y más\n' +
      '  Envío gratis en pedidos desde $30.000\n\n' +
      '📱 *Portal de clientes:* https://mi.bigotesypaticas.com\n' +
      '  Pedí domicilio, acumulá Puntos Bigotes y llevá el carnet de tu mascota\n\n' +
      '📍 *Tienda física:* Samara Plaza Mall, Local 2 · Dosquebradas\n' +
      '🕐 Lun–Sáb 10am–7pm\n\n' +
      '📸 Instagram: @bigotesypaticas\n' +
      '💬 WhatsApp: 320 687 6633',
  },
  {
    id: 'portal_invite',
    label: 'Invitar al portal',
    emoji: '📱',
    description: 'Para que descarguen el portal como app',
    message:
      '¡Hola! 🐾 ¿Ya conocés el *portal de clientes* de Bigotes y Paticas?\n\n' +
      '👉 https://mi.bigotesypaticas.com\n\n' +
      '¿Qué podés hacer?\n' +
      '✓ Pedir domicilio sin llamar\n' +
      '✓ Ver el historial de productos y salud de tu mascota\n' +
      '✓ Ganar *Puntos Bigotes* con cada compra y canjearlos por descuentos\n' +
      '✓ Calificar tus compras y ganar puntos extra\n\n' +
      '🆓 Es gratis y tardás 30 segundos en registrarte.\n' +
      'Desde el celular, abrís el link y podés instalarlo como app.\n\n' +
      '📸 @bigotesypaticas · 🛒 bigotesypaticas.com',
  },
  {
    id: 'como_pedir',
    label: 'Cómo hacer un pedido',
    emoji: '🛒',
    description: 'Instrucciones para pedir por primera vez',
    message:
      '¡Hola! Te explico cómo pedir en *Bigotes y Paticas* 🐾\n\n' +
      '*Opción 1 — Por la tienda online:*\n' +
      '1. Entrá a https://bigotesypaticas.com\n' +
      '2. Buscá el producto y agregalo al carrito\n' +
      '3. Nos escribís por WhatsApp con tu pedido y dirección\n\n' +
      '*Opción 2 — Por el portal (recomendado):*\n' +
      '1. Registrate gratis en https://mi.bigotesypaticas.com\n' +
      '2. Pedís desde el portal y acumulás Puntos Bigotes\n\n' +
      '🚚 *Envío:* el mismo día en Pereira y Dosquebradas\n' +
      '💰 *Envío gratis* en pedidos desde $30.000\n' +
      '💵 Pago contra entrega (efectivo, tarjeta, Nequi, Daviplata)\n\n' +
      '📍 Samara Plaza Mall, Local 2 · 320 687 6633',
  },
  {
    id: 'ubicacion',
    label: 'Ubicación y horarios',
    emoji: '📍',
    description: 'Dirección, cómo llegar y horario de atención',
    message:
      '¡Hola! Nuestra *tienda física* está en 🐾\n\n' +
      '📍 *Samara Plaza Mall, Local 2*\n' +
      '  Cl. 15 #3A-07 · Dosquebradas, Risaralda\n\n' +
      '🕐 *Horario:* Lunes a Sábado, 10am a 7pm\n\n' +
      '🗺️ Ver en Google Maps:\n' +
      'https://www.google.com/maps/search/?api=1&query=Bigotes+y+Paticas+Samara+Plaza+Mall+Dosquebradas\n\n' +
      '🚚 También hacemos *domicilio el mismo día* a Pereira y Dosquebradas.\n' +
      'Pedí por el portal: https://mi.bigotesypaticas.com\n\n' +
      '💬 320 687 6633 · 📸 @bigotesypaticas',
  },
  {
    id: 'catalogo',
    label: 'Enviar catálogo',
    emoji: '📦',
    description: 'Comparte el link del catálogo con categorías',
    message:
      '¡Hola! 🐾 Te comparto el *catálogo completo* de Bigotes y Paticas:\n\n' +
      '🐶 Perros: https://bigotesypaticas.com/categorias/perros\n' +
      '🐱 Gatos: https://bigotesypaticas.com/categorias/gatos\n' +
      '🎀 Accesorios: https://bigotesypaticas.com/categorias/accesorios\n' +
      '🍖 Snacks: https://bigotesypaticas.com/categorias/snacks\n\n' +
      '🔍 Buscar todos los productos: https://bigotesypaticas.com/categorias/todos\n\n' +
      '🚚 Envío gratis desde $30.000 · Entrega el mismo día\n' +
      '📱 Portal de puntos: https://mi.bigotesypaticas.com · 📸 @bigotesypaticas',
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ShareStoreModal({ open, onClose }: Props) {
  const [selected, setSelected] = useState<string>('medios_pago');
  const [copied, setCopied] = useState(false);
  const [copiadoDato, setCopiadoDato] = useState<string | null>(null);

  if (!open) return null;

  const scenario = SCENARIOS.find((s) => s.id === selected)!;

  function copyMessage() {
    navigator.clipboard.writeText(scenario.message)
      .then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      })
      .catch(() => {});
  }

  function copiarDato(id: string, valor: string) {
    navigator.clipboard.writeText(valor)
      .then(() => {
        setCopiadoDato(id);
        setTimeout(() => setCopiadoDato(null), 1500);
      })
      .catch(() => {});
  }

  function openWhatsApp() {
    // Una sola pestaña de WhatsApp (o la app): ver lib/whatsapp.ts
    openWhatsAppLink(null, scenario.message);
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl w-[95%] max-w-2xl z-50 flex flex-col max-h-[90vh] overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b bg-[#0d4a45]">
          <div>
            <h2 className="font-bold text-white text-base flex items-center gap-2">
              🐾 Compartir Bigotes y Paticas
            </h2>
            <p className="text-teal-200 text-xs mt-0.5">Mensajes listos para enviar por WhatsApp</p>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-full hover:bg-white/20 text-white">
            <X size={18} />
          </button>
        </div>

        <div className="flex flex-col sm:flex-row flex-1 overflow-hidden min-h-0">
          {/* Scenario picker */}
          <div className="sm:w-52 shrink-0 border-b sm:border-b-0 sm:border-r bg-gray-50 p-3 flex sm:flex-col gap-1.5 overflow-x-auto sm:overflow-y-auto">
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                onClick={() => setSelected(s.id)}
                className={`shrink-0 text-left rounded-xl px-3 py-2.5 text-sm transition-all ${
                  selected === s.id
                    ? 'bg-[#187f77] text-white shadow-sm'
                    : 'text-gray-700 hover:bg-gray-200'
                }`}
              >
                <div className="font-semibold flex items-center gap-1.5 whitespace-nowrap">
                  <span>{s.emoji}</span> {s.label}
                </div>
                <div className={`text-xs mt-0.5 leading-snug ${selected === s.id ? 'text-teal-100' : 'text-gray-400'}`}>
                  {s.description}
                </div>
              </button>
            ))}
          </div>

          {/* Message preview */}
          <div className="flex-1 flex flex-col overflow-hidden min-h-0">
            <div className="flex-1 overflow-y-auto p-4">
              {DATOS[selected] && (
                <div className="mb-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
                  {DATOS[selected].map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => copiarDato(p.id, p.valor)}
                      title="Copiar solo este dato"
                      className="group flex items-center gap-3 rounded-xl border border-teal-100 bg-gradient-to-br from-teal-50 to-white px-3 py-2.5 text-left transition-colors hover:border-[#187f77] active:scale-[0.98]"
                    >
                      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white text-lg shadow-sm">{p.icono}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block text-[11px] font-semibold uppercase tracking-wide text-[#187f77]">{p.titulo}</span>
                        <span className="block truncate font-mono text-sm font-bold text-gray-900">{p.valor}</span>
                        <span className="block text-[11px] text-gray-400">{p.nota}</span>
                      </span>
                      {copiadoDato === p.id
                        ? <CheckCircle size={16} className="shrink-0 text-green-600" />
                        : <Copy size={15} className="shrink-0 text-gray-300 group-hover:text-[#187f77]" />}
                    </button>
                  ))}
                </div>
              )}
              <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed bg-gray-50 rounded-xl p-4 border border-gray-100">
                {scenario.message}
              </pre>
            </div>

            {/* Actions */}
            <div className="p-4 border-t flex gap-2.5 bg-white">
              <button
                onClick={copyMessage}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl border-2 border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {copied ? <CheckCircle size={15} className="text-green-600" /> : <Copy size={15} />}
                {copied ? '¡Copiado!' : 'Copiar'}
              </button>
              <button
                onClick={openWhatsApp}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-bold text-white transition-colors"
                style={{ backgroundColor: '#25D366' }}
              >
                <MessageCircle size={15} />
                Abrir WhatsApp
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
