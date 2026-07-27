'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { CalendarClock, Plus, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { partner, type ServiceSlotItem } from '@/lib/api';
import { dayLabel } from '@/lib/utils';
import { Button } from '@/components/ui/button';

const DAYS = [0, 1, 2, 3, 4, 5, 6];

type FormState = {
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_minutes: string;
  max_bookings: string;
  service_id: string;
};

const EMPTY: FormState = { day_of_week: 0, start_time: '09:00', end_time: '17:00', slot_minutes: '30', max_bookings: '1', service_id: '' };

export default function DisponibilidadPage() {
  const qc = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<FormState>(EMPTY);

  const { data: slots, isLoading } = useQuery({ queryKey: ['partner-slots'], queryFn: () => partner.slots.list() });
  const { data: services } = useQuery({ queryKey: ['partner-services'], queryFn: () => partner.services.list() });

  const createMut = useMutation({
    mutationFn: () =>
      partner.slots.create({
        service_id: form.service_id || null,
        day_of_week: form.day_of_week,
        start_time: form.start_time,
        end_time: form.end_time,
        slot_minutes: Number(form.slot_minutes),
        max_bookings: Number(form.max_bookings),
      }),
    onSuccess: () => {
      toast.success('Disponibilidad agregada');
      qc.invalidateQueries({ queryKey: ['partner-slots'] });
      setShowForm(false);
      setForm(EMPTY);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const removeMut = useMutation({
    mutationFn: (id: string) => partner.slots.remove(id),
    onSuccess: () => {
      toast.success('Franja eliminada');
      qc.invalidateQueries({ queryKey: ['partner-slots'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const byDay = (day: number) => (slots ?? []).filter((s) => s.day_of_week === day);
  const serviceName = (id: string | null) => (id ? services?.find((s) => s.id === id)?.name : null);

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground flex items-center gap-2">
            <CalendarClock className="h-6 w-6 text-primary-700" /> Disponibilidad
          </h1>
          <p className="text-muted text-sm mt-1">Configura los horarios en los que los clientes pueden agendar contigo.</p>
        </div>
        {!showForm && <Button onClick={() => setShowForm(true)}><Plus className="h-4 w-4" /> Agregar horario</Button>}
      </div>

      {showForm && (
        <div className="card space-y-4">
          <h3 className="font-display font-bold text-foreground">Nuevo horario recurrente</h3>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="col-span-2 sm:col-span-1">
              <label className="label-field">Día</label>
              <select
                className="input-field"
                value={form.day_of_week}
                onChange={(e) => setForm({ ...form, day_of_week: Number(e.target.value) })}
              >
                {DAYS.map((d) => <option key={d} value={d}>{dayLabel(d)}</option>)}
              </select>
            </div>
            <div>
              <label className="label-field">Desde</label>
              <input type="time" className="input-field" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
            </div>
            <div>
              <label className="label-field">Hasta</label>
              <input type="time" className="input-field" value={form.end_time} onChange={(e) => setForm({ ...form, end_time: e.target.value })} />
            </div>
            <div>
              <label className="label-field">Franja (min)</label>
              <input type="number" className="input-field" value={form.slot_minutes} onChange={(e) => setForm({ ...form, slot_minutes: e.target.value })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label-field">Capacidad simultánea</label>
              <input type="number" className="input-field" value={form.max_bookings} onChange={(e) => setForm({ ...form, max_bookings: e.target.value })} />
            </div>
            <div>
              <label className="label-field">Solo para un servicio (opcional)</label>
              <select className="input-field" value={form.service_id} onChange={(e) => setForm({ ...form, service_id: e.target.value })}>
                <option value="">Todos mis servicios</option>
                {(services ?? []).map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <Button variant="outline" onClick={() => { setShowForm(false); setForm(EMPTY); }} className="flex-1">Cancelar</Button>
            <Button onClick={() => createMut.mutate()} disabled={createMut.isPending} className="flex-1">Guardar</Button>
          </div>
        </div>
      )}

      {isLoading && <p className="text-sm text-muted">Cargando…</p>}

      {!isLoading && (slots ?? []).length === 0 && !showForm && (
        <div className="card text-center py-10 text-muted text-sm">
          Todavía no configuras tu disponibilidad. Sin esto, los clientes no podrán ver horarios libres para agendar.
        </div>
      )}

      <div className="space-y-3">
        {DAYS.map((day) => {
          const rules = byDay(day);
          if (rules.length === 0) return null;
          return (
            <div key={day} className="card">
              <p className="font-display font-bold text-foreground mb-2">{dayLabel(day)}</p>
              <div className="flex flex-col gap-2">
                {rules.map((r: ServiceSlotItem) => (
                  <div key={r.id} className="flex items-center justify-between gap-2 rounded-xl bg-primary-50/60 px-3 py-2">
                    <p className="text-sm text-foreground/80">
                      {r.start_time}–{r.end_time} · cada {r.slot_minutes} min · cap. {r.max_bookings}
                      {serviceName(r.service_id) ? ` · ${serviceName(r.service_id)}` : ' · todos los servicios'}
                    </p>
                    <button onClick={() => removeMut.mutate(r.id)} className="text-muted hover:text-red-600 shrink-0">
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
