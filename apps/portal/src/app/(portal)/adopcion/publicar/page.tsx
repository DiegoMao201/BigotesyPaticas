'use client';

import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ArrowLeft, Loader2, LocateFixed, CheckCircle2, ImagePlus, X, Upload } from 'lucide-react';
import { adoption, type AdoptionListingInput } from '@/lib/api';
import { useGeolocation } from '@/hooks/useGeolocation';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

interface Draft {
  file: File;
  preview: string;
}

export default function PublishAdoptionPage() {
  const router = useRouter();
  const customer = useAuthStore((s) => s.customer);
  const { coords, error: geoError, loading: geoLoading, getCurrentPosition } = useGeolocation();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [form, setForm] = useState<Partial<AdoptionListingInput>>({
    post_type: 'offer',
    contact_phone: customer?.phone ?? '',
  });
  const [drafts, setDrafts] = useState<Draft[]>([]);
  const [createdId, setCreatedId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [uploading, setUploading] = useState(false);

  const set = <K extends keyof AdoptionListingInput>(k: K, v: AdoptionListingInput[K]) =>
    setForm((f) => ({ ...f, [k]: v }));

  const { mutateAsync: createListing } = useMutation({
    mutationFn: (data: AdoptionListingInput) => adoption.create(data),
  });

  function onFilesSelected(files: FileList | null) {
    if (!files) return;
    const next: Draft[] = Array.from(files)
      .filter((f) => {
        if (!f.type.startsWith('image/')) {
          toast.error(`${f.name}: solo se aceptan imágenes`);
          return false;
        }
        if (f.size > 5 * 1024 * 1024) {
          toast.error(`${f.name}: no debe superar 5 MB`);
          return false;
        }
        return true;
      })
      .map((file) => ({ file, preview: URL.createObjectURL(file) }));
    setDrafts((prev) => [...prev, ...next]);
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!form.title?.trim()) return toast.error('Escribe un título, ej: "Cachorro busca hogar"');
    if (!form.contact_phone?.trim()) return toast.error('Escribe un teléfono de contacto');

    let loc = coords;
    if (!loc) {
      try {
        loc = await getCurrentPosition();
      } catch {
        return toast.error('Necesitamos tu ubicación para publicar');
      }
    }

    setSubmitting(true);
    try {
      const listing = await createListing({ ...(form as AdoptionListingInput), lat: loc.lat, lng: loc.lng });
      setCreatedId(listing.id);
      toast.success('Publicación creada — ahora sube las fotos');
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo crear la publicación');
    } finally {
      setSubmitting(false);
    }
  }

  async function handlePublish() {
    if (!createdId) return;
    if (drafts.length === 0) return toast.error('Sube al menos una foto');
    setUploading(true);
    try {
      await adoption.uploadPhotos(createdId, drafts.map((d) => d.file));
      toast.success('🏠 ¡Publicado! Gracias por ayudarlo a encontrar un hogar');
      router.push(`/adopcion`);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudieron subir las fotos');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="p-4 pt-6 flex flex-col gap-5 pb-8">
      <div className="flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-gray-100">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h1 className="font-display text-xl font-bold text-foreground">Doy en adopción</h1>
      </div>

      <p className="text-xs text-muted -mt-2">
        Bigotes y Paticas conecta a quienes tienen un animal en adopción con quienes desean adoptar — no
        gestionamos ni somos responsables del proceso de adopción en sí.
      </p>

      {!createdId ? (
        <form onSubmit={handleCreate} className="flex flex-col gap-5">
          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Título *</label>
            <input
              className="input-field"
              placeholder='Ej: "Cachorro de 3 meses busca hogar"'
              value={form.title ?? ''}
              onChange={(e) => set('title', e.target.value)}
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Descripción</label>
            <textarea
              className="input-field"
              rows={3}
              placeholder="Personalidad, salud, vacunas, esterilización… (opcional)"
              value={form.description ?? ''}
              onChange={(e) => set('description', e.target.value)}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Especie</label>
              <input
                className="input-field"
                placeholder="Perro, gato…"
                value={form.species ?? ''}
                onChange={(e) => set('species', e.target.value)}
              />
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
          </div>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Dirección / referencia *</label>
            <input
              className="input-field"
              placeholder="Ej: Barrio Cuba, Pereira"
              value={form.address ?? ''}
              onChange={(e) => set('address', e.target.value)}
              required
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
              Observaciones de la entrega
            </label>
            <textarea
              className="input-field"
              rows={2}
              placeholder="Ej: contrato de adopción, visita previa, esterilización obligatoria…"
              value={form.delivery_notes ?? ''}
              onChange={(e) => set('delivery_notes', e.target.value)}
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
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">Ubicación *</label>
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

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold text-white shadow-lg transition-all active:scale-95 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #2fc4a8, #187f77)', boxShadow: '0 8px 20px rgba(24,127,119,0.3)' }}
          >
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Continuar y subir fotos'}
          </button>
        </form>
      ) : (
        <div className="flex flex-col gap-4">
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            className="hidden"
            onChange={(e) => onFilesSelected(e.target.files)}
          />

          {drafts.length === 0 ? (
            <button
              onClick={() => fileInputRef.current?.click()}
              className="rounded-2xl border-2 border-dashed border-emerald-300 flex flex-col items-center justify-center py-10 gap-2 text-emerald-700"
            >
              <Upload className="h-7 w-7" />
              <span className="text-sm font-semibold">Sube las fotos (puedes elegir varias a la vez)</span>
            </button>
          ) : (
            <div className="grid grid-cols-3 gap-2">
              {drafts.map((d, i) => (
                <div key={i} className="relative">
                  <button
                    onClick={() => setDrafts((prev) => prev.filter((_, j) => j !== i))}
                    className="absolute -top-1.5 -right-1.5 h-5 w-5 rounded-full bg-red-500 text-white flex items-center justify-center z-10"
                  >
                    <X className="h-3 w-3" />
                  </button>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={d.preview} alt="" className="aspect-square w-full object-cover rounded-xl" />
                </div>
              ))}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="aspect-square rounded-xl border-2 border-dashed border-emerald-300 flex items-center justify-center text-emerald-600"
              >
                <ImagePlus className="h-5 w-5" />
              </button>
            </div>
          )}

          <button
            onClick={handlePublish}
            disabled={uploading || drafts.length === 0}
            className="inline-flex items-center justify-center gap-2 rounded-xl px-5 py-3.5 text-sm font-bold text-white shadow-lg transition-all active:scale-95 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #2fc4a8, #187f77)', boxShadow: '0 8px 20px rgba(24,127,119,0.3)' }}
          >
            {uploading ? <Loader2 className="h-4 w-4 animate-spin" /> : `🏠 Publicar (${drafts.length} foto${drafts.length === 1 ? '' : 's'})`}
          </button>
        </div>
      )}
    </div>
  );
}
