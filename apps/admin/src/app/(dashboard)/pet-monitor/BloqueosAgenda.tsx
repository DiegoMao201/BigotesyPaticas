'use client';

/**
 * Bloqueos de agenda (29-sep-2026). Diego: "bloquear días de agendamiento… el groomer no
 * está, se va de vacaciones, se enfermó… el portal y la web no tendrán disponibles esos
 * días o esas horas… y no que por estar bloqueado no me deje moverme en la agenda".
 * La web y el portal los respetan; el admin puede agendar o mover citas encima. Al
 * bloquear se listan las citas que quedaron dentro, con acceso directo a reagendarlas.
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Lock, Loader2, Trash2, AlertTriangle } from 'lucide-react';
import { adminPortal, type BloqueoAgenda, type CitaAfectada } from '@/lib/api';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

const HORAS: string[] = [];
for (let t = 10 * 60; t <= 19 * 60; t += 30) HORAS.push(`${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`);
const MOTIVOS = ['Groomer de vacaciones', 'Groomer enfermo', 'Cierre de la tienda'];

function hora12(hhmm: string) {
  const [h, m] = hhmm.split(':').map(Number);
  if (h === 24) return '12:00 a. m.';
  return `${h > 12 ? h - 12 : h === 0 ? 12 : h}:${String(m).padStart(2, '0')} ${h < 12 ? 'a. m.' : 'p. m.'}`;
}

export function describirBloqueo(b: BloqueoAgenda) {
  const ini = new Date(b.inicio);
  const fin = new Date(b.fin);
  const f = (d: Date) => {
    const t = d.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' });
    return t.charAt(0).toUpperCase() + t.slice(1);
  };
  if (b.dia_completo) {
    const ultimo = new Date(fin.getTime() - 1);
    return ini.toDateString() === ultimo.toDateString() ? `${f(ini)} (todo el día)` : `${f(ini)} al ${f(ultimo)} (días completos)`;
  }
  const h = (d: Date) => d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' });
  return `${f(ini)} · ${h(ini)} – ${h(fin)}`;
}

function invalidarAgenda(qc: ReturnType<typeof useQueryClient>) {
  ['admin-agenda', 'admin-bloqueos', 'admin-horas-libres'].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
}

export function CitasAfectadas({ citas, onOpenCita }: { citas: CitaAfectada[]; onOpenCita: (id: string) => void }) {
  return (
    <ul className="divide-y divide-amber-200 rounded-lg border border-amber-200 bg-amber-50 text-sm text-gray-800">
      {citas.map((c) => (
        <li key={c.id} className="flex items-center justify-between gap-2 px-3 py-2">
          <span className="min-w-0 truncate">
            <strong>{c.pet_name ?? 'Mascota'}</strong> · {c.customer_name ?? 'Cliente'} ·{' '}
            {new Date(c.cuando).toLocaleString('es-CO', { weekday: 'short', day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}
            {c.status === 'pending' && <span className="ml-1 text-xs text-amber-700">(por confirmar)</span>}
          </span>
          <Button size="sm" variant="outline" onClick={() => onOpenCita(c.id)}>Reagendar</Button>
        </li>
      ))}
    </ul>
  );
}

export function NuevoBloqueo({ fecha, onClose, onOpenCita }: { fecha: string; onClose: () => void; onOpenCita: (id: string) => void }) {
  const qc = useQueryClient();
  const [tipo, setTipo] = useState<'dias' | 'horas'>('dias');
  const [desde, setDesde] = useState(fecha);
  const [hasta, setHasta] = useState(fecha);
  const [h1, setH1] = useState('14:00');
  const [h2, setH2] = useState('16:00');
  const [motivo, setMotivo] = useState(MOTIVOS[0]);
  const [afectadas, setAfectadas] = useState<CitaAfectada[] | null>(null);

  const crear = useMutation({
    mutationFn: () =>
      adminPortal.crearBloqueo(
        tipo === 'dias'
          ? { fecha_desde: desde, fecha_hasta: hasta, motivo }
          : { fecha_desde: desde, hora_desde: h1, hora_hasta: h2, motivo },
      ),
    onSuccess: (b) => {
      invalidarAgenda(qc);
      if (b.afectadas && b.afectadas.length > 0) {
        setAfectadas(b.afectadas);
      } else {
        toast.success(`Bloqueado: ${describirBloqueo(b)}. La web y el portal ya no ofrecen esas horas.`);
        onClose();
      }
    },
    onError: (e: Error) => toast.error(e.message),
  });

  if (afectadas) {
    return (
      <Dialog open onClose={onClose} title="Bloqueo creado" size="md">
        <DialogBody className="space-y-3">
          <p className="flex items-start gap-2 text-sm text-amber-800">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {afectadas.length === 1 ? 'Esta cita quedó' : `Estas ${afectadas.length} citas quedaron`} dentro del bloqueo. Siguen en pie hasta
            que las muevas: reagéndalas y avísale a cada cliente por WhatsApp.
          </p>
          <CitasAfectadas citas={afectadas} onOpenCita={(id) => { onClose(); onOpenCita(id); }} />
        </DialogBody>
        <DialogFooter>
          <Button onClick={onClose}>Listo</Button>
        </DialogFooter>
      </Dialog>
    );
  }

  const valido = tipo === 'dias' ? !!desde && !!hasta && hasta >= desde : !!desde && h2 > h1;
  return (
    <Dialog open onClose={onClose} title="Bloquear agenda" size="md">
      <form onSubmit={(e) => { e.preventDefault(); if (valido) crear.mutate(); }}>
        <DialogBody className="space-y-4">
          <div className="grid grid-cols-2 gap-1">
            {([['dias', 'Días completos'], ['horas', 'Unas horas de un día']] as const).map(([v, l]) => (
              <button key={v} type="button" onClick={() => setTipo(v)}
                className={`rounded-md border py-2 text-sm ${tipo === v ? 'border-teal-600 bg-teal-50 font-semibold text-teal-800' : ''}`}>
                {l}
              </button>
            ))}
          </div>
          {tipo === 'dias' ? (
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium">Desde</label>
                <Input type="date" value={desde} onChange={(e) => { setDesde(e.target.value); if (e.target.value > hasta) setHasta(e.target.value); }} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">Hasta (inclusive)</label>
                <Input type="date" value={hasta} min={desde} onChange={(e) => setHasta(e.target.value)} />
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="mb-1 block text-xs font-medium">Día</label>
                <Input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">Desde</label>
                <select value={h1} onChange={(e) => setH1(e.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-2 text-sm">
                  {HORAS.slice(0, -1).map((h) => <option key={h} value={h}>{hora12(h)}</option>)}
                </select>
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium">Hasta</label>
                <select value={h2} onChange={(e) => setH2(e.target.value)} className="h-10 w-full rounded-md border border-input bg-background px-2 text-sm">
                  {HORAS.slice(1).map((h) => <option key={h} value={h}>{hora12(h)}</option>)}
                </select>
              </div>
            </div>
          )}
          <div>
            <label className="mb-1 block text-xs font-medium">Motivo (solo lo ves tú)</label>
            <div className="mb-2 flex flex-wrap gap-1">
              {MOTIVOS.map((m) => (
                <button key={m} type="button" onClick={() => setMotivo(m)}
                  className={`rounded-full border px-3 py-1 text-xs ${motivo === m ? 'border-teal-600 bg-teal-50 font-semibold text-teal-800' : ''}`}>
                  {m}
                </button>
              ))}
            </div>
            <Input value={motivo} onChange={(e) => setMotivo(e.target.value)} maxLength={200} />
          </div>
          <p className="text-[11px] text-gray-500">
            La web y el portal no ofrecerán esas horas. Tú sí puedes agendar o mover citas encima si decides atender.
            Si ya hay citas en ese horario, te las muestro para reagendarlas.
          </p>
        </DialogBody>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>Cancelar</Button>
          <Button type="submit" disabled={!valido || crear.isPending} className="gap-1.5">
            {crear.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />} Bloquear
          </Button>
        </DialogFooter>
      </form>
    </Dialog>
  );
}

/** Lista de bloqueos vigentes y futuros, con sus citas afectadas y el botón para quitarlos. */
export function ProximosBloqueos({ onOpenCita }: { onOpenCita: (id: string) => void }) {
  const qc = useQueryClient();
  const { data = [] } = useQuery({ queryKey: ['admin-bloqueos'], queryFn: adminPortal.bloqueos, refetchInterval: 120_000 });
  const [quitando, setQuitando] = useState<string | null>(null);
  const quitar = useMutation({
    mutationFn: (id: string) => adminPortal.quitarBloqueo(id),
    onSuccess: () => { invalidarAgenda(qc); setQuitando(null); toast.success('Bloqueo quitado: esas horas vuelven a estar disponibles'); },
    onError: (e: Error) => toast.error(e.message),
  });
  if (data.length === 0) return null;
  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 text-gray-800">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-gray-500">
        <Lock className="h-3.5 w-3.5" /> Bloqueos próximos
      </p>
      <ul className="space-y-2">
        {data.map((b) => (
          <li key={b.id} className="rounded-xl border border-gray-100 p-3">
            <div className="flex items-center gap-2">
              <span className="min-w-0 flex-1 text-sm">
                <strong className="text-gray-900">{describirBloqueo(b)}</strong>
                {b.motivo && <span className="text-gray-500"> · {b.motivo}</span>}
              </span>
              {quitando === b.id ? (
                <>
                  <Button size="sm" variant="destructive" onClick={() => quitar.mutate(b.id)} disabled={quitar.isPending}>Sí, quitar</Button>
                  <Button size="sm" variant="ghost" onClick={() => setQuitando(null)}>No</Button>
                </>
              ) : (
                <Button size="sm" variant="ghost" className="gap-1 text-red-600" onClick={() => setQuitando(b.id)}>
                  <Trash2 className="h-3.5 w-3.5" /> Quitar
                </Button>
              )}
            </div>
            {b.afectadas && b.afectadas.length > 0 && (
              <div className="mt-2">
                <p className="mb-1 text-xs font-semibold text-amber-700">
                  ⚠ {b.afectadas.length} cita{b.afectadas.length === 1 ? '' : 's'} dentro de este bloqueo:
                </p>
                <CitasAfectadas citas={b.afectadas} onOpenCita={onOpenCita} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
