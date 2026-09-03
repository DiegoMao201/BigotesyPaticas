'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { MapPin, PawPrint, CalendarDays, User } from 'lucide-react';
import { adminRescues } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default function RescatesPage() {
  const [tab, setTab] = useState<'open' | 'closed'>('open');

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['admin-rescues', tab],
    queryFn: () => adminRescues.list(tab),
  });

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Rescates SOS</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Animales encontrados que los clientes reportan desde el portal. Cierra el evento o marca un animal como
          reunido cuando ya pasó un tiempo prudente.
        </p>
      </div>

      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(['open', 'closed'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'open' ? 'Abiertos' : 'Cerrados'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-4 animate-pulse h-40" />
          ))}
        </div>
      ) : events.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">
          No hay eventos {tab === 'open' ? 'abiertos' : 'cerrados'} todavía. Aparecerán aquí apenas un cliente
          reporte animalitos encontrados desde el portal.
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {events.map((ev) => (
            <Link key={ev.id} href={`/rescates/${ev.id}`}>
              <Card className="p-0 overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col">
                <div className="aspect-video bg-teal-50 relative overflow-hidden">
                  {ev.animals[0]?.thumb_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={ev.animals[0].thumb_url ?? ev.animals[0].photo_url} alt={ev.title} className="h-full w-full object-contain bg-muted" />
                  ) : (
                    <div className="h-full w-full flex items-center justify-center text-teal-300">
                      <PawPrint className="h-8 w-8" />
                    </div>
                  )}
                  <Badge className="absolute top-2 left-2 bg-white/90 text-teal-800">
                    🐾 {ev.animal_count} {ev.unclaimed_count > 0 && ev.unclaimed_count < ev.animal_count ? `(${ev.unclaimed_count} sin reunir)` : ''}
                  </Badge>
                </div>
                <div className="p-3 flex-1">
                  <p className="font-semibold text-sm text-gray-900 truncate">{ev.title}</p>
                  <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 flex-wrap">
                    <span className="inline-flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {formatAgo(ev.found_at)}</span>
                    {ev.address && <span className="inline-flex items-center gap-1 truncate"><MapPin className="h-3 w-3 shrink-0" /> {ev.address}</span>}
                  </div>
                  {ev.reporter_name && (
                    <p className="inline-flex items-center gap-1 text-xs text-gray-400 mt-1">
                      <User className="h-3 w-3" /> Reportado por {ev.reporter_name}
                    </p>
                  )}
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
