'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, LocateFixed, CheckCircle2 } from 'lucide-react';
import { sos, type SOSReportInput } from '@/lib/api';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

const SPECIES = [
  { value: 'perro' as const, emoji: '🐶', label: 'Perro' },
  { value: 'gato' as const, emoji: '🐱', label: 'Gato' },
  { value: 'otro' as const, emoji: '🐾', label: 'Otro' },
];

export default function ReportSOSPage() {
  const router = useRouter();
  const customer = useAuthStore((s) => s.customer);
  const { coords, error: geoError, loading: geoLoading, getCurrentPosition } = useGeolocation();

  const [form, setForm] = useState<Partial<SOSReportInput>>({
    species: 'perro',
    contact_phone: customer?.phone ?? '',
    radius_km: 5,
  });

  const set = <K extends keyof SOSReportInput>(k: K, v: SOSReportInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const { mutate, isPending } = useMutation({
    mutationFn: (data: SOSReportInput) => sos.report(data),
    onSuccess: (event) => {
      toast.success('🐾 Reporte publicado — la comunidad ya fue notificada');
      router.push(`/sos/${event.id}`);
    },
    onError: (err: Error) => toast.error(err.message ?? 'No se pudo publicar el reporte'),
  });

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.pet_name?.trim()) return toast.error('Escribe el nombre de tu mascota');
    if (!form.color?.trim()) return toast.error('Describe el color');
    if (!form.contact_phone?.trim()) return toast.error('Escribe un teléfono de contacto');

    let loc = coords;
    if (!loc) {
      try {
        loc = await getCurrentPosition();
      } catch {
        return toast.error('Necesitamos tu ubicación para publicar el reporte');
      }
    }

    mutate({
      ...(form as SOSReportInput),
      last_seen_lat: loc.lat,
      last_seen_lng: loc.lng,
    });
  }

  return (
    <div className="p-4 pt-6 flex flex-col gap-5 pb-8">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Reportar mascota perdida</h1>
      </div>

      <div className="rounded-2xl p-4 bg-[#FDEEE9] border border-[#f6c7bb]">
        <p className="text-xs text-[#c62f28] font-medium leading-relaxed">
          🐾 Le avisaremos a la comunidad de Bigotes y Paticas cerca de la última ubicación donde la viste.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-5">
        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Nombre *</label>
          <input
            className="input-field"
            placeholder="Nombre de tu mascota"
            value={form.pet_name ?? ''}
            onChange={(e) => set('pet_name', e.target.value)}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Especie *</label>
          <div className="grid grid-cols-3 gap-2">
            {SPECIES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => set('species', s.value)}
                className={cn(
                  'flex flex-col items-center gap-1.5 rounded-xl p-3 border-2 text-xs font-medium transition-all',
                  form.species === s.value
                    ? 'border-[#e8433a] bg-[#FDEEE9] text-[#c62f28]'
                    : 'border-border bg-white text-muted'
                )}
              >
                <span className="text-2xl">{s.emoji}</span>
                {s.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Raza</label>
          <input
            className="input-field"
            placeholder="Opcional"
            value={form.breed ?? ''}
            onChange={(e) => set('breed', e.target.value)}
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Color *</label>
          <input
            className="input-field"
            placeholder="Ej: café con blanco"
            value={form.color ?? ''}
            onChange={(e) => set('color', e.target.value)}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Teléfono de contacto *</label>
          <input
            className="input-field"
            placeholder="300 000 0000"
            value={form.contact_phone ?? ''}
            onChange={(e) => set('contact_phone', e.target.value)}
            required
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Recompensa (opcional)</label>
          <input
            type="number"
            min="0"
            className="input-field"
            placeholder="$ 0"
            value={form.reward ?? ''}
            onChange={(e) => set('reward', e.target.value ? Number(e.target.value) : undefined)}
          />
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
            Radio de alerta a la comunidad
          </label>
          <div className="flex gap-2">
            {[5, 10, 15, 20].map((km) => (
              <button
                key={km}
                type="button"
                onClick={() => set('radius_km', km)}
                className={cn(
                  'flex-1 py-2 rounded-xl text-xs font-semibold border-2 transition-all',
                  form.radius_km === km
                    ? 'border-[#e8433a] bg-[#FDEEE9] text-[#c62f28]'
                    : 'border-border bg-white text-muted'
                )}
              >
                {km} km
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
            Última ubicación vista *
          </label>
          <button
            type="button"
            onClick={() => getCurrentPosition()}
            disabled={geoLoading}
            className={cn(
              'w-full flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold border-2 transition-all',
              coords ? 'border-emerald-400 bg-emerald-50 text-emerald-700' : 'border-border bg-white text-muted'
            )}
          >
            {geoLoading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : coords ? (
              <CheckCircle2 className="h-4 w-4" />
            ) : (
              <LocateFixed className="h-4 w-4" />
            )}
            {coords ? 'Ubicación capturada' : geoLoading ? 'Obteniendo ubicación…' : 'Usar mi ubicación actual'}
          </button>
          {geoError && <p className="text-xs text-red-600 mt-1.5">{geoError}</p>}
        </div>

        <button type="submit" disabled={isPending} className="sos-submit-btn">
          {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : '🐾 Publicar reporte'}
        </button>
      </form>
    </div>
  );
}
