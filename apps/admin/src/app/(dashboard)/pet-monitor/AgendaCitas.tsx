'use client';

/**
 * Agenda del día (29-sep-2026). Diego: "el admin no tiene generador de citas… necesito que
 * desde el admin se pueda agendar para que coordinemos horarios… cuánto tiempo se le irá
 * bañando el animal… es comunicación global". Línea de tiempo 10 a. m. – 7 p. m. con cada
 * cita ocupando sus horas reales (portal, web o admin). Tocar un espacio libre agenda ahí;
 * lo que se agenda aquí queda confirmado y deja de aparecer en la web y el portal.
 */
import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChevronLeft, ChevronRight, CalendarPlus, Loader2 } from 'lucide-react';
import { adminPortal, type CitaAgenda, type NuevaCitaAdmin } from '@/lib/api';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { openWhatsApp } from '@/lib/whatsapp';

const FILA_PX = 30; // alto de cada media hora
export const DURACIONES = [
  { min: 60, label: '1 h' },
  { min: 120, label: '2 h' },
  { min: 180, label: '3 h' },
  { min: 240, label: '4 h' },
];
const DIRECCION = 'Samara Plaza Mall, Cl. 15 #3A-07, Local 2, Dosquebradas';
const MAPA = 'https://maps.google.com/?cid=8425398225613945586';

function isoLocal(d: Date) {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function aMin(hhmm: string) {
  const [h, m] = hhmm.split(':').map(Number);
  return h * 60 + m;
}
function hora12(hhmm: string) {
  const [h, m] = hhmm.split(':').map(Number);
  return `${h > 12 ? h - 12 : h}:${String(m).padStart(2, '0')} ${h < 12 ? 'a. m.' : 'p. m.'}`;
}
function horaMenos20(hhmm: string) {
  const t = aMin(hhmm) - 20;
  return hora12(`${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`);
}

const ORIGEN: Record<CitaAgenda['origen'], { label: string; cls: string }> = {
  web: { label: 'WEB', cls: 'bg-amber-100 text-amber-800' },
  portal: { label: 'PORTAL', cls: 'bg-purple-100 text-purple-800' },
  admin: { label: 'TIENDA', cls: 'bg-sky-100 text-sky-800' },
};

export function AgendaCitas({ onOpenCita }: { onOpenCita: (id: string) => void }) {
  const [fecha, setFecha] = useState(() => isoLocal(new Date()));
  const [nueva, setNueva] = useState<{ time?: string } | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['admin-agenda', fecha],
    queryFn: () => adminPortal.agendaDia(fecha),
    refetchInterval: 60_000,
  });

  const abre = aMin(data?.abre ?? '10:00');
  const cierra = aMin(data?.cierra ?? '19:00');
  const filas = useMemo(() => {
    const out: string[] = [];
    for (let t = abre; t < cierra; t += 30) out.push(`${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`);
    return out;
  }, [abre, cierra]);

  function mover(dias: number) {
    const d = new Date(`${fecha}T12:00:00`);
    d.setDate(d.getDate() + dias);
    setFecha(isoLocal(d));
  }

  const d = new Date(`${fecha}T12:00:00`);
  const esHoy = fecha === isoLocal(new Date());
  const ocupadoEn = (t: string) =>
    (data?.citas ?? []).some((c) => aMin(c.inicio) <= aMin(t) && aMin(t) < aMin(c.fin));

  return (
    <div className="rounded-2xl border border-teal-100 bg-white p-4 shadow-sm">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <button onClick={() => mover(-1)} className="rounded-lg border p-1.5 hover:bg-gray-50" aria-label="Día anterior"><ChevronLeft size={16} /></button>
        <input type="date" value={fecha} onChange={(e) => e.target.value && setFecha(e.target.value)}
          className="rounded-lg border px-2 py-1 text-sm" />
        <button onClick={() => mover(1)} className="rounded-lg border p-1.5 hover:bg-gray-50" aria-label="Día siguiente"><ChevronRight size={16} /></button>
        {!esHoy && <button onClick={() => setFecha(isoLocal(new Date()))} className="text-xs text-teal-700 underline">Hoy</button>}
        <span className="text-sm font-semibold text-gray-700 capitalize">
          {d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
        </span>
        <Button size="sm" className="ml-auto gap-1.5" onClick={() => setNueva({})}>
          <CalendarPlus size={15} /> Agendar cita
        </Button>
      </div>

      {data?.cerrado && (
        <p className="mb-2 rounded-lg bg-gray-50 px-3 py-2 text-xs text-gray-500">Domingo: la tienda está cerrada (igual puedes agendar si abren).</p>
      )}

      {isLoading ? (
        <div className="flex justify-center py-10"><Loader2 className="h-6 w-6 animate-spin text-teal-600" /></div>
      ) : (
        <div className="relative" style={{ height: filas.length * FILA_PX }}>
          {filas.map((t, i) => (
            <button
              key={t}
              type="button"
              onClick={() => !ocupadoEn(t) && setNueva({ time: t })}
              className={`absolute left-0 right-0 flex items-start border-t text-left ${t.endsWith(':00') ? 'border-gray-200' : 'border-dashed border-gray-100'} ${ocupadoEn(t) ? 'cursor-default' : 'hover:bg-teal-50/60'}`}
              style={{ top: i * FILA_PX, height: FILA_PX }}
              title={ocupadoEn(t) ? undefined : `Agendar a las ${hora12(t)}`}
            >
              <span className="w-16 shrink-0 pl-1 pt-0.5 text-[11px] text-gray-400">{t.endsWith(':00') ? hora12(t) : ''}</span>
            </button>
          ))}
          {(data?.citas ?? []).map((c) => {
            const ini = Math.max(aMin(c.inicio), abre);
            const top = ((ini - abre) / 30) * FILA_PX;
            const alto = Math.max(((aMin(c.fin) - ini) / 30) * FILA_PX - 3, 24);
            const pendiente = c.status === 'pending';
            const hecha = c.status === 'completed';
            return (
              <button
                key={c.id}
                type="button"
                onClick={() => onOpenCita(c.id)}
                className={`absolute left-16 right-1 overflow-hidden rounded-lg border-l-4 px-2 py-1 text-left text-xs shadow-sm transition hover:shadow-md ${pendiente ? 'border-amber-500 bg-amber-50' : hecha ? 'border-gray-400 bg-gray-100' : 'border-teal-600 bg-teal-50'}`}
                style={{ top: top + 1, height: alto }}
              >
                <div className="flex items-center gap-1.5">
                  <strong className="truncate text-gray-900">{c.pet_name ?? 'Mascota'}</strong>
                  <span className="truncate text-gray-600">· {c.customer_name ?? 'Cliente'}</span>
                  <span className={`ml-auto shrink-0 rounded px-1.5 py-0.5 text-[9px] font-bold ${ORIGEN[c.origen].cls}`}>{ORIGEN[c.origen].label}</span>
                </div>
                <div className={pendiente ? 'text-amber-700 font-semibold' : hecha ? 'text-gray-500' : 'text-teal-700'}>
                  {hora12(c.inicio)} – {hora12(c.fin)} · {pendiente ? 'POR CONFIRMAR' : hecha ? 'completada' : 'confirmada'}
                </div>
              </button>
            );
          })}
        </div>
      )}
      <p className="mt-2 text-[11px] text-gray-400">Toca un espacio libre para agendar ahí. Lo que agendas o confirmas aquí se bloquea en la web y el portal.</p>

      {nueva && <NuevaCita fecha={fecha} horaInicial={nueva.time} onClose={() => setNueva(null)} />}
    </div>
  );
}

function NuevaCita({ fecha: fechaInicial, horaInicial, onClose }: { fecha: string; horaInicial?: string; onClose: () => void }) {
  const qc = useQueryClient();
  const [f, setF] = useState<NuevaCitaAdmin>({
    date: fechaInicial, time: horaInicial ?? '', duration_min: 120, owner_name: '', phone: '',
    pet_name: '', species: 'perro', origen: 'tienda', notes: '',
  });
  const set = <K extends keyof NuevaCitaAdmin>(k: K, v: NuevaCitaAdmin[K]) => setF((x) => ({ ...x, [k]: v }));

  const { data: libres, isFetching } = useQuery({
    queryKey: ['admin-horas-libres', f.date, f.duration_min],
    queryFn: () => adminPortal.horasLibres(f.date, f.duration_min),
  });
  const horaValida = !!f.time && (libres?.starts ?? []).includes(f.time);

  const crear = useMutation({
    mutationFn: () => adminPortal.crearCita({ ...f, notes: f.notes?.trim() || undefined }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['admin-agenda'] });
      qc.invalidateQueries({ queryKey: ['admin-portal-appointments'] });
      qc.invalidateQueries({ queryKey: ['admin-horas-libres'] });
      const d = new Date(`${f.date}T12:00:00`);
      const fechaTxt = d.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' });
      const msg = `¡Hola ${f.owner_name.split(' ')[0]}! Te escribo de Bigotes y Paticas. ✅ Quedó agendada la cita de baño y peluquería de ${f.pet_name} para el ${fechaTxt} a las ${hora12(f.time)}.\n\n📍 Trae a tu mascota a la tienda (no hacemos recogida): ${DIRECCION}.\n⏰ Por favor llega 20 minutos antes, a las ${horaMenos20(f.time)}.\n🗺️ Cómo llegar: ${MAPA}\n\nSi no puedes asistir, avísanos por aquí. ¡Te esperamos! 🐾`;
      toast.success(`Cita agendada: ${f.pet_name}, ${hora12(f.time)}`, {
        action: { label: 'Avisar por WhatsApp', onClick: () => openWhatsApp(f.phone, msg) },
        duration: 15000,
      });
      onClose();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const listo = horaValida && f.owner_name.trim().length >= 2 && f.pet_name.trim() && f.phone.replace(/\D/g, '').length >= 10;

  return (
    <Dialog open onClose={onClose} title="Agendar cita de peluquería" size="md">
      <form onSubmit={(e) => { e.preventDefault(); if (listo) crear.mutate(); }}>
        <DialogBody className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium">Día</label>
              <Input type="date" value={f.date} onChange={(e) => { set('date', e.target.value); set('time', ''); }} required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">¿Cuánto se demora?</label>
              <div className="grid grid-cols-4 gap-1">
                {DURACIONES.map((o) => (
                  <button key={o.min} type="button" onClick={() => set('duration_min', o.min)}
                    className={`rounded-md border py-2 text-sm font-semibold ${f.duration_min === o.min ? 'border-teal-600 bg-teal-600 text-white' : 'hover:border-teal-300'}`}>
                    {o.label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div>
            <label className="mb-1 flex items-center gap-2 text-xs font-medium">
              Hora de inicio {isFetching && <Loader2 size={12} className="animate-spin" />}
            </label>
            {libres && libres.starts.length === 0 ? (
              <p className="rounded-md bg-amber-50 px-3 py-2 text-xs text-amber-800">No hay espacio para {f.duration_min / 60} h ese día. Prueba otra duración u otro día.</p>
            ) : (
              <div className="grid grid-cols-4 sm:grid-cols-6 gap-1.5 max-h-40 overflow-y-auto">
                {(libres?.starts ?? []).map((t) => (
                  <button key={t} type="button" onClick={() => set('time', t)}
                    className={`rounded-md border py-1.5 text-xs font-semibold ${f.time === t ? 'border-teal-600 bg-teal-600 text-white' : 'hover:border-teal-300'}`}>
                    {hora12(t)}
                  </button>
                ))}
              </div>
            )}
            {f.time && !horaValida && libres && (
              <p className="mt-1 text-xs text-red-600">Las {hora12(f.time)} no quedan libres para {f.duration_min / 60} h. Elige otra hora.</p>
            )}
            {horaValida && (
              <p className="mt-1 text-xs text-teal-700">
                Separa de {hora12(f.time)} a {hora12(`${String(Math.floor((aMin(f.time) + f.duration_min) / 60)).padStart(2, '0')}:${String((aMin(f.time) + f.duration_min) % 60).padStart(2, '0')}`)}
              </p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="mb-1 block text-xs font-medium">Nombre del dueño *</label>
              <Input value={f.owner_name} onChange={(e) => set('owner_name', e.target.value)} placeholder="Juan García" required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">Celular / WhatsApp *</label>
              <Input value={f.phone} onChange={(e) => set('phone', e.target.value)} placeholder="311 660 2399" inputMode="tel" required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">Nombre de la mascota *</label>
              <Input value={f.pet_name} onChange={(e) => set('pet_name', e.target.value)} placeholder="Rocky" required />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium">Es un…</label>
              <div className="grid grid-cols-2 gap-1">
                {(['perro', 'gato'] as const).map((sp) => (
                  <button key={sp} type="button" onClick={() => set('species', sp)}
                    className={`rounded-md border py-2 text-sm ${f.species === sp ? 'border-teal-600 bg-teal-50 font-semibold text-teal-800' : ''}`}>
                    {sp === 'perro' ? '🐶 Perro' : '🐱 Gato'}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium">¿Cómo llegó la cita?</label>
            <div className="grid grid-cols-3 gap-1">
              {([['tienda', '🏪 En tienda'], ['llamada', '📞 Llamada'], ['whatsapp', '💬 WhatsApp']] as const).map(([v, l]) => (
                <button key={v} type="button" onClick={() => set('origen', v)}
                  className={`rounded-md border py-2 text-sm ${f.origen === v ? 'border-teal-600 bg-teal-50 font-semibold text-teal-800' : ''}`}>
                  {l}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium">Notas (opcional)</label>
            <Input value={f.notes ?? ''} onChange={(e) => set('notes', e.target.value)} placeholder="Corte, raza, si es nervioso…" />
          </div>
          <p className="text-[11px] text-gray-500">Queda confirmada de una vez y esas horas se bloquean en la web y el portal.</p>
        </DialogBody>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={!listo || crear.isPending}>
            {crear.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Agendar'}
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}
