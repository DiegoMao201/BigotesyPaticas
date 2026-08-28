'use client';

import { useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Upload, X, CheckCircle2, Trash2, MapPin, Lock, Unlock } from 'lucide-react';
import { toast } from 'sonner';
import { adminRescues, type RescueAnimal } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface Draft {
  file: File;
  preview: string;
  description: string;
}

export default function RescueEventDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [drafts, setDrafts] = useState<Draft[]>([]);

  const { data: event, isLoading } = useQuery({
    queryKey: ['admin-rescue-detail', id],
    queryFn: () => adminRescues.get(id),
  });

  const { mutate: upload, isPending: uploading } = useMutation({
    mutationFn: () =>
      adminRescues.uploadAnimals(
        id,
        drafts.map((d) => d.file),
        drafts.map((d) => d.description)
      ),
    onSuccess: (res) => {
      toast.success(`${res.animals.length} foto${res.animals.length === 1 ? '' : 's'} subida${res.animals.length === 1 ? '' : 's'}`);
      drafts.forEach((d) => URL.revokeObjectURL(d.preview));
      setDrafts([]);
      qc.invalidateQueries({ queryKey: ['admin-rescue-detail', id] });
      qc.invalidateQueries({ queryKey: ['admin-rescues'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: updateAnimal } = useMutation({
    mutationFn: ({ animalId, payload }: { animalId: string; payload: { description?: string; status?: RescueAnimal['status'] } }) =>
      adminRescues.updateAnimal(id, animalId, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-rescue-detail', id] }),
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: deleteAnimal } = useMutation({
    mutationFn: (animalId: string) => adminRescues.deleteAnimal(id, animalId),
    onSuccess: () => {
      toast.success('Foto eliminada');
      qc.invalidateQueries({ queryKey: ['admin-rescue-detail', id] });
      qc.invalidateQueries({ queryKey: ['admin-rescues'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const { mutate: toggleEventStatus } = useMutation({
    mutationFn: () => adminRescues.update(id, { status: event?.status === 'open' ? 'closed' : 'open' }),
    onSuccess: () => {
      toast.success('Estado actualizado');
      qc.invalidateQueries({ queryKey: ['admin-rescue-detail', id] });
      qc.invalidateQueries({ queryKey: ['admin-rescues'] });
    },
  });

  function onFilesSelected(files: FileList | null) {
    if (!files) return;
    const next: Draft[] = Array.from(files).map((file) => ({
      file,
      preview: URL.createObjectURL(file),
      description: '',
    }));
    setDrafts((prev) => [...prev, ...next]);
  }

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
          {event.address && (
            <a
              href={`https://www.google.com/maps?q=${event.lat},${event.lng}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-xs text-teal-700 font-medium mt-1"
            >
              <MapPin className="h-3 w-3" /> {event.address}
            </a>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => toggleEventStatus()} className="gap-1.5 shrink-0">
          {event.status === 'open' ? <Lock className="h-3.5 w-3.5" /> : <Unlock className="h-3.5 w-3.5" />}
          {event.status === 'open' ? 'Cerrar evento' : 'Reabrir evento'}
        </Button>
      </div>

      {/* Subir fotos */}
      <Card className="p-4 border-dashed border-2 border-teal-200 bg-teal-50/30">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="hidden"
          onChange={(e) => onFilesSelected(e.target.files)}
        />
        {drafts.length === 0 ? (
          <button
            onClick={() => fileInputRef.current?.click()}
            className="w-full flex flex-col items-center gap-2 py-6 text-teal-700"
          >
            <Upload className="h-6 w-6" />
            <span className="text-sm font-medium">Subir fotos de animalitos (puedes elegir varias a la vez)</span>
          </button>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
              {drafts.map((d, i) => (
                <div key={i} className="relative">
                  <button
                    onClick={() => setDrafts((prev) => prev.filter((_, j) => j !== i))}
                    className="absolute -top-2 -right-2 h-5 w-5 rounded-full bg-red-500 text-white flex items-center justify-center z-10"
                  >
                    <X className="h-3 w-3" />
                  </button>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={d.preview} alt="" className="aspect-square w-full object-cover rounded-lg" />
                  <input
                    value={d.description}
                    onChange={(e) =>
                      setDrafts((prev) => prev.map((p, j) => (j === i ? { ...p, description: e.target.value } : p)))
                    }
                    placeholder="Descripción (opcional)"
                    className="mt-1 w-full text-[11px] rounded border border-gray-200 px-1.5 py-1"
                  />
                </div>
              ))}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="aspect-square rounded-lg border-2 border-dashed border-teal-300 flex items-center justify-center text-teal-500"
              >
                <Upload className="h-5 w-5" />
              </button>
            </div>
            <div className="flex gap-2">
              <Button onClick={() => upload()} disabled={uploading} className="gap-1.5">
                {uploading ? 'Subiendo…' : `Subir ${drafts.length} foto${drafts.length === 1 ? '' : 's'}`}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  drafts.forEach((d) => URL.revokeObjectURL(d.preview));
                  setDrafts([]);
                }}
              >
                Cancelar
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Animales ya subidos */}
      <div>
        <h2 className="text-sm font-semibold text-gray-900 mb-3">
          {event.animals.length} animalito{event.animals.length === 1 ? '' : 's'} en este evento
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
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="p-2 space-y-1.5">
                <textarea
                  defaultValue={a.description ?? ''}
                  onBlur={(e) => {
                    if (e.target.value !== (a.description ?? '')) {
                      updateAnimal({ animalId: a.id, payload: { description: e.target.value } });
                    }
                  }}
                  placeholder="Descripción…"
                  rows={2}
                  className="w-full text-xs rounded border border-gray-200 px-1.5 py-1 resize-none"
                />
                <button
                  onClick={() => updateAnimal({ animalId: a.id, payload: { status: a.status === 'unclaimed' ? 'reunited' : 'unclaimed' } })}
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
