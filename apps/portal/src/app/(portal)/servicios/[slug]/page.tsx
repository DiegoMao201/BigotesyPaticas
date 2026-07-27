'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { ArrowLeft, Phone, MessageCircle, MapPin, Star } from 'lucide-react';
import { partners, type PartnerType } from '@/lib/api';
import { formatCOP, whatsappLink } from '@/lib/utils';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

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

export default function PartnerDetailPage() {
  const { slug } = useParams<{ slug: string }>();
  const router = useRouter();

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
      ? `https://www.google.com/maps?q=${partner.lat},${partner.lng}`
      : null;
  const waLink = whatsappLink(
    `Hola, vi tu perfil en Bigotes y Paticas y quiero agendar un servicio.`
  );

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

          <div className="flex flex-col gap-1.5 text-xs text-muted pt-1 border-t border-border">
            {partner.address && (
              <p className="flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 shrink-0" />
                {partner.address} · {partner.city}
              </p>
            )}
            {mapsUrl && (
              <a href={mapsUrl} target="_blank" rel="noopener noreferrer" className="text-primary-700 font-semibold underline underline-offset-2">
                Ver ubicación en Google Maps
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
              <div key={s.id} className="card flex items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="font-semibold text-foreground truncate">{s.name}</p>
                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    <span className="text-[10px] font-bold uppercase tracking-wide text-primary-700 bg-primary-50 px-2 py-0.5 rounded-full">
                      {CATEGORY_LABEL[s.category] ?? s.category}
                    </span>
                    {s.duration_min && <span className="text-[11px] text-muted">· {s.duration_min} min</span>}
                  </div>
                </div>
                <p className="font-display font-bold text-foreground shrink-0">
                  {formatPrice(s.price, s.price_type)}
                </p>
              </div>
            ))}
            <p className="text-xs text-muted px-1">
              Agenda directo por WhatsApp mientras habilitamos el calendario en línea.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
