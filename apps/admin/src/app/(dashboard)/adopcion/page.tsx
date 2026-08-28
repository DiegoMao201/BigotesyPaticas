'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { MapPin, Heart, User, Lock, Unlock, Trash2, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import { adminAdoption } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default function AdoptionModerationPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'open' | 'closed'>('open');
  const [typeFilter, setTypeFilter] = useState<'all' | 'offer' | 'want'>('all');

  const { data: listings = [], isLoading } = useQuery({
    queryKey: ['admin-adoption', tab],
    queryFn: () => adminAdoption.list(tab),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ['admin-adoption'] });

  const { mutate: setStatus } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'open' | 'closed' }) => adminAdoption.setStatus(id, status),
    onSuccess: () => {
      toast.success('Estado actualizado');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: remove } = useMutation({
    mutationFn: (id: string) => adminAdoption.remove(id),
    onSuccess: () => {
      toast.success('Publicación eliminada');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const filtered = typeFilter === 'all' ? listings : listings.filter((l) => l.post_type === typeFilter);

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Foro de Adopción</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Publicaciones de clientes que dan animales en adopción o buscan adoptar, hechas desde el portal.
        </p>
      </div>

      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
          {(['open', 'closed'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                tab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'open' ? 'Abiertas' : 'Cerradas'}
            </button>
          ))}
        </div>
        <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
          {([
            { key: 'all', label: 'Todas' },
            { key: 'offer', label: '🏠 En adopción' },
            { key: 'want', label: '🔍 Buscan adoptar' },
          ] as const).map((t) => (
            <button
              key={t.key}
              onClick={() => setTypeFilter(t.key)}
              className={`px-3 py-2 rounded-lg text-xs font-medium transition-all ${
                typeFilter === t.key ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-4 animate-pulse h-40" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <Card className="p-10 text-center text-gray-500">No hay publicaciones {tab === 'open' ? 'abiertas' : 'cerradas'} todavía.</Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {filtered.map((l) => (
            <Card key={l.id} className="p-0 overflow-hidden flex flex-col">
              <div className="aspect-video bg-teal-50 relative overflow-hidden">
                {l.photos[0] ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={l.photos[0]} alt={l.title} className="h-full w-full object-cover" />
                ) : (
                  <div className="h-full w-full flex items-center justify-center text-teal-300">
                    <Heart className="h-8 w-8" />
                  </div>
                )}
                <Badge className="absolute top-2 left-2 bg-white/90 text-teal-800">
                  {l.post_type === 'offer' ? '🏠 En adopción' : '🔍 Busca adoptar'}
                </Badge>
              </div>
              <div className="p-3 flex-1 flex flex-col gap-1.5">
                <p className="font-semibold text-sm text-gray-900 truncate">{l.title}</p>
                <div className="flex items-center gap-2 text-xs text-gray-500 flex-wrap">
                  <span className="inline-flex items-center gap-1"><CalendarDays className="h-3 w-3" /> {formatAgo(l.created_at)}</span>
                  {l.address && <span className="inline-flex items-center gap-1 truncate"><MapPin className="h-3 w-3 shrink-0" /> {l.address}</span>}
                </div>
                {l.reporter_name && (
                  <p className="inline-flex items-center gap-1 text-xs text-gray-400">
                    <User className="h-3 w-3" /> {l.reporter_name} {l.reporter_phone ? `· ${l.reporter_phone}` : ''}
                  </p>
                )}
                <div className="flex gap-2 mt-auto pt-2">
                  <Button
                    size="sm"
                    variant="outline"
                    className="flex-1 gap-1.5"
                    onClick={() => setStatus({ id: l.id, status: l.status === 'open' ? 'closed' : 'open' })}
                  >
                    {l.status === 'open' ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
                    {l.status === 'open' ? 'Cerrar' : 'Reabrir'}
                  </Button>
                  <Button size="sm" variant="outline" onClick={() => remove(l.id)}>
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
