'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DayPicker } from 'react-day-picker';
import { es } from 'date-fns/locale';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, CalendarDays, Clock } from 'lucide-react';
import { appointments, pets } from '@/lib/api';
import { getSpeciesEmoji, cn } from '@/lib/utils';
import 'react-day-picker/dist/style.css';

const SERVICES = [
  { value: 'baño', label: '🛁 Baño', duration: 60 },
  { value: 'grooming', label: '✂️ Grooming', duration: 90 },
  { value: 'peluqueria', label: '✂️ Peluquería', duration: 120 },
  { value: 'consulta', label: '🩺 Consulta vet.', duration: 30 },
  { value: 'vacuna', label: '💉 Vacunación', duration: 20 },
  { value: 'otro', label: '📋 Otro', duration: 60 },
];

function formatLocalDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export default function NewAppointmentPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const [petId, setPetId] = useState('');
  const [service, setService] = useState('');
  const [selectedDay, setSelectedDay] = useState<Date | undefined>();
  const [selectedSlot, setSelectedSlot] = useState('');
  const [notes, setNotes] = useState('');

  const { data: petsData } = useQuery({ queryKey: ['portal-pets'], queryFn: pets.list });

  const dateStr = selectedDay ? formatLocalDate(selectedDay) : '';
  const { data: availability, isLoading: loadingSlots } = useQuery({
    queryKey: ['availability', dateStr, service],
    queryFn: () => appointments.availability(dateStr, service || 'baño'),
    enabled: !!dateStr && !!service,
    staleTime: 60 * 1000,
  });

  const { mutate: book, isPending } = useMutation({
    mutationFn: () => {
      if (!selectedDay || !selectedSlot || !petId || !service) throw new Error('Faltan datos');
      return appointments.create({
        pet_id: petId,
        service_type: service,
        scheduled_at: `${dateStr}T${selectedSlot}:00`,
        duration_min: SERVICES.find((s) => s.value === service)?.duration ?? 60,
        notes: notes || undefined,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portal-appointments'] });
      toast.success('✅ ¡Cita solicitada! Te avisaremos cuando la aprueben.');
      router.replace('/appointments');
    },
    onError: (err: Error) => toast.error(err.message ?? 'Error al solicitar la cita'),
  });

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const canBook = petId && service && selectedDay && selectedSlot && !isPending;

  return (
    <div className="p-4 pt-6 pb-8 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Solicitar cita</h1>
      </div>

      {/* Paso 1: Mascota */}
      {petsData && petsData.length > 0 && (
        <section>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <span className="h-5 w-5 rounded-full bg-primary-700 text-white text-[10px] font-bold flex items-center justify-center shrink-0">1</span>
            Para qué mascota
          </p>
          <div className="flex gap-2.5 overflow-x-auto scrollbar-hide pb-1">
            {petsData.map((pet) => (
              <button
                key={pet.id}
                onClick={() => setPetId(pet.id)}
                className={cn(
                  'flex flex-col items-center gap-1.5 min-w-[66px] px-3 py-2.5 rounded-2xl border-2 transition-all',
                  petId === pet.id ? 'border-primary-700 bg-primary-50' : 'border-border bg-white'
                )}
              >
                <span className="text-2xl">{getSpeciesEmoji(pet.species)}</span>
                <span className={cn('text-xs font-semibold truncate w-14 text-center', petId === pet.id ? 'text-primary-700' : 'text-muted')}>
                  {pet.name}
                </span>
              </button>
            ))}
          </div>
        </section>
      )}

      {/* Paso 2: Servicio */}
      <section>
        <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <span className="h-5 w-5 rounded-full bg-primary-700 text-white text-[10px] font-bold flex items-center justify-center shrink-0">2</span>
          Tipo de servicio
        </p>
        <div className="grid grid-cols-2 gap-2">
          {SERVICES.map((svc) => (
            <button
              key={svc.value}
              onClick={() => { setService(svc.value); setSelectedSlot(''); }}
              className={cn(
                'flex items-center gap-2.5 py-3 px-4 rounded-xl border-2 text-sm font-medium text-left transition-all',
                service === svc.value
                  ? 'border-primary-700 bg-primary-50 text-primary-700'
                  : 'border-border bg-white text-foreground'
              )}
            >
              <span className="text-lg">{svc.label.split(' ')[0]}</span>
              <span>{svc.label.split(' ').slice(1).join(' ')}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Paso 3: Calendario */}
      {service && (
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <CalendarDays className="h-4 w-4 text-primary-700" />
            Elige el día
          </p>
          <div className="card p-0 overflow-hidden">
            <style>{`
              .rdp { margin: 0; padding: 12px; --rdp-cell-size: 40px; }
              .rdp-day_selected { background-color: #187f77 !important; color: white !important; border-radius: 10px; }
              .rdp-day_today { color: #187f77; font-weight: 700; }
              .rdp-nav_button { color: #187f77; }
              .rdp-caption_label { font-family: inherit; font-weight: 700; color: #1f2937; font-size: 14px; }
              .rdp-head_cell { color: #6b7280; font-size: 11px; }
              .rdp-day { border-radius: 10px; }
              .rdp-day:hover:not([disabled]) { background: #e1f5ee; }
            `}</style>
            <DayPicker
              mode="single"
              selected={selectedDay}
              onSelect={(day) => { setSelectedDay(day); setSelectedSlot(''); }}
              disabled={{ before: today }}
              locale={es}
              weekStartsOn={1}
            />
          </div>
        </motion.section>
      )}

      {/* Paso 4: Slots */}
      {selectedDay && service && (
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <Clock className="h-4 w-4 text-primary-700" />
            Disponibilidad ·{' '}
            {selectedDay.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })}
          </p>

          {loadingSlots ? (
            <div className="flex justify-center py-6">
              <Loader2 className="h-6 w-6 animate-spin text-primary-700" />
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2.5">
              {(availability?.slots ?? []).map((slot) => (
                <button
                  key={slot.time}
                  disabled={!slot.available}
                  onClick={() => setSelectedSlot(slot.time)}
                  className={cn(
                    'flex flex-col items-center py-3 rounded-xl border-2 transition-all text-sm',
                    !slot.available && 'border-gray-100 bg-gray-50 text-gray-400 cursor-not-allowed',
                    slot.available && selectedSlot !== slot.time && 'border-border bg-white text-foreground hover:border-primary-500',
                    selectedSlot === slot.time && 'border-primary-700 bg-primary-700 text-white'
                  )}
                >
                  <span className="font-bold">{slot.time}</span>
                  <span className="text-[10px] mt-0.5">
                    {!slot.available ? 'ocupado' : selectedSlot === slot.time ? 'elegido ✓' : 'disponible'}
                  </span>
                </button>
              ))}
            </div>
          )}
        </motion.section>
      )}

      {/* Notas */}
      {selectedSlot && (
        <motion.section initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">
            Notas adicionales (opcional)
          </label>
          <textarea
            className="input-field min-h-[72px] resize-none"
            placeholder="Indicaciones especiales, alergias, comportamiento..."
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </motion.section>
      )}

      {/* Resumen + Botón */}
      <AnimatePresence>
        {selectedSlot && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col gap-3"
          >
            <div className="card-glass p-4 rounded-2xl text-sm flex flex-col gap-1.5">
              <p className="font-semibold text-foreground">Resumen</p>
              <p className="text-muted">
                <span className="text-foreground font-medium">
                  {SERVICES.find((s) => s.value === service)?.label}
                </span>
                {' · '}
                {selectedDay?.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
                {' a las '}<strong>{selectedSlot}</strong>
              </p>
              <p className="text-xs text-primary-700 font-semibold">+50 puntos Bigotes al completar</p>
            </div>

            <button
              onClick={() => book()}
              disabled={!canBook}
              className="btn-primary py-4 text-base font-bold disabled:opacity-60"
            >
              {isPending ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                'Solicitar cita →'
              )}
            </button>
            <p className="text-xs text-muted text-center">
              Un asesor confirmará la cita y te notificará en la campana 🔔
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
