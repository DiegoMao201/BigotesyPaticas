'use client';

/**
 * Aviso de citas por confirmar (28-sep-2026). Diego: "el admin siempre está abierto…
 * otro pop como el de pedidos que avise que hay citas por confirmar". Las reservas de la
 * web (bigotesypaticas.com/peluqueria) y del portal entran como 'pending'; quien reservó
 * espera el WhatsApp de confirmación, así que el aviso sale apenas llega una nueva y
 * recuerda cada 10 minutos mientras sigan sin confirmar.
 */
import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { CalendarClock } from 'lucide-react';
import { adminPortal } from '@/lib/api';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

const POLL_MS = 2 * 60 * 1000;      // revisa cada 2 minutos
const REMIND_MS = 10 * 60 * 1000;   // recuerda cada 10 minutos si siguen pendientes

export function PendingAppointmentsAlert() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const vistas = useRef<Set<string>>(new Set());
  const ultimoAviso = useRef(0);

  const { data } = useQuery({
    queryKey: ['admin-pending-appointments'],
    queryFn: async () => {
      const rows = await adminPortal.appointments({ status: 'pending', date_from: new Date().toISOString() });
      return rows.sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at));
    },
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  useEffect(() => {
    if (!data) return;
    if (data.length === 0) {
      setOpen(false);
      return;
    }
    const hayNueva = data.some((a) => !vistas.current.has(a.id));
    const toca = Date.now() - ultimoAviso.current >= REMIND_MS;
    if (hayNueva || toca) {
      data.forEach((a) => vistas.current.add(a.id));
      ultimoAviso.current = Date.now();
      setOpen(true);
    }
  }, [data]);

  if (!data || data.length === 0) return null;

  const n = data.length;
  return (
    <Dialog open={open} onClose={() => setOpen(false)} size="sm">
      <DialogBody className="space-y-3 pt-2">
        <div className="mx-auto w-14 h-14 rounded-full bg-teal-100 flex items-center justify-center">
          <CalendarClock className="w-7 h-7 text-teal-700" />
        </div>
        <h2 className="text-lg font-bold font-display text-center">
          Tienes {n} cita{n === 1 ? '' : 's'} por confirmar
        </h2>
        <p className="text-sm text-muted-foreground text-center">
          Esperan tu WhatsApp de confirmación. Confírmalas, cámbiales la hora o cancélalas desde Citas.
        </p>
        <ul className="divide-y rounded-xl border text-sm">
          {data.slice(0, 4).map((a) => {
            const d = new Date(a.scheduled_at);
            const web = a.notes?.includes('Reservó en la web');
            return (
              <li key={a.id} className="flex items-center justify-between gap-2 px-3 py-2">
                <span className="min-w-0 truncate">
                  <strong>{a.pet_name ?? 'Mascota'}</strong> · {a.customer_name ?? 'Cliente'}
                  {web && <span className="ml-1.5 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">WEB</span>}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {d.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })} ·{' '}
                  {d.toLocaleTimeString('es-CO', { hour: 'numeric', minute: '2-digit' })}
                </span>
              </li>
            );
          })}
          {n > 4 && <li className="px-3 py-2 text-xs text-muted-foreground">y {n - 4} más…</li>}
        </ul>
      </DialogBody>
      <DialogFooter className="justify-center">
        <Button variant="outline" onClick={() => setOpen(false)}>Después</Button>
        <Button
          onClick={() => {
            setOpen(false);
            router.push('/pet-monitor?tab=appointments');
          }}
        >
          Revisar citas
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
