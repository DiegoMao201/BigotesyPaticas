'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, MapPin, LocateFixed, ExternalLink, PawPrint, CalendarDays } from 'lucide-react';
import { toast } from 'sonner';
import { adminRescues } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const days = Math.floor(diffMs / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default function RescatesPage() {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'open' | 'closed'>('open');
  const [showCreate, setShowCreate] = useState(false);

  const { data: events = [], isLoading } = useQuery({
    queryKey: ['admin-rescues', tab],
    queryFn: () => adminRescues.list(tab),
  });

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Rescates SOS</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Animales encontrados/rescatados, agrupados por lugar — para que la gente reconozca a su mascota.
          </p>
        </div>
        <Button onClick={() => setShowCreate(true)} className="gap-1.5">
          <Plus className="h-4 w-4" /> Nuevo evento
        </Button>
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
          No hay eventos {tab === 'open' ? 'abiertos' : 'cerrados'} todavía.
        </Card>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {events.map((ev) => (
            <Link key={ev.id} href={`/rescates/${ev.id}`}>
              <Card className="p-0 overflow-hidden hover:shadow-md transition-shadow h-full flex flex-col">
                <div className="aspect-video bg-teal-50 relative overflow-hidden">
                  {ev.cover_thumb_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={ev.cover_thumb_url} alt={ev.title} className="h-full w-full object-cover" />
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
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}

      <CreateRescueDialog
        open={showCreate}
        onClose={() => setShowCreate(false)}
        onCreated={(id) => {
          setShowCreate(false);
          qc.invalidateQueries({ queryKey: ['admin-rescues'] });
          window.location.href = `/rescates/${id}`;
        }}
      />
    </div>
  );
}

function CreateRescueDialog({ open, onClose, onCreated }: { open: boolean; onClose: () => void; onCreated: (id: string) => void }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [address, setAddress] = useState('');
  const [contactPhone, setContactPhone] = useState('');
  const [lat, setLat] = useState('');
  const [lng, setLng] = useState('');
  const [foundAt, setFoundAt] = useState('');
  const [locating, setLocating] = useState(false);

  const { mutate: create, isPending } = useMutation({
    mutationFn: () =>
      adminRescues.create({
        title,
        description: description || undefined,
        address: address || undefined,
        lat: parseFloat(lat),
        lng: parseFloat(lng),
        found_at: foundAt ? new Date(foundAt).toISOString() : undefined,
        contact_phone: contactPhone || undefined,
      }),
    onSuccess: (ev) => {
      toast.success('Evento creado');
      onCreated(ev.id);
      setTitle(''); setDescription(''); setAddress(''); setContactPhone(''); setLat(''); setLng(''); setFoundAt('');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function useMyLocation() {
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLng(pos.coords.longitude.toFixed(6));
        setLocating(false);
      },
      () => {
        toast.error('No se pudo obtener tu ubicación');
        setLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10_000 }
    );
  }

  const canSubmit = title.trim().length > 0 && lat && lng && !isNaN(parseFloat(lat)) && !isNaN(parseFloat(lng));
  const mapsPreviewLink = lat && lng ? `https://www.google.com/maps?q=${lat},${lng}` : null;

  return (
    <Dialog open={open} onClose={onClose} title="Nuevo evento de rescate" description="Un lugar donde se encontraron uno o más animales">
      <DialogBody className="space-y-3">
        <div>
          <label className="text-xs font-medium text-gray-600">Título *</label>
          <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder='Ej: "10 cachorros rescatados en Cuba"' />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600">Descripción</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            className="flex w-full rounded-lg border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            placeholder="Qué pasó, en qué condiciones están, etc. (opcional)"
          />
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600">Dirección / referencia</label>
          <Input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Ej: Barrio Cuba, cerca al parque" />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium text-gray-600">Fecha en que se encontraron</label>
            <Input type="datetime-local" value={foundAt} onChange={(e) => setFoundAt(e.target.value)} />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-600">Teléfono de contacto</label>
            <Input value={contactPhone} onChange={(e) => setContactPhone(e.target.value)} placeholder="WhatsApp" />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium text-gray-600 flex items-center justify-between">
            Ubicación *
            <button type="button" onClick={useMyLocation} disabled={locating} className="text-teal-700 inline-flex items-center gap-1 text-xs font-semibold">
              <LocateFixed className="h-3 w-3" /> {locating ? 'Ubicando…' : 'Usar mi ubicación'}
            </button>
          </label>
          <div className="grid grid-cols-2 gap-3 mt-1">
            <Input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="Latitud" />
            <Input value={lng} onChange={(e) => setLng(e.target.value)} placeholder="Longitud" />
          </div>
          {mapsPreviewLink && (
            <a href={mapsPreviewLink} target="_blank" rel="noopener noreferrer" className="mt-1 inline-flex items-center gap-1 text-xs text-teal-700 font-medium">
              <ExternalLink className="h-3 w-3" /> Verificar en Google Maps
            </a>
          )}
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancelar</Button>
        <Button onClick={() => create()} disabled={!canSubmit || isPending}>
          {isPending ? 'Creando…' : 'Crear y subir fotos'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
