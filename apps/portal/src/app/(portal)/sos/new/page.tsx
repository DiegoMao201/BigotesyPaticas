'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, LocateFixed, CheckCircle2, Camera, ImagePlus } from 'lucide-react';
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
  const [photoFile, setPhotoFile] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const galleryRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);

  const set = <K extends keyof SOSReportInput>(k: K, v: SOSReportInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  function handlePhotoFile(file: File | undefined) {
    if (!file) return;
    if (!file.type.startsWith('image/')) return toast.error('Selecciona una imagen (JPEG, PNG o WebP)');
    if (file.size > 5 * 1024 * 1024) return toast.error('La imagen no debe superar 5 MB');
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  const { mutateAsync } = useMutation({
    mutationFn: (data: SOSReportInput) => sos.report(data),
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

    setSubmitting(true);
    try {
      const event = await mutateAsync({
        ...(form as SOSReportInput),
        last_seen_lat: loc.lat,
        last_seen_lng: loc.lng,
      });
      if (photoFile) {
        try {
          await sos.uploadPhoto(event.id, photoFile);
        } catch {
          toast.error('El reporte se publicó, pero la foto no se pudo subir. Puedes agregarla desde el detalle.');
        }
      }
      toast.success('🐾 Reporte publicado — la comunidad ya fue notificada');
      router.push(`/sos/${event.id}`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo publicar el reporte');
    } finally {
      setSubmitting(false);
    }
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
          <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
            Foto de tu mascota
          </label>
          <div
            className="rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-6 gap-3 relative overflow-hidden"
            style={{ borderColor: '#e8433a60' }}
          >
            {photoPreview ? (
              <div className="relative h-28 w-28 rounded-2xl overflow-hidden">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={photoPreview} alt="Foto de la mascota" className="h-full w-full object-cover" />
              </div>
            ) : (
              <div className="flex flex-col items-center gap-1.5">
                <div className="h-14 w-14 rounded-2xl flex items-center justify-center" style={{ background: '#FDEEE9' }}>
                  <ImagePlus className="h-7 w-7" style={{ color: '#e8433a' }} />
                </div>
                <p className="font-semibold text-foreground text-sm">Sube una foto para identificarla más fácil</p>
                <p className="text-muted text-xs">Opcional pero muy recomendado · máx 5 MB</p>
              </div>
            )}
            <input
              ref={galleryRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handlePhotoFile(e.target.files?.[0])}
            />
            <input
              ref={cameraRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => handlePhotoFile(e.target.files?.[0])}
            />
          </div>
          <div className="grid grid-cols-2 gap-3 mt-3">
            <button
              type="button"
              onClick={() => galleryRef.current?.click()}
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm border-2 border-border bg-white text-muted"
            >
              <ImagePlus className="h-4 w-4" /> Galería
            </button>
            <button
              type="button"
              onClick={() => cameraRef.current?.click()}
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-semibold text-sm border-2"
              style={{ borderColor: '#e8433a', color: '#c62f28' }}
            >
              <Camera className="h-4 w-4" /> Cámara
            </button>
          </div>
        </div>

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

        <button type="submit" disabled={submitting} className="sos-submit-btn">
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : '🐾 Publicar reporte'}
        </button>
      </form>
    </div>
  );
}
