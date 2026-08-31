'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { toast } from 'sonner';
import { Loader2, Send, Home, Search, Camera, X } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || '';
const ALLOWED_PHOTO_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);
const MAX_PHOTO_BYTES = 5 * 1024 * 1024;

export function QuickPostForm() {
  const router = useRouter();
  const [postType, setPostType] = useState<'offer' | 'want'>('offer');
  const [name, setName] = useState('');
  const [phone, setPhone] = useState('');
  const [message, setMessage] = useState('');
  const [accepted, setAccepted] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [photo, setPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    return () => { if (photoPreview) URL.revokeObjectURL(photoPreview); };
  }, [photoPreview]);

  function handlePhotoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    if (!ALLOWED_PHOTO_TYPES.has(file.type)) return toast.error('La foto debe ser JPEG, PNG o WebP');
    if (file.size > MAX_PHOTO_BYTES) return toast.error('La foto no debe superar 5 MB');
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(file);
    setPhotoPreview(URL.createObjectURL(file));
  }

  function removePhoto() {
    if (photoPreview) URL.revokeObjectURL(photoPreview);
    setPhoto(null);
    setPhotoPreview(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || name.trim().length < 2) return toast.error('Escribe tu nombre');
    if (!phone.trim() || phone.replace(/\D/g, '').length < 7) return toast.error('Escribe un teléfono válido');
    if (!message.trim() || message.trim().length < 5) return toast.error('Cuéntanos un poco más en el mensaje');
    if (!accepted) return toast.error('Debes aceptar que tu nombre y teléfono sean visibles para publicar');

    setSubmitting(true);
    try {
      const form = new FormData();
      form.set('post_type', postType);
      form.set('reporter_name', name.trim());
      form.set('contact_phone', phone.trim());
      form.set('message', message.trim());
      form.set('accepted_privacy', String(accepted));
      if (photo) form.set('photo', photo);

      const res = await fetch(`${API_BASE}/v1/public/community/adoption/quick-post`, {
        method: 'POST',
        body: form,
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: 'Error al publicar' }));
        throw new Error(body.detail ?? 'Error al publicar');
      }
      toast.success('🎉 ¡Publicado! Ya aparece más abajo');
      setName('');
      setPhone('');
      setMessage('');
      setAccepted(false);
      removePhoto();
      router.refresh();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'No se pudo publicar');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-3xl border-2 border-[#187f77]/20 bg-white p-6 md:p-8 shadow-sm">
      <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-1">Foro de la comunidad</h2>
      <p className="text-sm text-muted-foreground mb-1">
        Publica en 10 segundos. Solo necesitamos tu nombre y tu teléfono — nada de cuentas ni contraseñas.
      </p>
      <p className="text-xs text-muted-foreground mb-6">
        Bigotes y Paticas conecta a quienes tienen un animal en adopción con quienes desean adoptar — no
        gestionamos ni somos responsables del proceso de adopción en sí.
      </p>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setPostType('offer')}
            className={`flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold border-2 transition-all ${
              postType === 'offer' ? 'border-[#187f77] bg-[#E6F5F1] text-[#0d4a45]' : 'border-gray-200 text-gray-500'
            }`}
          >
            <Home className="h-4 w-4" /> Doy en adopción
          </button>
          <button
            type="button"
            onClick={() => setPostType('want')}
            className={`flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold border-2 transition-all ${
              postType === 'want' ? 'border-[#187f77] bg-[#E6F5F1] text-[#0d4a45]' : 'border-gray-200 text-gray-500'
            }`}
          >
            <Search className="h-4 w-4" /> Busco adoptar
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <input
            className="rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#187f77]/30"
            placeholder="Tu nombre"
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={150}
          />
          <input
            className="rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#187f77]/30"
            placeholder="Tu teléfono / WhatsApp"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            maxLength={40}
          />
        </div>

        <textarea
          className="rounded-xl border border-gray-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-[#187f77]/30"
          rows={3}
          placeholder={
            postType === 'offer'
              ? 'Ej: "Tengo 2 gaticos de 2 meses, muy sanos, buscan hogar en Pereira"'
              : 'Ej: "Busco un perrito pequeño y tranquilo para adoptar en Dosquebradas"'
          }
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          maxLength={1000}
        />

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={handlePhotoChange}
          className="sr-only"
        />
        {photoPreview ? (
          <div className="relative w-28 h-28 rounded-xl overflow-hidden border-2 border-[#187f77]/20">
            {/* eslint-disable-next-line @next/next/no-img-element -- vista previa local (object URL), nunca pasa por next/image */}
            <img src={photoPreview} alt="Vista previa" className="w-full h-full object-cover" />
            <button
              type="button"
              onClick={removePhoto}
              aria-label="Quitar foto"
              className="absolute top-1 right-1 h-6 w-6 rounded-full bg-black/60 text-white flex items-center justify-center hover:bg-black/80"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center justify-center gap-2 py-3 rounded-xl text-sm font-semibold border-2 border-dashed border-[#187f77]/30 text-[#187f77] hover:bg-[#E6F5F1] transition-colors"
          >
            <Camera className="h-4 w-4" /> Agregar foto del animalito (opcional)
          </button>
        )}

        <label className="flex items-start gap-2.5 text-xs text-gray-500 leading-relaxed">
          <input
            type="checkbox"
            checked={accepted}
            onChange={(e) => setAccepted(e.target.checked)}
            className="mt-0.5 h-4 w-4 shrink-0 accent-[#187f77]"
          />
          Acepto que mi nombre y teléfono sean visibles públicamente en esta página para que puedan contactarme. Ver{' '}
          <Link href="/politica-privacidad" className="underline">
            política de privacidad
          </Link>
          .
        </label>

        <button
          type="submit"
          disabled={submitting}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#187f77] text-white font-bold text-sm py-3.5 hover:bg-[#0d4a45] transition-colors disabled:opacity-50"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          Publicar ahora
        </button>
      </form>
    </div>
  );
}
