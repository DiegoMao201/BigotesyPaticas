'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  ArrowLeft, Phone, MessageCircle, MapPin, Star, Navigation, Calendar, Loader2, CheckCircle2, X,
} from 'lucide-react';
import { partners, type PartnerType, type PartnerService } from '@/lib/api';
import { formatCOP, whatsappLink } from '@/lib/utils';
import { loadMapsScript } from '@/lib/maps';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

const PARTNER_EMOJI: Record<PartnerType, string> = {
  vet: '🩺',
  walker: '🐕',
  shelter: '🏠',
  groomer: '✂️',
};

const PARTNER_TYPE_LABEL: Record<PartnerType, string> = {
  vet: 'Veterinaria',
  walker: 'Paseador',
  shelter: 'Refugio',
  groomer: 'Peluquería',
};

const CATEGORY_LABEL: Record<string, string> = {
  vacunacion: 'Vacunación',
  consulta: 'Consulta',
  esterilizacion: 'Esterilización',
  paseo_30min: 'Paseo 30 min',
  paseo_60min: 'Paseo 60 min',
  bano: 'Baño',
  corte: 'Corte',
};

function formatPrice(price: number | null, priceType: 'fixed' | 'from' | 'quote'): string {
  if (priceType === 'quote' || price == null) return 'Cotización';
  if (priceType === 'from') return `Desde ${formatCOP(price)}`;
  return formatCOP(price);
}

function todayISO() {
  return new Date().toISOString().slice(0, 10);
}

/** Mapa de un solo marcador — ubicación del aliado. */
function PartnerLocationMap({ lat, lng, name }: { lat: number; lng: number; name: string }) {
  const mapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!KEY || !mapRef.current) return;
    const el = mapRef.current;
    loadMapsScript(KEY, () => {
      const center = { lat, lng };
      const map = new window.google.maps.Map(el, {
        center,
        zoom: 15,
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false,
        zoomControl: false,
        styles: [{ featureType: 'poi', elementType: 'labels', stylers: [{ visibility: 'off' }] }],
      });
      new window.google.maps.Marker({ position: center, map, title: name, animation: window.google.maps.Animation.DROP });
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lat, lng]);

  if (!KEY) return null;
  return <div ref={mapRef} className="w-full rounded-xl overflow-hidden" style={{ height: 160 }} />;
}

/** Panel de agendamiento: elige fecha, ve franjas libres y confirma. */
function BookingPanel({ slug, service, onClose, onBooked }: { slug: string; service: PartnerService; onClose: () => void; onBooked: () => void }) {
  const [date, setDate] = useState(todayISO());

  const { data: availability, isLoading } = useQuery({
    queryKey: ['partner-availability', slug, service.id, date],
    queryFn: () => partners.availability(slug, service.id, date),
  });

  const bookMut = useMutation({
    mutationFn: (time: string) =>
      partners.book(slug, {
        service_id: service.id,
        scheduled_at: `${date}T${time}:00`,
      }),
    onSuccess: () => {
      toast.success('¡Reserva enviada! Te avisaremos cuando el aliado la confirme.');
      onBooked();
    },
    onError: (e: Error) => toast.error(e.message || 'No se pudo agendar'),
  });

  return (
    <div className="card flex flex-col gap-3 border-2 border-primary-200">
      <div className="flex items-center justify-between">
        <p className="font-display font-bold text-foreground">Agendar: {service.name}</p>
        <button onClick={onClose} className="text-muted hover:text-foreground"><X className="h-4 w-4" /></button>
      </div>

      <input
        type="date"
        className="input-field"
        value={date}
        min={todayISO()}
        onChange={(e) => setDate(e.target.value)}
      />

      {isLoading && <LoadingSpinner />}

      {!isLoading && availability && availability.slots.length === 0 && (
        <p className="text-sm text-muted text-center py-4">Este aliado no tiene horarios configurados para este día.</p>
      )}

      {!isLoading && availability && availability.slots.length > 0 && (
        <div className="grid grid-cols-4 gap-2">
          {availability.slots.map((s) => (
            <button
              key={s.time}
              disabled={!s.available || bookMut.isPending}
              onClick={() => bookMut.mutate(s.time)}
              className={
                'rounded-lg py-2 text-xs font-semibold transition-all ' +
                (s.available
                  ? 'bg-primary-50 text-primary-800 hover:bg-primary-700 hover:text-white'
                  : 'bg-gray-100 text-gray-300 line-through cursor-not-allowed')
              }
            >
              {s.time}
            </button>
          ))}
        </div>
      )}

      {bookMut.isPending && (
        <p className="text-xs text-muted flex items-center gap-1.5 justify-center">
          <Loader2 className="h-3 w-3 animate-spin" /> Agendando…
        </p>
      )}
    </div>
  );
}

export default function PartnerDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const [bookingService, setBookingService] = useState<PartnerService | null>(null);
  const [justBooked, setJustBooked] = useState(false);

  const { data: partner, isLoading } = useQuery({
    queryKey: ['partner-detail', slug],
    queryFn: () => partners.get(slug),
  });

  const { data: services } = useQuery({
    queryKey: ['partner-services', slug],
    queryFn: () => partners.services(slug),
    enabled: !!partner,
  });

  if (isLoading) return <LoadingSpinner />;
  if (!partner) return null;

  const mapsUrl =
    partner.lat != null && partner.lng != null
      ? `https://www.google.com/maps/dir/?api=1&destination=${partner.lat},${partner.lng}`
      : null;
  const waLink = whatsappLink(
    `Hola, vi tu perfil en Bigotes y Paticas y quiero agendar un servicio.`
  );

  function handleBooked() {
    setBookingService(null);
    setJustBooked(true);
    qc.invalidateQueries({ queryKey: ['my-bookings'] });
  }

  return (
    <div className="flex flex-col gap-5 pb-8">
      <div className="partners-hero px-4 pt-6 pb-6">
        <div className="flex items-center gap-3">
          <button onClick={() => router.back()} className="p-2 -ml-2 rounded-xl hover:bg-white/10 text-white">
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-display text-lg font-bold text-white truncate">{partner.business_name}</h1>
        </div>
      </div>

      <div className="px-4 flex flex-col gap-4 -mt-10">
        {justBooked && (
          <div className="completion-banner flex items-center gap-3 text-white">
            <CheckCircle2 className="h-6 w-6 shrink-0" />
            <p className="text-sm font-semibold">
              ¡Listo! Tu reserva quedó pendiente de confirmación. Revísala en tus citas.
            </p>
          </div>
        )}

        {/* Info principal */}
        <div className="card flex flex-col gap-3">
          <div className="flex gap-3">
            <div className="h-20 w-20 rounded-2xl shrink-0 overflow-hidden bg-[#E1F5EE] flex items-center justify-center text-4xl">
              {partner.logo_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={partner.logo_url} alt={partner.business_name} className="h-full w-full object-cover" />
              ) : (
                PARTNER_EMOJI[partner.partner_type]
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="font-display text-xl font-bold text-foreground">{partner.business_name}</h2>
                {partner.verified && <span className="partner-badge">✅ Verificado</span>}
              </div>
              <p className="text-sm text-muted">{PARTNER_TYPE_LABEL[partner.partner_type]}</p>
              {partner.rating_count > 0 ? (
                <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-600 mt-1">
                  <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                  {partner.rating_avg.toFixed(1)} ({partner.rating_count} reseñas)
                </span>
              ) : (
                <p className="text-xs text-muted mt-1">Sin reseñas todavía</p>
              )}
            </div>
          </div>

          {partner.bio && <p className="text-sm text-foreground/80 leading-relaxed">{partner.bio}</p>}

          {partner.lat != null && partner.lng != null && (
            <PartnerLocationMap lat={partner.lat} lng={partner.lng} name={partner.business_name} />
          )}

          <div className="flex flex-col gap-1.5 text-xs text-muted pt-1 border-t border-border">
            {partner.address && (
              <p className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 shrink-0" />
                {partner.address} · {partner.city}
              </p>
            )}
            {mapsUrl && (
              <a
                href={mapsUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-700 font-semibold inline-flex items-center gap-1 underline-offset-2 hover:underline"
              >
                <Navigation className="h-3.5 w-3.5" /> Cómo llegar
              </a>
            )}
          </div>
        </div>

        {/* Contacto */}
        <div className="card flex flex-col gap-2">
          <p className="text-xs font-semibold text-muted uppercase tracking-wide">Contactar</p>
          <div className="grid grid-cols-2 gap-3">
            {partner.phone ? (
              <a href={`tel:${partner.phone}`} className="btn-outline text-sm">
                <Phone className="h-4 w-4" /> Llamar
              </a>
            ) : (
              <span />
            )}
            <a href={waLink} target="_blank" rel="noopener noreferrer" className="btn-primary text-sm">
              <MessageCircle className="h-4 w-4" /> WhatsApp
            </a>
          </div>
        </div>

        {/* Servicios */}
        {services && services.length > 0 && (
          <div className="flex flex-col gap-3">
            <p className="text-xs font-semibold text-muted uppercase tracking-wide px-1">Servicios</p>
            {services.map((s) => (
              <div key={s.id} className="flex flex-col gap-2">
                <div className="card flex items-center justify-between gap-3 py-3">
                  <div className="min-w-0">
                    <p className="font-semibold text-foreground truncate">{s.name}</p>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-[10px] font-bold uppercase tracking-wide text-primary-700 bg-primary-50 px-2 py-0.5 rounded-full">
                        {CATEGORY_LABEL[s.category] ?? s.category}
                      </span>
                      {s.duration_min && <span className="text-[11px] text-muted">· {s.duration_min} min</span>}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1.5 shrink-0">
                    <p className="font-display font-bold text-foreground">{formatPrice(s.price, s.price_type)}</p>
                    <button
                      onClick={() => setBookingService(bookingService?.id === s.id ? null : s)}
                      className="text-xs font-semibold text-white bg-primary-700 hover:bg-primary-800 rounded-lg px-3 py-1.5 inline-flex items-center gap-1"
                    >
                      <Calendar className="h-3 w-3" /> Agendar
                    </button>
                  </div>
                </div>
                {bookingService?.id === s.id && (
                  <BookingPanel slug={slug} service={s} onClose={() => setBookingService(null)} onBooked={handleBooked} />
                )}
              </div>
            ))}
            <p className="text-xs text-muted px-1">
              ¿Prefieres coordinar directo? Escríbele por WhatsApp desde el botón de arriba.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
