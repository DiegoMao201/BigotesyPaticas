'use client';

import { useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ArrowLeft, Phone, MessageCircle, MapPin, Gift, Eye,
  CheckCircle2, Loader2, PartyPopper, ImagePlus,
} from 'lucide-react';
import { sos } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { useGeolocation } from '@/hooks/useGeolocation';
import { getSpeciesEmoji, formatDate, formatRelativeDate, whatsappLink } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export default function SOSDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const customer = useAuthStore((s) => s.customer);
  const { getCurrentPosition } = useGeolocation();

  const [showSightingForm, setShowSightingForm] = useState(false);
  const [note, setNote] = useState('');
  const photoInputRef = useRef<HTMLInputElement>(null);

  const { data: event, isLoading } = useQuery({
    queryKey: ['sos-detail', id],
    queryFn: () => sos.get(id),
  });

  const { mutate: uploadPhoto, isPending: uploadingPhoto } = useMutation({
    mutationFn: (file: File) => sos.uploadPhoto(id, file),
    onSuccess: () => {
      toast.success('📷 Foto agregada');
      qc.invalidateQueries({ queryKey: ['sos-detail', id] });
    },
    onError: (err: Error) => toast.error(err.message ?? 'No se pudo subir la foto'),
  });

  function handlePhotoFile(file: File | undefined) {
    if (!file) return;
    if (!file.type.startsWith('image/')) return toast.error('Selecciona una imagen (JPEG, PNG o WebP)');
    if (file.size > 5 * 1024 * 1024) return toast.error('La imagen no debe superar 5 MB');
    uploadPhoto(file);
  }

  const { mutate: sendSighting, isPending: sendingSighting } = useMutation({
    mutationFn: async () => {
      const loc = await getCurrentPosition();
      return sos.sighting(id, { lat: loc.lat, lng: loc.lng, note: note.trim() || undefined });
    },
    onSuccess: () => {
      toast.success('¡Gracias! Le avisamos a quien la reportó 🐾');
      setShowSightingForm(false);
      setNote('');
      qc.invalidateQueries({ queryKey: ['sos-detail', id] });
    },
    onError: (err: Error) => toast.error(err.message ?? 'No se pudo enviar el avistamiento'),
  });

  const { mutate: markFound, isPending: markingFound } = useMutation({
    mutationFn: () => sos.markFound(id),
    onSuccess: () => {
      toast.success('🎉 ¡Qué buena noticia! Marcado como encontrado');
      qc.invalidateQueries({ queryKey: ['sos-detail', id] });
      qc.invalidateQueries({ queryKey: ['sos-nearby'] });
    },
    onError: (err: Error) => toast.error(err.message ?? 'No se pudo actualizar'),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!event) return null;

  const isReporter = customer?.customer_id === event.reporter_customer_id;
  const isActive = event.status === 'active';
  const mapsUrl = `https://www.google.com/maps?q=${event.last_seen_lat},${event.last_seen_lng}`;
  const waLink = whatsappLink(
    `Hola, vi tu publicación en Bigotes y Paticas sobre ${event.pet_name}. Quiero contarte algo.`
  );

  return (
    <div className="flex flex-col gap-5 pb-8">
      <div className="sos-hero px-4 pt-6 pb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-white/10 text-white">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-display text-lg font-bold text-white">Reporte SOS</h1>
        </div>
      </div>

      <div className="px-4 flex flex-col gap-4 -mt-10">
        {/* Foto + info principal */}
        <div className="card flex flex-col gap-3">
          <div className="flex gap-3">
            <div className="h-20 w-20 rounded-2xl shrink-0 overflow-hidden bg-[#FDEEE9] flex items-center justify-center text-4xl">
              {event.photos[0] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={event.photos[0]} alt={event.pet_name} className="h-full w-full object-cover" />
              ) : (
                getSpeciesEmoji(event.species)
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-display text-xl font-bold text-foreground">{event.pet_name}</h2>
                {isActive ? (
                  <span className="sos-badge">Perdido</span>
                ) : event.status === 'found' ? (
                  <span className="sos-badge-success">Encontrado</span>
                ) : (
                  <span className="sos-badge-success">Cerrado</span>
                )}
              </div>
              <p className="text-sm text-muted capitalize">
                {event.species}{event.breed ? ` • ${event.breed}` : ''} • {event.color}
              </p>
              {event.reward != null && event.reward > 0 && (
                <p className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 mt-1">
                  <Gift className="h-3.5 w-3.5" /> Recompensa disponible
                </p>
              )}
            </div>
          </div>

          {(event.photos.length > 1 || (isReporter && isActive)) && (
            <div className="flex gap-2 overflow-x-auto scrollbar-hide">
              {event.photos.slice(1).map((url) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img key={url} src={url} alt={event.pet_name} className="h-16 w-16 rounded-xl object-cover shrink-0" />
              ))}
              {isReporter && isActive && (
                <button
                  type="button"
                  onClick={() => photoInputRef.current?.click()}
                  disabled={uploadingPhoto}
                  className="h-16 w-16 rounded-xl border-2 border-dashed flex items-center justify-center shrink-0"
                  style={{ borderColor: '#e8433a60' }}
                >
                  {uploadingPhoto ? (
                    <Loader2 className="h-5 w-5 animate-spin" style={{ color: '#e8433a' }} />
                  ) : (
                    <ImagePlus className="h-5 w-5" style={{ color: '#e8433a' }} />
                  )}
                </button>
              )}
            </div>
          )}
          {isReporter && isActive && (
            <input
              ref={photoInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={(e) => handlePhotoFile(e.target.files?.[0])}
            />
          )}

          <div className="flex flex-col gap-1.5 text-xs text-muted pt-1 border-t border-border">
            <p className="flex items-center gap-1.5">
              <MapPin className="h-3.5 w-3.5 shrink-0" />
              Visto por última vez {formatRelativeDate(event.last_seen_at)}
            </p>
            <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className="text-primary-700 font-semibold underline underline-offset-2">
              Ver ubicación en Google Maps
            </a>
          </div>
        </div>

        {event.status === 'found' && (
          <div className="completion-banner flex items-center gap-3 text-white">
            <PartyPopper className="h-6 w-6 shrink-0" />
            <p className="text-sm font-semibold">
              ¡{event.pet_name} ya apareció! Gracias a toda la comunidad por estar pendiente.
            </p>
          </div>
        )}

        {/* Contacto */}
        {isActive && (
          <div className="card flex flex-col gap-2">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide">Contactar</p>
            <div className="grid grid-cols-2 gap-3">
              <a href={`tel:${event.contact_phone}`} className="btn-outline text-sm">
                <Phone className="h-4 w-4" /> Llamar
              </a>
              <a href={waLink} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm">
                <MessageCircle className="h-4 w-4" /> WhatsApp
              </a>
            </div>
          </div>
        )}

        {/* Acciones */}
        {isActive && isReporter && (
          <button onClick={() => markFound()} disabled={markingFound} className="btn-primary bg-emerald-600 hover:bg-emerald-700">
            {markingFound ? <Loader2 className="h-4 w-4 animate-spin" /> : <CheckCircle2 className="h-4 w-4" />}
            Marcar como encontrada
          </button>
        )}

        {isActive && !isReporter && !showSightingForm && (
          <button onClick={() => setShowSightingForm(true)} className="sos-submit-btn">
            <Eye className="h-4 w-4" /> Yo la vi
          </button>
        )}

        {isActive && !isReporter && showSightingForm && (
          <div className="card flex flex-col gap-3">
            <p className="text-sm font-semibold text-foreground">Cuéntanos dónde la viste</p>
            <textarea
              className="input-field min-h-[70px] resize-none"
              placeholder="Ej: cerca al parque, hace 20 minutos, iba hacia el norte..."
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
            <p className="text-[11px] text-muted">Vamos a usar tu ubicación actual para ubicar el avistamiento en el mapa.</p>
            <div className="grid grid-cols-2 gap-3">
              <button onClick={() => setShowSightingForm(false)} className="btn-outline text-sm">Cancelar</button>
              <button onClick={() => sendSighting()} disabled={sendingSighting} className="sos-submit-btn text-sm">
                {sendingSighting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Enviar aviso'}
              </button>
            </div>
          </div>
        )}

        {/* Avistamientos */}
        {(event.sightings?.length ?? 0) > 0 && (
          <div className="flex flex-col gap-2">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide px-1">
              Avistamientos de la comunidad
            </p>
            {event.sightings!.map((s) => (
              <div key={s.id} className="card py-3">
                <div className="flex items-center justify-between">
                  <p className="text-sm font-semibold text-foreground">{s.spotter_name ?? 'Alguien de la comunidad'}</p>
                  <span className="text-[11px] text-muted">{formatDate(s.seen_at)}</span>
                </div>
                {s.note && <p className="text-xs text-muted mt-1">{s.note}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
