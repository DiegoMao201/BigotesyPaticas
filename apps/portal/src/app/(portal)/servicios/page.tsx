'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Handshake, Star, MapPin, CalendarCheck } from 'lucide-react';
import { partners, type PartnerType } from '@/lib/api';
import { useGeolocation } from '@/hooks/useGeolocation';
import { PartnersMap } from '@/components/maps/PartnersMap';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

const TYPE_FILTERS: { value: PartnerType | 'all'; label: string; emoji: string }[] = [
  { value: 'all', label: 'Todos', emoji: '🐾' },
  { value: 'vet', label: 'Veterinarias', emoji: '🩺' },
  { value: 'walker', label: 'Paseadores', emoji: '🐕' },
  { value: 'shelter', label: 'Refugios', emoji: '🏠' },
  { value: 'groomer', label: 'Peluquerías', emoji: '✂️' },
];

const PARTNER_EMOJI: Record<PartnerType, string> = {
  vet: '🩺',
  walker: '🐕',
  shelter: '🏠',
  groomer: '✂️',
};

export default function ServiciosListPage() {
  const [type, setType] = useState<PartnerType | 'all'>('all');
  const { coords, getCurrentPosition } = useGeolocation();

  useEffect(() => {
    getCurrentPosition().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['partners', type, coords?.lat, coords?.lng],
    queryFn: () =>
      partners.list({
        type: type === 'all' ? undefined : type,
        ...(coords ? { lat: coords.lat, lng: coords.lng } : {}),
      }),
  });

  return (
    <div className="flex flex-col gap-5 pb-4">
      {/* Hero */}
      <div className="partners-hero px-4 pt-6 pb-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white/80 text-xs font-semibold uppercase tracking-wide">
              Comunidad Bigotes y Paticas
            </p>
            <h1 className="font-display text-2xl font-extrabold text-white mt-0.5">
              Aliados y Servicios
            </h1>
          </div>
          <div className="h-14 w-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
            <Handshake className="h-7 w-7 text-white" strokeWidth={2.2} />
          </div>
        </div>
        <p className="text-white/90 text-sm mt-3 leading-relaxed">
          Veterinarias, paseadores, refugios y peluquerías de confianza cerca de ti.
        </p>
        <Link
          href="/servicios/mis-reservas"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white/15 backdrop-blur px-4 py-2.5 text-sm font-semibold text-white active:scale-95 transition-transform"
        >
          <CalendarCheck className="h-4 w-4" /> Mis reservas
        </Link>
      </div>

      <div className="px-4 flex flex-col gap-4">
        {/* Filtros por tipo */}
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {TYPE_FILTERS.map((f) => (
            <button
              key={f.value}
              onClick={() => setType(f.value)}
              className={
                'shrink-0 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ' +
                (type === f.value
                  ? 'bg-primary-700 border-primary-700 text-white'
                  : 'border-border text-muted bg-white')
              }
            >
              {f.emoji} {f.label}
            </button>
          ))}
        </div>

        {!isLoading && data && data.items.length > 0 && (
          <PartnersMap partners={data.items} userLocation={coords} />
        )}

        {isLoading && <LoadingSpinner />}

        {!isLoading && data?.items.length === 0 && (
          <div className="card flex flex-col items-center gap-2 py-12 text-center">
            <span className="text-4xl">🤝</span>
            <p className="font-semibold text-foreground">Aún no hay aliados en tu zona</p>
            <p className="text-xs text-muted">¡Pronto sumamos más veterinarias, paseadores y refugios!</p>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {data?.items.map((p, i) => (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link
                href={`/servicios/${p.slug}`}
                className="card flex gap-3 py-3 hover:shadow-card-hover transition-shadow"
              >
                <div className="h-16 w-16 rounded-2xl shrink-0 overflow-hidden bg-[#E1F5EE] flex items-center justify-center text-3xl">
                  {p.logo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.logo_url} alt={p.business_name} className="h-full w-full object-cover" />
                  ) : (
                    PARTNER_EMOJI[p.partner_type]
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="font-display font-bold text-foreground truncate">{p.business_name}</p>
                    {p.verified && <span className="partner-badge shrink-0">✅ Verificado</span>}
                  </div>
                  <p className="text-xs text-muted capitalize inline-flex items-center gap-0.5">
                    <MapPin className="h-3 w-3" /> {p.city}
                  </p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {p.rating_count > 0 ? (
                      <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-amber-600">
                        <Star className="h-3 w-3 fill-amber-400 text-amber-400" /> {p.rating_avg.toFixed(1)} ({p.rating_count})
                      </span>
                    ) : (
                      <span className="text-[11px] text-muted">Sin reseñas todavía</span>
                    )}
                  </div>
                </div>
              </Link>
            </motion.div>
          ))}
        </div>
      </div>
    </div>
  );
}
