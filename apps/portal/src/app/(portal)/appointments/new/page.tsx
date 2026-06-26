'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { appointments, pets } from '@/lib/api';
import { getSpeciesEmoji, cn } from '@/lib/utils';

const SERVICES = [
  { value: 'baño', label: '🛁 Baño', duration: 60 },
  { value: 'grooming', label: '✂️ Grooming', duration: 90 },
  { value: 'peluqueria', label: '✂️ Peluquería', duration: 120 },
  { value: 'consulta', label: '🩺 Consulta vet.', duration: 30 },
  { value: 'vacuna', label: '💉 Vacunación', duration: 20 },
  { value: 'otro', label: '📋 Otro', duration: 60 },
];

export default function NewAppointmentPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [petId, setPetId] = useState('');
  const [service, setService] = useState('');
  const [date, setDate] = useState('');
  const [time, setTime] = useState('09:00');
  const [notes, setNotes] = useState('');

  const { data: petsData } = useQuery({ queryKey: ['portal-pets'], queryFn: pets.list });

  const { mutate, isPending } = useMutation({
    mutationFn: () => {
      const scheduled_at = new Date(`${date}T${time}:00`).toISOString();
      return appointments.create({ pet_id: petId, service_type: service, scheduled_at, notes: notes || undefined });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portal-appointments'] });
      toast.success('Cita solicitada. Te confirmamos por WhatsApp.');
      router.push('/appointments');
    },
    onError: (err: any) => toast.error(err.message ?? 'Error al agendar'),
  });

  const minDate = new Date();
  minDate.setDate(minDate.getDate() + 1);
  const minDateStr = minDate.toISOString().split('T')[0];

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Agendar cita</h1>
      </div>

      {/* Mascota */}
      {petsData && petsData.length > 0 && (
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">Para qué mascota</label>
          <div className="flex gap-2 flex-wrap">
            {petsData.map((pet) => (
              <button
                key={pet.id}
                type="button"
                onClick={() => setPetId(pet.id)}
                className={cn(
                  'flex items-center gap-2 px-3 py-2 rounded-xl border-2 text-sm font-medium transition-all',
                  petId === pet.id
                    ? 'border-primary-700 bg-primary-50 text-primary-700'
                    : 'border-border text-muted'
                )}
              >
                <span>{getSpeciesEmoji(pet.species)}</span>
                {pet.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Servicio */}
      <div>
        <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">Servicio *</label>
        <div className="grid grid-cols-2 gap-2">
          {SERVICES.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setService(s.value)}
              className={cn(
                'px-3 py-3 rounded-xl border-2 text-sm font-medium text-left transition-all',
                service === s.value
                  ? 'border-primary-700 bg-primary-50 text-primary-700'
                  : 'border-border text-foreground'
              )}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Fecha y hora */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Fecha *</label>
          <input type="date" className="input-field" min={minDateStr} value={date} onChange={(e) => setDate(e.target.value)} />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Hora *</label>
          <input type="time" className="input-field" value={time} onChange={(e) => setTime(e.target.value)} />
        </div>
      </div>

      <div>
        <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Notas adicionales</label>
        <textarea
          className="input-field min-h-[72px] resize-none"
          placeholder="Alergias, comportamiento especial, indicaciones..."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      <button
        disabled={isPending || !service || !date}
        onClick={() => mutate()}
        className="btn-primary"
      >
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Solicitar cita'}
      </button>

      <p className="text-xs text-muted text-center">
        Confirmaremos disponibilidad y te escribiremos por WhatsApp.
      </p>
    </div>
  );
}
