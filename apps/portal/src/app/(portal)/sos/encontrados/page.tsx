'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { PawPrint, MapPin, ChevronLeft, ImageOff, Plus, AlertTriangle } from 'lucide-react';
import { rescues } from '@/lib/api';
import { formatRelativeDate } from '@/lib/utils';
import { useGeolocation } from '@/hooks/useGeolocation';
import { LoadingSpinner } from '@/components/ui/loading-spinner';
import { RescuesMap } from '@/components/maps/RescuesMap';

export default function RescuedAnimalsPage() {
  const { coords, getCurrentPosition } = useGeolocation();

  useEffect(() => {
    getCurrentPosition().catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data: events, isLoading, isError, refetch } = useQuery({
    queryKey: ['rescues-list', coords?.lat, coords?.lng],
    queryFn: () => rescues.list(coords ? { lat: coords.lat, lng: coords.lng } : undefined),
  });

  return (
    <div className="flex flex-col gap-5 pb-4">
      {/* Hero */}
      <div className="sos-hero px-4 pt-6 pb-8" style={{ background: 'linear-gradient(145deg, #2fc4a8 0%, #187f77 55%, #085041 100%)', boxShadow: '0 8px 24px rgba(24,127,119,0.28)' }}>
        <Link href="/sos" className="inline-flex items-center gap-1 text-white/80 text-xs font-semibold mb-2">
          <ChevronLeft className="h-3.5 w-3.5" /> Volver a SOS
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white/80 text-xs font-semibold uppercase tracking-wide">Comunidad Bigotes y Paticas</p>
            <h1 className="font-display text-2xl font-extrabold text-white mt-0.5">Animalitos Encontrados</h1>
          </div>
          <div className="h-14 w-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
            <PawPrint className="h-7 w-7 text-white" strokeWidth={2.2} />
          </div>
        </div>
        <p className="text-white/90 text-sm mt-3 leading-relaxed">
          Animales rescatados que están a salvo en un refugio o albergue, esperando a que su familia los reconozca.
        </p>
        <Link
          href="/sos/encontrados/reportar"
          className="mt-4 inline-flex items-center gap-2 rounded-xl bg-white px-5 py-3 text-sm font-bold text-[#187f77] shadow-lg active:scale-95 transition-transform"
        >
          <Plus className="h-4 w-4" /> Reportar animalito encontrado
        </Link>
      </div>

      <div className="px-4 flex flex-col gap-4">
        {isLoading && <LoadingSpinner />}

        {isError && (
          <div className="card border-amber-300 bg-amber-50 flex flex-col items-center gap-2 py-6 text-center">
            <AlertTriangle className="h-6 w-6 text-amber-600" />
            <p className="text-sm text-amber-800">No pudimos cargar los animalitos encontrados</p>
            <button onClick={() => refetch()} className="btn-outline py-2 px-4 text-xs">
              Reintentar
            </button>
          </div>
        )}

        {!isLoading && !isError && events && events.length > 0 && (
          <RescuesMap events={events} userLocation={coords} height={200} />
        )}

        {!isLoading && !isError && events?.length === 0 && (
          <div className="card flex flex-col items-center gap-2 py-12 text-center">
            <span className="text-4xl">🏠</span>
            <p className="font-semibold text-foreground">No hay animalitos encontrados por ahora</p>
            <p className="text-xs text-muted">¿Encontraste alguno? Sé el primero en reportarlo</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {events?.map((ev, i) => (
            <motion.div key={ev.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
              <Link href={`/sos/encontrados/${ev.id}`} className="card flex flex-col p-0 overflow-hidden hover:shadow-card-hover transition-shadow">
                <div className="aspect-square bg-[#E6F5F1] relative overflow-hidden">
                  {ev.cover_thumb_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={ev.cover_thumb_url} alt={ev.title} className="h-full w-full object-cover" />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-emerald-700/40">
                      <ImageOff className="h-8 w-8" />
                    </div>
                  )}
                  <span className="absolute top-2 left-2 inline-flex items-center gap-1 rounded-full bg-white/90 backdrop-blur px-2 py-0.5 text-[10px] font-bold text-emerald-800">
                    🐾 {ev.animal_count}
                  </span>
                </div>
                <div className="p-2.5">
                  <p className="font-display font-bold text-sm text-foreground leading-tight line-clamp-1">{ev.title}</p>
                  <div className="flex items-center gap-2 mt-1 flex-wrap">
                    {ev.distance_km != null && (
                      <span className="inline-flex items-center gap-0.5 text-[10px] text-muted">
                        <MapPin className="h-2.5 w-2.5" /> {ev.distance_km.toFixed(1)} km
                      </span>
                    )}
                    <span className="text-[10px] text-muted">{formatRelativeDate(ev.found_at)}</span>
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
