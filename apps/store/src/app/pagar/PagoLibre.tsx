'use client';

/**
 * El formulario del pago libre. Tres campos y a pagar.
 *
 * **El monto lo pone el cliente, y aquí sí está bien.** La regla de que el servidor
 * calcula el monto existe para que nadie compre un bulto de concentrado por mil
 * pesos: protege un PRECIO que fijamos nosotros. En un pago libre no hay producto ni
 * precio que proteger — el cliente declara cuánto quiere pagar y paga eso. Si pone
 * una cifra baja, simplemente abonó menos; nadie sale perdiendo.
 *
 * Lo que sí hace falta es pedirle nombre y celular: un abono sin saber de quién es
 * no sirve para nada, y es justo el dato que hay que buscar a mano cuando llega una
 * transferencia suelta.
 */

import { useState } from 'react';
import { Clock, MapPin, Phone, ShieldCheck, Star } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';
import { formatCurrency } from '@/lib/utils';

const SUGERENCIAS = [20000, 30000, 50000, 100000];

export function PagoLibre() {
  const [nombre, setNombre] = useState('');
  const [telefono, setTelefono] = useState('');
  const [monto, setMonto] = useState('');
  const [concepto, setConcepto] = useState('');
  const [trampa, setTrampa] = useState('');
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  const montoNum = Number(monto.replace(/\D/g, '')) || 0;
  const telOk = /^3\d{9}$/.test(telefono.replace(/\D/g, ''));
  const puede = nombre.trim().length >= 2 && telOk && montoNum >= 1000;

  async function continuar() {
    if (!puede) return;
    setError('');
    setEnviando(true);
    try {
      const r = await fetch('/api/v1/public/pago-libre', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre: nombre.trim(),
          telefono: telefono.replace(/\D/g, ''),
          monto: montoNum,
          concepto: concepto.trim() || null,
          website: trampa || null,
        }),
      });
      const d = await r.json();
      if (!r.ok || !d?.pagar_en) throw new Error(d?.detail ?? 'No se pudo preparar el pago');
      window.location.href = d.pagar_en;
    } catch (e) {
      setEnviando(false);
      setError(
        e instanceof Error && e.message !== 'Failed to fetch'
          ? e.message
          : 'No pudimos preparar el pago. Intenta de nuevo o escríbenos por WhatsApp.',
      );
    }
  }

  return (
    <div className="min-h-[85vh] bg-gradient-to-b from-[#f2fbfa] to-white py-10">
      <div className="container-tight max-w-lg">
        <div className="text-center">
          <p className="text-xs font-semibold uppercase tracking-wider text-[#187f77]">
            Pago seguro
          </p>
          <h1 className="mt-1 font-display text-2xl font-bold text-[#0d4a45]">
            Pagar o abonar
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Bigotes y Paticas · Tienda de mascotas, Dosquebradas
          </p>
          <div className="mt-3 flex items-center justify-center gap-1.5 text-sm">
            <Star className="h-4 w-4 fill-[#f5a641] text-[#f5a641]" aria-hidden="true" />
            <span className="font-semibold">{BUSINESS_INFO.rating.value}</span>
            <span className="text-muted-foreground">en Google</span>
          </div>
        </div>

        <div className="mt-7 rounded-3xl border border-border bg-white p-6 shadow-sm">
          <label className="block text-sm font-semibold">¿Cuánto vas a pagar?</label>
          <div className="relative mt-2">
            <span className="absolute left-4 top-1/2 -translate-y-1/2 text-xl text-muted-foreground">
              $
            </span>
            <input
              value={monto}
              onChange={(e) => setMonto(e.target.value)}
              inputMode="numeric"
              placeholder="30000"
              className="w-full rounded-2xl border border-border py-4 pl-9 pr-4 text-2xl font-bold tabular-nums outline-none focus:border-[#187f77]"
            />
          </div>
          {/* Atajos: la mayoría de los abonos caen en cifras redondas, y teclear en
              el celular es donde se abandona. */}
          <div className="mt-2 flex flex-wrap gap-2">
            {SUGERENCIAS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => setMonto(String(s))}
                className="rounded-xl border border-border px-3 py-1.5 text-xs font-semibold transition-colors hover:border-[#187f77] hover:text-[#187f77]"
              >
                {formatCurrency(s)}
              </button>
            ))}
          </div>

          <div className="mt-5 space-y-4">
            <div>
              <label className="block text-sm font-semibold">Tu nombre</label>
              <input
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                placeholder="Como te conocemos"
                className="mt-1.5 w-full rounded-xl border border-border px-4 py-2.5 text-sm outline-none focus:border-[#187f77]"
              />
            </div>
            <div>
              <label className="block text-sm font-semibold">Tu celular (WhatsApp)</label>
              <input
                value={telefono}
                onChange={(e) => setTelefono(e.target.value)}
                inputMode="numeric"
                placeholder="3001234567"
                className={`mt-1.5 w-full rounded-xl border px-4 py-2.5 text-sm outline-none focus:border-[#187f77] ${
                  telefono && !telOk ? 'border-red-300' : 'border-border'
                }`}
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Para confirmarte el pago y saber a quién abonarlo.
              </p>
            </div>
            <div>
              <label className="block text-sm font-semibold">
                ¿De qué es el pago? <span className="font-normal text-muted-foreground">(opcional)</span>
              </label>
              <input
                value={concepto}
                onChange={(e) => setConcepto(e.target.value)}
                placeholder="Ej: abono peluquería de Luna"
                className="mt-1.5 w-full rounded-xl border border-border px-4 py-2.5 text-sm outline-none focus:border-[#187f77]"
              />
            </div>
          </div>

          {/* Trampa para bots: una persona nunca llena un campo que no ve. */}
          <input
            tabIndex={-1}
            autoComplete="off"
            aria-hidden="true"
            value={trampa}
            onChange={(e) => setTrampa(e.target.value)}
            className="absolute left-[-9999px] h-0 w-0 opacity-0"
          />

          {error && (
            <div className="mt-4 rounded-2xl border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
              {error}
            </div>
          )}

          <button
            onClick={continuar}
            disabled={!puede || enviando}
            className="mt-6 w-full rounded-2xl bg-[#187f77] py-4 text-lg font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {enviando
              ? 'Preparando tu pago…'
              : montoNum > 0
                ? `Pagar ${formatCurrency(montoNum)}`
                : 'Pagar'}
          </button>

          <p className="mt-4 flex items-start gap-2 text-xs leading-relaxed text-muted-foreground">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
            <span>
              El pago lo procesa <strong>Bold</strong>: tarjeta, PSE, Nequi o Daviplata.
              Tus datos de tarjeta viajan directo a la pasarela, nosotros nunca los
              vemos ni los guardamos.
            </span>
          </p>
        </div>

        <div className="mt-5 rounded-3xl border border-border bg-white/70 p-5 text-sm">
          <p className="font-semibold text-[#0d4a45]">¿Dudas antes de pagar?</p>
          <ul className="mt-3 space-y-2 text-muted-foreground">
            <li className="flex items-start gap-2">
              <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <span>
                {BUSINESS_INFO.address.streetAddress}, {BUSINESS_INFO.address.addressLocality}
              </span>
            </li>
            <li className="flex items-start gap-2">
              <Clock className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <span>Lunes a sábado, 10:00 a. m. – 7:00 p. m.</span>
            </li>
            <li className="flex items-start gap-2">
              <Phone className="mt-0.5 h-4 w-4 shrink-0 text-[#187f77]" aria-hidden="true" />
              <a
                href={`https://wa.me/${BUSINESS_INFO.whatsapp}`}
                className="font-medium text-[#187f77] underline"
              >
                {BUSINESS_INFO.phoneDisplay} · WhatsApp
              </a>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
