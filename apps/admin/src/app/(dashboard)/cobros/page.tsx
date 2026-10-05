'use client';

/**
 * Enlaces de cobro: para vender por WhatsApp, por teléfono o en el mostrador y
 * cobrar al momento, sin que el cliente tenga que pasar por el catálogo.
 *
 * Diego (5-oct-2026): *"la página de pagos o link de pago para cualquier otro tipo
 * de pagos que no son de la web"*.
 *
 * El cobro entra por el MISMO camino que una venta de la tienda —webhook,
 * verificación de monto, aviso, correo, pedido pagado— y usa LA MISMA página de
 * pago. Por eso se crea aquí y no desde el panel de Bold: un cobro hecho por fuera
 * no queda en la base, no avisa y hay que cuadrarlo a mano después.
 */

import { useState } from 'react';
import { Copy, Link2, Loader2, MessageCircle } from 'lucide-react';
import { toast } from 'sonner';
import { api } from '@/lib/api';

interface Cobro {
  referencia: string;
  monto: number;
  enlace: string;
  whatsapp: string;
  mensaje: string;
  expira: string;
}

const VALIDEZ = [
  { v: 1440, t: '1 día' },
  { v: 4320, t: '3 días' },
  { v: 10080, t: '7 días' },
  { v: 120, t: '2 horas' },
];

export default function CobrosPage() {
  const [concepto, setConcepto] = useState('');
  const [monto, setMonto] = useState('');
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [notas, setNotas] = useState('');
  const [validez, setValidez] = useState(1440);
  const [creando, setCreando] = useState(false);
  const [cobro, setCobro] = useState<Cobro | null>(null);

  const montoNum = Number(monto.replace(/\D/g, '')) || 0;
  const telOk = /^3\d{9}$/.test(telefono.replace(/\D/g, ''));
  const puede = concepto.trim().length >= 3 && montoNum > 0 && nombre.trim().length >= 2 && telOk;

  async function crear() {
    if (!puede) return;
    setCreando(true);
    try {
      const r = await api<Cobro>('/v1/admin/payment-links', {
        method: 'POST',
        body: JSON.stringify({
          concepto: concepto.trim(),
          monto: montoNum,
          cliente_nombre: nombre.trim(),
          cliente_telefono: telefono.replace(/\D/g, ''),
          notas: notas.trim() || null,
          minutos_validez: validez,
        }),
      });
      setCobro(r);
      toast.success('Enlace de cobro creado');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'No se pudo crear el enlace');
    } finally {
      setCreando(false);
    }
  }

  function copiar(texto: string, que: string) {
    navigator.clipboard.writeText(texto);
    toast.success(`${que} copiado`);
  }

  return (
    <div className="p-4 md:p-6 max-w-2xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-[#0d4a45] flex items-center gap-2">
          <Link2 className="h-6 w-6" /> Enlaces de cobro
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Para cobrar por WhatsApp, por teléfono o en el mostrador. El cliente paga con
          tarjeta, PSE, Nequi o Daviplata, y el pedido entra aquí ya pagado.
        </p>
      </div>

      {!cobro ? (
        <div className="bg-white rounded-2xl shadow-sm p-5 space-y-4">
          <Campo label="¿Qué le estás cobrando?" hint="Lo verá el cliente en la página de pago">
            <input
              value={concepto}
              onChange={(e) => setConcepto(e.target.value)}
              placeholder="Ej: Concentrado Hills 2 Kg + arena"
              className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm"
            />
          </Campo>

          <Campo label="Monto total" hint="En pesos, sin puntos. Incluye el domicilio si lo cobras">
            <div className="relative">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400">$</span>
              <input
                value={monto}
                onChange={(e) => setMonto(e.target.value)}
                inputMode="numeric"
                placeholder="45000"
                className="w-full rounded-xl border border-gray-200 pl-8 pr-4 py-2.5 text-sm"
              />
            </div>
            {montoNum > 0 && (
              <p className="mt-1 text-xs font-semibold text-[#187f77]">
                Se le cobrará ${montoNum.toLocaleString('es-CO')}
              </p>
            )}
          </Campo>

          <div className="grid gap-4 sm:grid-cols-2">
            <Campo label="Nombre del cliente">
              <input
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="María Gómez"
                className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm"
              />
            </Campo>
            <Campo label="Celular (WhatsApp)">
              <input
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                inputMode="numeric"
                placeholder="3001234567"
                className={`w-full rounded-xl border px-4 py-2.5 text-sm ${
                  telefono && !telOk ? 'border-red-300' : 'border-gray-200'
                }`}
              />
              {telefono && !telOk && (
                <p className="mt-1 text-xs text-red-600">Debe ser un celular de 10 dígitos</p>
              )}
            </Campo>
          </div>

          <Campo label="Notas internas" hint="Solo las ves tú, no el cliente">
            <input
              value={notas}
              onChange={(e) => setNotas(e.target.value)}
              placeholder="Opcional"
              className="w-full rounded-xl border border-gray-200 px-4 py-2.5 text-sm"
            />
          </Campo>

          <Campo label="El enlace vence en">
            <div className="flex flex-wrap gap-2">
              {VALIDEZ.map((o) => (
                <button
                  key={o.v}
                  type="button"
                  onClick={() => setValidez(o.v)}
                  className={`rounded-xl border px-3 py-1.5 text-sm font-medium ${
                    validez === o.v
                      ? 'border-[#187f77] bg-[#187f77]/10 text-[#187f77]'
                      : 'border-gray-200 text-gray-600'
                  }`}
                >
                  {o.t}
                </button>
              ))}
            </div>
          </Campo>

          <button
            onClick={crear}
            disabled={!puede || creando}
            className="w-full rounded-xl bg-[#187f77] py-3 font-bold text-white disabled:opacity-50"
          >
            {creando ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" /> Creando…
              </span>
            ) : (
              'Crear enlace de cobro'
            )}
          </button>
        </div>
      ) : (
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm text-gray-500">Cobro por</p>
          <p className="text-3xl font-bold text-[#187f77]">
            ${cobro.monto.toLocaleString('es-CO')}
          </p>
          <p className="mt-1 font-mono text-xs text-gray-400">{cobro.referencia}</p>

          {/* El botón de WhatsApp va primero: es lo que de verdad se hace con esto.
              Copiar el enlace es la alternativa, no el camino principal. */}
          <a
            href={cobro.whatsapp}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-5 flex w-full items-center justify-center gap-2 rounded-xl bg-green-500 py-3 font-bold text-white"
          >
            <MessageCircle className="h-5 w-5" /> Enviar por WhatsApp
          </a>

          <button
            onClick={() => copiar(cobro.enlace, 'Enlace')}
            className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl border border-gray-200 py-3 text-sm font-semibold"
          >
            <Copy className="h-4 w-4" /> Copiar solo el enlace
          </button>

          <div className="mt-4 rounded-xl bg-gray-50 p-3">
            <p className="text-xs text-gray-500 mb-1">Mensaje que se enviará:</p>
            <p className="whitespace-pre-line text-sm text-gray-700">{cobro.mensaje}</p>
          </div>

          <p className="mt-4 text-xs leading-relaxed text-gray-500">
            Cuando el cliente pague, el pedido aparecerá en <strong>Pedidos</strong> marcado
            como <strong>💳 PAGADO</strong>, con su aviso y su correo. Mientras no pague no
            sale en la lista: un enlace enviado todavía no es una venta.
          </p>

          <button
            onClick={() => {
              setCobro(null);
              setConcepto('');
              setMonto('');
              setNombre('');
              setTelefono('');
              setNotas('');
            }}
            className="mt-4 w-full rounded-xl border border-gray-200 py-2.5 text-sm font-semibold"
          >
            Crear otro cobro
          </button>
        </div>
      )}
    </div>
  );
}

function Campo({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700">{label}</label>
      {hint && <p className="mb-1.5 text-xs text-gray-400">{hint}</p>}
      {!hint && <div className="mb-1.5" />}
      {children}
    </div>
  );
}
