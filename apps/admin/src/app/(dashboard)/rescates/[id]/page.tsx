'use client';

import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, CheckCircle2, Trash2, MapPin, Lock, Unlock, User, Phone } from 'lucide-react';
import { toast } from 'sonner';
import { adminRescues } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export default function RescueEventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();

  const { data: event, isLoading } = useQuery({
    queryKey: ['admin-rescue-detail', id],
    queryFn: () => adminRescues.get(id),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['admin-rescue-detail', id] });
    qc.invalidateQueries({ queryKey: ['admin-rescues'] });
  };

  const { mutate: setAnimalStatus } = useMutation({
    mutationFn: ({ animalId, status }: { animalId: string; status: 'unclaimed' | 'reunited' }) =>
      adminRescues.setAnimalStatus(id, animalId, status),
    onSuccess: invalidate,
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: deleteAnimal } = useMutation({
    mutationFn: (animalId: string) => adminRescues.deleteAnimal(id, animalId),
    onSuccess: () => {
      toast.success('Foto eliminada');
      invalidate();
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: toggleEventStatus } = useMutation({
    mutationFn: () => adminRescues.setEventStatus(id, event?.status === 'open' ? 'closed' : 'open'),
    onSuccess: () => {
      toast.success('Estado actualizado');
      invalidate();
    },
  });

  if (isLoading || !event) {
    return <div className="p-6 max-w-4xl mx-auto animate-pulse text-gray-400">Cargando…</div>;
  }

  return (
    <div className="space-y-6 p-6 max-w-4xl mx-auto">
      <button onClick={() => router.push('/rescates')} className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700">
        <ChevronLeft className="h-4 w-4" /> Volver a Rescates
      </button>

      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-gray-900">{event.title}</h1>
            <Badge className={event.status === 'open' ? 'bg-teal-100 text-teal-700' : 'bg-gray-100 text-gray-600'}>
              {event.status === 'open' ? 'Abierto' : 'Cerrado'}
            </Badge>
          </div>
          {event.description && <p className="text-sm text-gray-500 mt-1 max-w-xl">{event.description}</p>}
          <div className="flex items-center gap-3 mt-1.5 flex-wrap text-xs">
            {event.address && (
              <a
                href={`https://www.google.com/maps?q=${event.lat},${event.lng}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-teal-700 font-medium"
              >
                <MapPin className="h-3 w-3" /> {event.address}
              </a>
            )}
            {event.reporter_name && (
              <span className="inline-flex items-center gap-1 text-gray-500">
                <User className="h-3 w-3" /> {event.reporter_name}
              </span>
            )}
            {event.reporter_phone && (
              <a
                href={`https://wa.me/${event.reporter_phone.replace(/\D/g, '')}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-gray-500"
              >
                <Phone className="h-3 w-3" /> {event.reporter_phone}
              </a>
            )}
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={() => toggleEventStatus()} className="gap-1.5 shrink-0">
          {event.status === 'open' ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
          {event.status === 'open' ? 'Cerrar evento' : 'Reabrir evento'}
        </Button>
      </div>

      <div>
        <h2 className="text-sm font-semibold text-gray-900 mb-3">
          {event.animals.length} animalito{event.animals.length === 1 ? '' : 's'} reportados
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {event.animals.map((a) => (
            <Card key={a.id} className="p-0 overflow-hidden">
              <div className="aspect-square relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={a.thumb_url ?? a.photo_url} alt="" className="h-full w-full object-cover" />
                <button
                  onClick={() => deleteAnimal(a.id)}
                  className="absolute top-1.5 right-1.5 h-6 w-6 rounded-full bg-black/50 text-white flex items-center justify-center"
                  title="Quitar foto"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="p-2 space-y-1.5">
                {a.description && <p className="text-xs text-gray-600 line-clamp-2">{a.description}</p>}
                <button
                  onClick={() => setAnimalStatus({ animalId: a.id, status: a.status === 'unclaimed' ? 'reunited' : 'unclaimed' })}
                  className={`w-full inline-flex items-center justify-center gap-1 rounded-md py-1 text-[11px] font-semibold ${
                    a.status === 'reunited' ? 'bg-emerald-100 text-emerald-700' : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  <CheckCircle2 className="h-3 w-3" /> {a.status === 'reunited' ? 'Reunido con su familia' : 'Sin reunir'}
                </button>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}
