'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { DayPicker } from 'react-day-picker';
import { es } from 'date-fns/locale';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Loader2, CalendarDays, Clock } from 'lucide-react';
import { appointments, pets, type PetCreate } from '@/lib/api';
import { useMetaPixelEvent } from '@/hooks/useMetaPixelEvent';
import { getSpeciesEmoji, cn } from '@/lib/utils';
import { PageHeader } from '@/components/ui/page-header';
import 'react-day-picker/dist/style.css';

// Solo lo que se presta de verdad (27-sep-2026): la tienda NO hace consulta veterinaria
// ni vacunación; antes el portal las ofrecía y alguien podía reservarlas.
const SERVICES = [
  {
    value: 'grooming',
    icon: '🛁',
    label: 'Baño y peluquería',
    sublabel: 'Canina y felina',
    description: 'Baño, corte, cepillado y corte de uñas',
    duration: 120,
  },
];

// Promoción de lanzamiento del groomer: quien reserva por el portal tiene 10% de
// descuento. Viaja como nota en la cita para que quien atiende lo vea y lo aplique.
const NOTA_DESCUENTO = 'Reservó por el portal: 10% de descuento en el servicio.';

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
  const [service, setService] = useState('grooming');
  const [selectedDay, setSelectedDay] = useState<Date | undefined>();
  const [selectedSlot, setSelectedSlot] = useState('');
  const [notes, setNotes] = useState('');
  // Quien llega sin mascota registrada (p. ej. desde el anuncio) la escribe aquí mismo;
  // antes el botón nunca se habilitaba porque no había mascota que elegir.
  const [newPetName, setNewPetName] = useState('');
  const [newPetSpecies, setNewPetSpecies] = useState<'perro' | 'gato'>('perro');
  const { track } = useMetaPixelEvent();

  const { data: petsData, isLoading: loadingPets } = useQuery({ queryKey: ['portal-pets'], queryFn: pets.list });
  const sinMascotas = !loadingPets && (petsData?.length ?? 0) === 0;

  const dateStr = selectedDay ? formatLocalDate(selectedDay) : '';
  const { data: availability, isLoading: loadingSlots } = useQuery({
    queryKey: ['availability', dateStr, service],
    queryFn: () => appointments.availability(dateStr, service || 'grooming'),
    enabled: !!dateStr && !!service,
    staleTime: 60 * 1000,
  });

  const { mutate: book, isPending } = useMutation({
    mutationFn: async () => {
      let pid = petId;
      if (!pid && sinMascotas && newPetName.trim()) {
        const nueva = await pets.create({ name: newPetName.trim(), species: newPetSpecies } as PetCreate);
        pid = nueva.id;
        qc.invalidateQueries({ queryKey: ['portal-pets'] });
      }
      if (!selectedDay || !selectedSlot || !pid || !service) throw new Error('Faltan datos');
      return appointments.create({
        pet_id: pid,
        service_type: service,
        scheduled_at: `${dateStr}T${selectedSlot}:00`,
        duration_min: SERVICES.find((s) => s.value === service)?.duration ?? 60,
        notes: [NOTA_DESCUENTO, notes.trim()].filter(Boolean).join(' · '),
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['portal-appointments'] });
      track('Schedule', { content_name: service, content_category: 'appointment' });
      toast.success('✅ ¡Cita solicitada! Te avisaremos cuando la aprueben.');
      router.replace('/appointments');
    },
    onError: (err: Error) => toast.error(err.message ?? 'Error al solicitar la cita'),
  });

  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const tieneMascota = !!petId || (sinMascotas && newPetName.trim().length > 0);
  const canBook = tieneMascota && service && selectedDay && selectedSlot && !isPending;

  return (
    <div className="p-4 pt-6 pb-8 flex flex-col gap-5">
      <PageHeader title="Solicitar cita" subtitle="Baño y peluquería canina y felina" back />

      <div className="rounded-2xl bg-gradient-to-r from-teal-600 to-emerald-500 text-white p-4 shadow-md">
        <p className="text-lg font-extrabold leading-tight">🎉 10% de descuento</p>
        <p className="text-sm opacity-95">por reservar tu cita de peluquería aquí en el portal. Lunes a sábado, 10 a. m. a 7 p. m.</p>
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

      {sinMascotas && (
        <section>
          <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
            <span className="h-5 w-5 rounded-full bg-primary-700 text-white text-[10px] font-bold flex items-center justify-center shrink-0">1</span>
            Tu mascota
          </p>
          <div className="flex gap-2 mb-2.5">
            {(['perro', 'gato'] as const).map((sp) => (
              <button key={sp} type="button" onClick={() => setNewPetSpecies(sp)}
                className={cn('flex-1 py-2.5 rounded-xl border-2 text-sm font-semibold',
                  newPetSpecies === sp ? 'border-primary-700 bg-primary-50 text-primary-700' : 'border-border bg-white text-muted')}>
                {sp === 'perro' ? '🐶 Perro' : '🐱 Gato'}
              </button>
            ))}
          </div>
          <input className="input-field" placeholder="¿Cómo se llama?" value={newPetName} maxLength={60}
            onChange={(e) => setNewPetName(e.target.value)} />
        </section>
      )}

      {/* Paso 2: Servicio */}
      <section>
        <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-3 flex items-center gap-1.5">
          <span className="h-5 w-5 rounded-full bg-primary-700 text-white text-[10px] font-bold flex items-center justify-center shrink-0">2</span>
          Tipo de servicio
        </p>
        <div className="flex flex-col gap-3 md:flex-row">
          {SERVICES.map((svc) => (
            <motion.button
              key={svc.value}
              onClick={() => { setService(svc.value); setSelectedSlot(''); }}
              whileTap={{ scale: 0.97 }}
              className={cn(
                'flex-1 flex flex-col items-center gap-2 py-5 px-4 rounded-2xl border-2 text-center transition-all',
                service === svc.value
                  ? 'border-primary-700 bg-primary-50 shadow-md'
                  : 'border-border bg-white hover:border-primary-300'
              )}
            >
              <span className="text-4xl">{svc.icon}</span>
              <div>
                <p className={cn('font-bold text-sm', service === svc.value ? 'text-primary-700' : 'text-foreground')}>
                  {svc.label}
                </p>
                <p className="text-xs text-muted mt-0.5">{svc.sublabel}</p>
              </div>
              <p className="text-[11px] text-muted leading-snug px-2 hidden md:block">{svc.description}</p>
              {service === svc.value && (
                <span className="text-[11px] font-bold text-primary-700 bg-primary-100 rounded-full px-2.5 py-0.5">
                  ✓ Elegido
                </span>
              )}
            </motion.button>
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
              disabled={[{ before: today }, { dayOfWeek: [0] }]}
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
          ) : (availability?.slots ?? []).length === 0 ? (
            <p className="text-sm text-muted text-center py-4">Ese día no atendemos. Elige de lunes a sábado.</p>
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
                    {!slot.available ? (slot.reason ?? 'ocupado') : selectedSlot === slot.time ? 'elegido ✓' : 'disponible'}
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
                  {SERVICES.find((s) => s.value === service)?.icon} {SERVICES.find((s) => s.value === service)?.label}
                </span>
                {' · '}
                {selectedDay?.toLocaleDateString('es-CO', { weekday: 'long', day: 'numeric', month: 'long' })}
                {' a las '}<strong>{selectedSlot}</strong>
              </p>
              <p className="text-xs text-primary-700 font-semibold">+50 puntos Bigotes al completar</p>
            </div>

            {/* Mismas reglas que la reserva de la web (28-sep-2026): sin vacíos para el cliente */}
            <div className="rounded-2xl bg-primary-50 px-4 py-3 text-xs text-foreground flex flex-col gap-1">
              <p>🏪 Traes a tu mascota a la tienda: no hacemos recogida.</p>
              <p>📍 Samara Plaza Mall, Cl. 15 #3A-07, Local 2, Dosquebradas.</p>
              <p>⏰ Llega 20 minutos antes de tu cita.</p>
              <p>✅ La cita queda en firme cuando te la confirmemos por WhatsApp.</p>
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
              Te confirmamos por WhatsApp y en la campana 🔔
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
