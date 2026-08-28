'use client';

import { useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ChevronLeft, MapPin, Phone, CalendarDays, CheckCircle2 } from 'lucide-react';
import { rescues } from '@/lib/api';
import { formatRelativeDate } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { PhotoLightbox } from '@/components/PhotoLightbox';

export default function RescueEventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  const { data: event, isLoading } = useQuery({
    queryKey: ['rescue-detail', id],
    queryFn: () => rescues.get(id),
  });

  if (isLoading) return <LoadingSpinner />;
  if (!event) return null;

  const photos = event.animals.map((a) => ({ url: a.photo_url, caption: a.description }));
  const waLink = event.contact_phone
    ? `https://wa.me/${event.contact_phone.replace(/\D/g, '').startsWith('57') ? event.contact_phone.replace(/\D/g, '') : `57${event.contact_phone.replace(/\D/g, '')}`}?text=${encodeURIComponent(`Hola, vi en el portal el reporte "${event.title}" y creo que uno de esos animalitos podría ser mío. ¿Me pueden dar más info?`)}`
    : null;
  const mapsLink = `https://www.google.com/maps?q=${event.lat},${event.lng}`;

  return (
    <div className="flex flex-col gap-5 pb-8">
      <div
        className="px-4 pt-6 pb-6"
        style={{
          background: 'linear-gradient(145deg, #2fc4a8 0%, #187f77 55%, #085041 100%)',
          borderRadius: '0 0 28px 28px',
          boxShadow: '0 8px 24px rgba(24,127,119,0.28)',
        }}
      >
        <Link href="/sos/encontrados" className="inline-flex items-center gap-1 text-white/80 text-xs font-semibold mb-3">
          <ChevronLeft className="h-3.5 w-3.5" /> Volver
        </Link>
        <h1 className="font-display text-xl font-extrabold text-white leading-tight">{event.title}</h1>
        {event.description && <p className="text-white/90 text-sm mt-2 leading-relaxed">{event.description}</p>}
        <div className="flex items-center gap-3 mt-3 flex-wrap">
          <span className="inline-flex items-center gap-1 rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-semibold text-white">
            🐾 {event.animal_count} animalito{event.animal_count === 1 ? '' : 's'}
          </span>
          <span className="inline-flex items-center gap-1 rounded-full bg-white/15 backdrop-blur px-2.5 py-1 text-[11px] font-semibold text-white">
            <CalendarDays className="h-3 w-3" /> {formatRelativeDate(event.found_at)}
          </span>
        </div>
      </div>

      <div className="px-4 flex flex-col gap-4">
        {event.address && (
          <a href={mapsLink} target="_blank" rel="noopener noreferrer" className="card flex items-center gap-3 py-3 hover:shadow-card-hover transition-shadow">
            <div className="h-10 w-10 rounded-xl bg-[#E6F5F1] flex items-center justify-center shrink-0">
              <MapPin className="h-5 w-5 text-emerald-700" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-foreground truncate">{event.address}</p>
              <p className="text-xs text-muted">Toca para ver la ubicación en el mapa</p>
            </div>
          </a>
        )}

        <div>
          <p className="text-sm font-bold text-foreground mb-2">Fotos de los animalitos</p>
          <div className="grid grid-cols-3 gap-2">
            {event.animals.map((a, i) => (
              <button
                key={a.id}
                onClick={() => setLightboxIndex(i)}
                className="aspect-square rounded-xl overflow-hidden relative bg-[#E6F5F1]"
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={a.thumb_url ?? a.photo_url} alt={a.description ?? 'Animal rescatado'} className="h-full w-full object-cover" />
                {a.status === 'reunited' && (
                  <span className="absolute inset-0 bg-black/50 flex items-center justify-center">
                    <span className="inline-flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[10px] font-bold text-emerald-700">
                      <CheckCircle2 className="h-3 w-3" /> Reunido
                    </span>
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>

        {waLink && (
          <a
            href={waLink}
            target="_blank"
            rel="noopener noreferrer"
            className="btn-primary w-full"
          >
            <Phone className="h-4 w-4" /> Escribir por WhatsApp
          </a>
        )}
      </div>

      {lightboxIndex !== null && (
        <PhotoLightbox
          photos={photos}
          index={lightboxIndex}
          onClose={() => setLightboxIndex(null)}
          onIndexChange={setLightboxIndex}
        />
      )}
    </div>
  );
}
