'use client';

import { useRef, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { Camera, ImagePlus, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { pets } from '@/lib/api';

interface PetPhotoUploaderProps {
  petId: string;
  currentPhotoUrl: string | null;
  petName: string;
  accentColor?: string;
}

export function PetPhotoUploader({
  petId,
  currentPhotoUrl,
  petName,
  accentColor = '#187f77',
}: PetPhotoUploaderProps) {
  const qc = useQueryClient();
  const galleryRef = useRef<HTMLInputElement>(null);
  const cameraRef = useRef<HTMLInputElement>(null);
  const [preview, setPreview] = useState<string | null>(null);

  const { mutate: upload, isPending } = useMutation({
    mutationFn: (file: File) => pets.uploadPhoto(petId, file),
    onSuccess: (updated) => {
      qc.invalidateQueries({ queryKey: ['portal-pets'] });
      qc.setQueryData(['portal-pet', petId], updated);
      toast.success('✅ Foto actualizada');
      setPreview(null);
    },
    onError: (err: Error) => toast.error(err.message ?? 'No se pudo subir la foto'),
  });

  function handleFile(file: File | undefined) {
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      toast.error('Selecciona una imagen (JPEG, PNG o WebP)');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error('La imagen no debe superar 5 MB');
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    upload(file);
  }

  const displayPhoto = preview ?? currentPhotoUrl;

  return (
    <div className="flex flex-col gap-4">
      {/* Área principal */}
      <div
        className="rounded-2xl border-2 border-dashed flex flex-col items-center justify-center py-8 gap-3 relative overflow-hidden"
        style={{ borderColor: `${accentColor}60` }}
      >
        {displayPhoto ? (
          <div className="relative h-32 w-32 rounded-2xl overflow-hidden">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={displayPhoto}
              alt={`Foto de ${petName}`}
              className="h-full w-full object-cover"
            />
            {isPending && (
              <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                <Loader2 className="h-8 w-8 text-white animate-spin" />
              </div>
            )}
          </div>
        ) : (
          <motion.div
            animate={{ scale: isPending ? 0.95 : 1 }}
            className="flex flex-col items-center gap-2"
          >
            <div
              className="h-16 w-16 rounded-2xl flex items-center justify-center text-4xl"
              style={{ background: `${accentColor}18` }}
            >
              {isPending ? (
                <Loader2 className="h-8 w-8 animate-spin" style={{ color: accentColor }} />
              ) : '🐾'}
            </div>
            <p className="font-semibold text-foreground text-sm">
              {isPending ? 'Subiendo...' : 'Toca para subir foto'}
            </p>
            <p className="text-muted text-xs">Galería o cámara · máx 5 MB</p>
          </motion.div>
        )}

        {/* inputs hidden */}
        <input
          ref={galleryRef}
          type="file"
          accept="image/*"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
        <input
          ref={cameraRef}
          type="file"
          accept="image/*"
          capture="environment"
          className="hidden"
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>

      {/* Botones */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          disabled={isPending}
          onClick={() => galleryRef.current?.click()}
          className="flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-white text-sm disabled:opacity-60"
          style={{ background: accentColor }}
        >
          <ImagePlus className="h-4 w-4" />
          Galería
        </button>
        <button
          type="button"
          disabled={isPending}
          onClick={() => cameraRef.current?.click()}
          className="flex items-center justify-center gap-2 py-3 rounded-xl font-semibold text-sm border-2 disabled:opacity-60"
          style={{ borderColor: accentColor, color: accentColor }}
        >
          <Camera className="h-4 w-4" />
          Cámara
        </button>
      </div>

      {/* Tip card */}
      <div
        className="rounded-2xl p-4 flex flex-col gap-1.5"
        style={{ background: '#FFF8ED' }}
      >
        <p className="text-amber-800 font-semibold text-xs flex items-center gap-1.5">
          💡 ¿Cómo subo la foto?
        </p>
        <ol className="text-amber-700 text-xs flex flex-col gap-1 pl-1">
          <li>1. Toca &ldquo;Galería&rdquo; para elegir una foto que ya tengas</li>
          <li>2. O toca &ldquo;Cámara&rdquo; para tomarla ahora mismo</li>
          <li>3. La foto se sube automáticamente</li>
        </ol>
        <p className="text-amber-600 text-xs mt-1">
          Usa una foto con buena luz donde se vea bien la carita de {petName} 🐾
        </p>
      </div>
    </div>
  );
}
