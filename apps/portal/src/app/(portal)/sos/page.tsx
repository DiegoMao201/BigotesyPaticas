'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { PawPrint, MapPin, Gift, Plus, RefreshCw, LocateFixed } from 'lucide-react';
import { sos, portalLocation } from '@/lib/api';
import { getSpeciesEmoji, formatRelativeDate } from '@/lib/utils';
import { useGeolocation } from '@/hooks/useGeolocation';
import { LoadingSpinner } from '@/components/ui/loading-spinner';

export default function SOSListPage() {
  const { coords, error, loading, getCurrentPosition } = useGeolocation();
  const [radiusKm, setRadiusKm] = useState(15);

  useEffect(() => {
    getCurrentPosition()
      .then((c) => {
        portalLocation.update(c.lat, c.lng).catch(() => {});
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: events, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['sos-nearby', coords?.lat, coords?.lng, radiusKm],
    queryFn: () => sos.nearby(coords!.lat, coords!.lng, radiusKm),
    enabled: !!coords,
  });

  return (
    <div className="flex flex-col gap-5 pb-4">
      {/* Hero */}
      <div className="sos-hero px-4 pt-6 pb-8">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white/80 text-xs font-semibold uppercase tracking-wide">Comunidad Bigotes y Paticas</p>
            <h1 className="font-display text-2xl font-extrabold text-white mt-0.5">SOS Mascotas Perdidas</h1>
          </div>
          <div className="h-14 w-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
            <PawPrint className="h-7 w-7 text-white" strokeWidth={2.2} />
          </div>
        </div>
        <p className="text-white/90 text-sm mt-3 leading-relaxed">
          Toda la comunidad ayuda a encontrar mascotas perdidas cerca de ti. Si ves una, avísale a quien la reportó.
        </p>
        <div className="flex items-center gap-2 mt-4 flex-wrap">
          <Link
            href="/sos/new"
            className="inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-[#e8433a] shadow-lg active:scale-95 transition-transform"
          >
            <Plus className="h-4 w-4" /> Reportar mascota perdida
          </Link>
          <Link
            href="/sos/encontrados"
            className="inline-flex items-center gap-2 rounded-xl bg-white/15 backdrop-blur px-5 py-3 text-sm font-bold text-white active:scale-95 transition-transform"
          >
            🏠 Ver animalitos encontrados
          </Link>
          <a
            href="https://bigotesypaticas.com/finales-felices"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 rounded-xl bg-white/15 backdrop-blur px-5 py-3 text-sm font-bold text-white active:scale-95 transition-transform"
          >
            🎉 Finales felices
          </a>
        </div>
      </div>

      <div className="px-4 flex flex-col gap-4">
        {/* Radio + refresh */}
        <div className="flex items-center justify-between">
          <div className="flex gap-1.5">
            {[5, 15, 30, 50].map((km) => (
              <button
                key={km}
                onClick={() => setRadiusKm(km)}
                className={
                  'px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ' +
                  (radiusKm === km
                    ? 'bg-[#e8433a] border-[#e8433a] text-white'
                    : 'border-border text-muted bg-white')
                }
              >
                {km} km
              </button>
            ))}
          </div>
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="p-2 rounded-xl border border-border bg-white text-muted"
          >
            <RefreshCw className={'h-4 w-4' + (isFetching ? ' animate-spin' : '')} />
          </button>
        </div>

        {/* Estado de ubicación */}
        {!coords && !error && (
          <div className="card flex flex-col items-center gap-3 py-10 text-center">
            <LocateFixed className="h-8 w-8 text-muted" />
            <p className="text-sm text-muted">
              {loading ? 'Obteniendo tu ubicación…' : 'Necesitamos tu ubicación para mostrarte reportes cerca de ti'}
            </p>
            {!loading && (
              <button onClick={() => getCurrentPosition()} className="btn-primary py-2 px-4 text-xs">
                Activar ubicación
              </button>
            )}
          </div>
        )}

        {error && (
          <div className="card border-amber-300 bg-amber-50 flex flex-col items-center gap-2 py-6 text-center">
            <p className="text-sm text-amber-800">{error}</p>
            <button onClick={() => getCurrentPosition()} className="btn-outline py-2 px-4 text-xs">
              Reintentar
            </button>
          </div>
        )}

        {coords && isLoading && <LoadingSpinner />}

        {coords && !isLoading && events?.length === 0 && (
          <div className="card flex flex-col items-center gap-2 py-12 text-center">
            <span className="text-4xl">🎉</span>
            <p className="font-semibold text-foreground">No hay mascotas perdidas cerca de ti</p>
            <p className="text-xs text-muted">Te avisaremos si alguien reporta una en tu zona</p>
          </div>
        )}

        <div className="flex flex-col gap-3">
          {events?.map((ev, i) => (
            <motion.div key={ev.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Link href={`/sos/${ev.id}`} className="card flex gap-3 py-3 hover:shadow-card-hover transition-shadow">
                <div className="h-16 w-16 rounded-2xl shrink-0 overflow-hidden bg-[#FDEEE9] flex items-center justify-center text-3xl">
                  {ev.photos[0] ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={ev.photos[0]} alt={ev.pet_name} className="h-full w-full object-contain bg-muted" />
                  ) : (
                    getSpeciesEmoji(ev.species)
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <p className="font-display font-bold text-foreground truncate">{ev.pet_name}</p>
                    <span className="shrink-0 text-[10px] font-bold uppercase tracking-wide text-[#e8433a] bg-[#FDEEE9] px-2 py-0.5 rounded-full">
                      Perdido
                    </span>
                  </div>
                  <p className="text-xs text-muted capitalize">
                    {ev.species}
                    {ev.breed ? ` • ${ev.breed}` : ''} • {ev.color}
                  </p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {ev.distance_km != null && (
                      <span className="inline-flex items-center gap-0.5 text-[11px] text-muted">
                        <MapPin className="h-3 w-3" /> {ev.distance_km.toFixed(1)} km
                      </span>
                    )}
                    <span className="text-[11px] text-muted">{formatRelativeDate(ev.created_at)}</span>
                    {ev.reward != null && ev.reward > 0 && (
                      <span className="inline-flex items-center gap-0.5 text-[11px] font-semibold text-emerald-700">
                        <Gift className="h-3 w-3" /> Recompensa
                      </span>
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
