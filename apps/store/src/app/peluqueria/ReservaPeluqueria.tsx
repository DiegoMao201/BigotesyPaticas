'use client';

/**
 * Reserva de peluquería SIN cuenta (28-sep-2026). Diego: "lo importante es captar ese clic
 * en un cliente… no poner esa camisa de fuerza de que se logueen". Usa la misma
 * disponibilidad y el mismo flujo de citas del portal (API /v1/public/grooming).
 */
import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Loader2, ShieldCheck } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';
import { BUSINESS_INFO } from '@/lib/business-info';

type Slot = { time: string; available: boolean; reason?: string | null };

const DIAS = ['dom', 'lun', 'mar', 'mié', 'jue', 'vie', 'sáb'];
const MESES = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];

function isoLocal(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function horaBonita(t: string) {
  const h = Number(t.slice(0, 2));
  const h12 = h > 12 ? h - 12 : h;
  return `${h12}:00 ${h < 12 ? 'a. m.' : 'p. m.'}`;
}

export function ReservaPeluqueria() {
  // 14 días hábiles hacia adelante (domingo cerrado)
  const dias = useMemo(() => {
    const out: Date[] = [];
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    while (out.length < 14) {
      if (d.getDay() !== 0) out.push(new Date(d));
      d.setDate(d.getDate() + 1);
    }
    return out;
  }, []);

  const [dia, setDia] = useState<string>('');
  const [slots, setSlots] = useState<Slot[] | null>(null);
  const [cargandoSlots, setCargandoSlots] = useState(false);
  const [hora, setHora] = useState('');
  const [form, setForm] = useState({ species: 'perro', pet_name: '', full_name: '', phone: '', notes: '', website: '' });
  const [pidiendoPermiso, setPidiendoPermiso] = useState(false);
  const [estado, setEstado] = useState<'idle' | 'enviando' | 'ok'>('idle');
  const [error, setError] = useState('');
  const [hecho, setHecho] = useState<{ fecha: string; hora: string; mascota: string } | null>(null);

  useEffect(() => {
    if (!dia) return;
    let vivo = true;
    setCargandoSlots(true);
    setSlots(null);
    setHora('');
    fetch(`/api/v1/public/grooming/availability?date=${dia}`)
      .then((r) => (r.ok ? r.json() : { slots: [] }))
      .then((d) => vivo && setSlots(d.slots ?? []))
      .catch(() => vivo && setSlots([]))
      .finally(() => vivo && setCargandoSlots(false));
    return () => { vivo = false; };
  }, [dia]);

  function set(k: keyof typeof form, v: string) {
    setForm((f) => ({ ...f, [k]: v }));
  }

  const listo = dia && hora && form.pet_name.trim() && form.full_name.trim() && form.phone.trim();

  // Al enviar, primero la autorización de datos (ventana simple); solo con "Acepto" se reserva.
  function pedirPermiso(e: React.FormEvent) {
    e.preventDefault();
    if (!listo || estado === 'enviando') return;
    setPidiendoPermiso(true);
  }

  async function reservar() {
    setPidiendoPermiso(false);
    if (!listo || estado === 'enviando') return;
    setEstado('enviando');
    setError('');
    try {
      const r = await fetch('/api/v1/public/grooming/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, date: dia, time: hora, accept_data: true }),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) {
        const msg = typeof d.detail === 'string' ? d.detail : 'Revisa los datos, por favor.';
        setError(msg);
        setEstado('idle');
        if (r.status === 409) {
          // la hora se ocupó: refrescar el día
          const a = await fetch(`/api/v1/public/grooming/availability?date=${dia}`).then((x) => x.json()).catch(() => null);
          if (a?.slots) setSlots(a.slots);
          setHora('');
        }
        return;
      }
      setHecho({ fecha: dia, hora, mascota: form.pet_name.trim() });
      setEstado('ok');
      trackEvent('generate_lead', { lead_source: 'reserva_peluqueria_web', value: 0, currency: 'COP' });
      try {
        (window as unknown as { fbq?: (...a: unknown[]) => void }).fbq?.('track', 'Schedule', { content_name: 'grooming' });
      } catch { /* sin píxel */ }
    } catch {
      setError('No pudimos conectarnos. Intenta de nuevo o escríbenos por WhatsApp.');
      setEstado('idle');
    }
  }

  if (estado === 'ok' && hecho) {
    const f = new Date(`${hecho.fecha}T12:00:00`);
    const fechaTxt = `${['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'][f.getDay()]} ${f.getDate()} de ${['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'][f.getMonth()]}`;
    const texto = `Hola, acabo de reservar en la web la peluquería para ${hecho.mascota} el ${fechaTxt} a las ${horaBonita(hecho.hora)}.`;
    return (
      <div className="rounded-3xl bg-white border border-teal-100 shadow-xl p-6 sm:p-8 text-center">
        <CheckCircle2 className="h-16 w-16 text-teal-600 mx-auto mb-3" />
        <h3 className="text-2xl font-display font-extrabold text-[#0d4a45]">¡Listo! Tu cita quedó solicitada</h3>
        <p className="mt-2 text-gray-600">
          <strong>{hecho.mascota}</strong> · {fechaTxt} a las <strong>{horaBonita(hecho.hora)}</strong>
        </p>
        <p className="mt-3 text-sm text-gray-600">
          Te escribimos por WhatsApp para confirmarla y decirte el precio según el tamaño y el pelaje. Recuerda: tienes <strong>10% de descuento</strong> por reservar en línea.
        </p>
        <a
          href={`https://wa.me/${BUSINESS_INFO.whatsapp}?text=${encodeURIComponent(texto)}`}
          target="_blank" rel="noopener noreferrer"
          className="mt-5 inline-flex w-full justify-center rounded-2xl bg-[#25D366] px-5 py-3.5 font-bold text-white shadow-md hover:brightness-95"
        >
          Avisar por WhatsApp (opcional)
        </a>
      </div>
    );
  }

  return (
    <form onSubmit={pedirPermiso} className="rounded-3xl bg-white border border-teal-100 shadow-xl p-5 sm:p-7 space-y-6">
      {/* 1. Mascota */}
      <div>
        <p className="text-sm font-bold text-[#0d4a45] mb-2">1. Tu mascota</p>
        <div className="grid grid-cols-2 gap-2 mb-3">
          {[
            { v: 'perro', l: '🐶 Perro' },
            { v: 'gato', l: '🐱 Gato' },
          ].map((o) => (
            <button key={o.v} type="button" onClick={() => set('species', o.v)}
              className={`rounded-xl border-2 py-2.5 font-semibold transition ${form.species === o.v ? 'border-[#187f77] bg-teal-50 text-[#0d4a45]' : 'border-gray-200 text-gray-500 hover:border-teal-300'}`}>
              {o.l}
            </button>
          ))}
        </div>
        <input
          required maxLength={60} value={form.pet_name} onChange={(e) => set('pet_name', e.target.value)}
          placeholder="¿Cómo se llama?"
          className="w-full rounded-xl border border-gray-200 px-4 py-3 focus:border-[#187f77] focus:outline-none focus:ring-2 focus:ring-teal-100"
        />
      </div>

      {/* 2. Día */}
      <div>
        <p className="text-sm font-bold text-[#0d4a45] mb-2">2. Elige el día</p>
        <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1">
          {dias.map((d) => {
            const iso = isoLocal(d);
            const activo = dia === iso;
            return (
              <button key={iso} type="button" onClick={() => setDia(iso)}
                className={`flex min-w-[58px] flex-col items-center rounded-xl border-2 px-2 py-2 transition ${activo ? 'border-[#187f77] bg-[#187f77] text-white' : 'border-gray-200 bg-white text-gray-700 hover:border-teal-300'}`}>
                <span className="text-[11px] uppercase">{DIAS[d.getDay()]}</span>
                <span className="text-lg font-extrabold leading-tight">{d.getDate()}</span>
                <span className="text-[11px]">{MESES[d.getMonth()]}</span>
              </button>
            );
          })}
        </div>
        <p className="mt-1.5 text-xs text-gray-500">Lunes a sábado. El baño toma unas 2 horas.</p>
      </div>

      {/* 3. Hora */}
      {dia && (
        <div>
          <p className="text-sm font-bold text-[#0d4a45] mb-2">3. Elige la hora</p>
          {cargandoSlots || slots === null ? (
            <div className="flex justify-center py-4"><Loader2 className="h-6 w-6 animate-spin text-[#187f77]" /></div>
          ) : slots.filter((s) => s.available).length === 0 ? (
            <p className="rounded-xl bg-amber-50 px-4 py-3 text-sm text-amber-800">
              Ese día ya no quedan horas. Prueba otro día o escríbenos por WhatsApp.
            </p>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
              {slots.map((s) => (
                <button key={s.time} type="button" disabled={!s.available} onClick={() => setHora(s.time)}
                  className={`rounded-xl border-2 py-2.5 text-sm font-bold transition ${!s.available ? 'cursor-not-allowed border-gray-100 bg-gray-50 text-gray-300 line-through' : hora === s.time ? 'border-[#187f77] bg-[#187f77] text-white' : 'border-gray-200 text-gray-700 hover:border-teal-300'}`}>
                  {horaBonita(s.time)}
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 4. Tus datos */}
      <div>
        <p className="text-sm font-bold text-[#0d4a45] mb-2">{dia ? '4' : '3'}. Tus datos</p>
        <div className="grid gap-3 sm:grid-cols-2">
          <input required maxLength={120} value={form.full_name} onChange={(e) => set('full_name', e.target.value)}
            placeholder="Tu nombre" autoComplete="name"
            className="w-full rounded-xl border border-gray-200 px-4 py-3 focus:border-[#187f77] focus:outline-none focus:ring-2 focus:ring-teal-100" />
          <input required inputMode="tel" maxLength={20} value={form.phone} onChange={(e) => set('phone', e.target.value)}
            placeholder="Celular / WhatsApp" autoComplete="tel"
            className="w-full rounded-xl border border-gray-200 px-4 py-3 focus:border-[#187f77] focus:outline-none focus:ring-2 focus:ring-teal-100" />
        </div>
        <textarea maxLength={500} value={form.notes} onChange={(e) => set('notes', e.target.value)}
          placeholder="¿Algo que debamos saber? Raza, tamaño, si es nervioso… (opcional)"
          className="mt-3 min-h-[70px] w-full resize-none rounded-xl border border-gray-200 px-4 py-3 focus:border-[#187f77] focus:outline-none focus:ring-2 focus:ring-teal-100" />
        {/* trampa para bots: oculta para personas */}
        <input tabIndex={-1} autoComplete="off" aria-hidden="true" value={form.website}
          onChange={(e) => set('website', e.target.value)} className="hidden" name="website" />
      </div>

      {error && <p className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}

      <button type="submit" disabled={!listo || estado === 'enviando'}
        className="flex w-full items-center justify-center gap-2 rounded-2xl bg-[#F5A641] py-4 text-lg font-black text-[#0d4a45] shadow-lg transition hover:brightness-95 disabled:cursor-not-allowed disabled:opacity-50">
        {estado === 'enviando' ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Reservar mi cita ✂️'}
      </button>
      <p className="text-center text-xs text-gray-500">Sin registrarte · te confirmamos por WhatsApp · 10% de descuento</p>

      {pidiendoPermiso && (
        <div className="fixed inset-0 z-[90] flex items-end sm:items-center justify-center bg-black/50 p-4" role="dialog" aria-modal="true"
          aria-label="Autorización de datos" onClick={() => setPidiendoPermiso(false)}>
          <div className="w-full max-w-md rounded-3xl bg-white p-6 shadow-2xl" onClick={(e) => e.stopPropagation()}>
            <ShieldCheck className="h-10 w-10 text-[#187f77]" />
            <h3 className="mt-2 text-lg font-extrabold text-[#0d4a45]">Autorización de datos</h3>
            <p className="mt-2 text-sm text-gray-600 leading-relaxed">
              Autorizo a <strong>Bigotes y Paticas</strong> a usar mi nombre, mi celular y los datos de mi mascota para
              gestionar esta cita y para enviarme información comercial, promociones y novedades por WhatsApp,
              llamada o correo, según la Ley 1581 de 2012. Puedo pedir que los actualicen o los borren cuando quiera.{' '}
              <a href="/politica-privacidad" target="_blank" className="underline">Política de privacidad</a>.
            </p>
            <div className="mt-5 grid gap-2">
              <button type="button" onClick={reservar}
                className="rounded-2xl bg-[#F5A641] py-3.5 font-black text-[#0d4a45] shadow hover:brightness-95">
                Acepto y reservo
              </button>
              <button type="button" onClick={() => setPidiendoPermiso(false)}
                className="rounded-2xl py-3 text-sm font-semibold text-gray-500 hover:bg-gray-50">
                Volver
              </button>
            </div>
          </div>
        </div>
      )}
    </form>
  );
}
