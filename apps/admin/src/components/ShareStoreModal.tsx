'use client';

import { useState } from 'react';
import { X, Copy, MessageCircle, CheckCircle } from 'lucide-react';

interface Scenario {
  id: string;
  label: string;
  emoji: string;
  description: string;
  message: string;
}

const SCENARIOS: Scenario[] = [
  {
    id: 'info_general',
    label: 'Info de la tienda',
    emoji: '🏠',
    description: 'Cuando preguntan qué es Bigotes y Paticas',
    message:
      '¡Hola! 🐾 Somos *Bigotes y Paticas*, tu pet shop de confianza en Dosquebradas y Pereira.\n\n' +
      '🛒 *Tienda online:* https://bigotesypaticas.com\n' +
      '  +900 productos: concentrados, accesorios, medicamentos y más\n' +
      '  Envío gratis en pedidos desde $30.000\n\n' +
      '📱 *Portal de clientes:* https://mi.bigotesypaticas.com\n' +
      '  Pedí domicilio, acumulá Puntos Bigotes y llevá el carnet de tu mascota\n\n' +
      '📍 *Tienda física:* Mall Zamara Plaza, Local 2 · Dosquebradas\n' +
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
      '🚚 *Envío:* 24-72h en Pereira y Dosquebradas\n' +
      '💰 *Envío gratis* en pedidos desde $30.000\n' +
      '💵 Pago contra entrega (efectivo, tarjeta, Nequi, Daviplata)\n\n' +
      '📍 Mall Zamara Plaza, Local 2 · 320 687 6633',
  },
  {
    id: 'ubicacion',
    label: 'Ubicación y horarios',
    emoji: '📍',
    description: 'Dirección, cómo llegar y horario de atención',
    message:
      '¡Hola! Nuestra *tienda física* está en 🐾\n\n' +
      '📍 *Mall Zamara Plaza, Local 2*\n' +
      '  Cl. 15 #3A-07 · Dosquebradas, Risaralda\n\n' +
      '🕐 *Horario:* Lunes a Sábado, 10am a 7pm\n\n' +
      '🗺️ Ver en Google Maps:\n' +
      'https://www.google.com/maps/search/?api=1&query=Bigotes+y+Paticas+Mall+Zamara+Plaza+Dosquebradas\n\n' +
      '🚚 También hacemos *domicilio en 24-72h* a Pereira y Dosquebradas.\n' +
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
      '🚚 Envío gratis desde $30.000 · Entrega 24-72h\n' +
      '📱 Portal de puntos: https://mi.bigotesypaticas.com · 📸 @bigotesypaticas',
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function ShareStoreModal({ open, onClose }: Props) {
  const [selected, setSelected] = useState<string>('info_general');
  const [copied, setCopied] = useState(false);

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

  function openWhatsApp() {
    window.open(`https://wa.me/?text=${encodeURIComponent(scenario.message)}`, '_blank', 'noopener,noreferrer');
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
