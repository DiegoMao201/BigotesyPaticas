'use client';

import { useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Star, Camera, X, Upload, CheckCircle, ExternalLink, ChevronLeft, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { orders, request } from '@/lib/api';
import { trackEvent } from '@/lib/analytics';

// ── Tipos ────────────────────────────────────────────────────────────────────

interface ReviewDraft {
  rating: number;
  title: string;
  comment: string;
  photoUrls: string[];
  petName: string;
}

const DEFAULT_DRAFT: ReviewDraft = { rating: 0, title: '', comment: '', photoUrls: [], petName: '' };

// ── Star rating interactivo ───────────────────────────────────────────────────

function StarRating({ value, onChange }: { value: number; onChange: (n: number) => void }) {
  const [hover, setHover] = useState(0);
  return (
    <div className="flex gap-1" role="group" aria-label="Calificación">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          onMouseEnter={() => setHover(star)}
          onMouseLeave={() => setHover(0)}
          aria-label={`${star} estrellas`}
          className="transition-transform active:scale-90"
        >
          <Star
            className={`w-9 h-9 transition-colors ${
              star <= (hover || value) ? 'fill-amber-400 text-amber-400' : 'text-gray-200'
            }`}
          />
        </button>
      ))}
    </div>
  );
}

// ── Upload foto ───────────────────────────────────────────────────────────────

function PhotoUpload({ urls, onAdd, onRemove }: {
  urls: string[];
  onAdd: (url: string) => void;
  onRemove: (i: number) => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  async function handleFile(file: File) {
    if (!file.type.startsWith('image/')) { toast.error('Solo imágenes'); return; }
    if (file.size > 5 * 1024 * 1024) { toast.error('Máximo 5 MB por foto'); return; }
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await request<{ url: string }>('/photos/upload', { method: 'POST', body: fd });
      onAdd(res.url);
    } catch {
      toast.error('No se pudo subir la foto');
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="flex gap-3 flex-wrap items-center">
      {urls.map((url, i) => (
        <div key={i} className="relative w-20 h-20 rounded-xl overflow-hidden border-2 border-primary-200">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={url} alt={`Foto ${i + 1}`} className="w-full h-full object-cover" />
          <button
            onClick={() => onRemove(i)}
            className="absolute top-0.5 right-0.5 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center"
          >
            <X className="w-3 h-3 text-white" />
          </button>
        </div>
      ))}
      {urls.length < 2 && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="w-20 h-20 rounded-xl border-2 border-dashed border-primary-300 flex flex-col items-center justify-center gap-1 text-primary-600 hover:bg-primary-50 transition-colors disabled:opacity-60"
        >
          {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Camera className="w-5 h-5" />}
          <span className="text-[10px] font-medium">{uploading ? 'Subiendo…' : 'Foto'}</span>
        </button>
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => { if (e.target.files?.[0]) handleFile(e.target.files[0]); }}
      />
    </div>
  );
}

// ── Página principal ──────────────────────────────────────────────────────────

export default function CalificarPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [drafts, setDrafts] = useState<Record<string, ReviewDraft>>({});
  const [submitted, setSubmitted] = useState(false);
  const [totalPts, setTotalPts] = useState(0);

  const { data: timeline, isLoading } = useQuery({
    queryKey: ['order-timeline', id],
    queryFn: () => orders.timeline(id),
  });

  const submitMut = useMutation({
    mutationFn: async () => {
      const items = timeline?.items.filter((it) => it.product_id && drafts[it.product_id]?.rating > 0) ?? [];
      if (items.length === 0) throw new Error('Califica al menos un producto');
      let pts = 0;
      for (const item of items) {
        const d = drafts[item.product_id!];
        const res = await request<{ points_awarded: number }>(
          `/products/${item.product_id}/reviews`,
          {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              rating: d.rating,
              title: d.title || undefined,
              comment: d.comment || undefined,
              photo_urls: d.photoUrls,
              pet_name: d.petName || undefined,
            }),
          },
        );
        pts += res.points_awarded || 0;
        trackEvent('review_submitted', {
          product_id: item.product_id,
          rating: d.rating,
          has_photo: d.photoUrls.length > 0,
        });
      }
      return pts;
    },
    onSuccess: (pts) => {
      setTotalPts(pts);
      setSubmitted(true);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function updateDraft(productId: string, patch: Partial<ReviewDraft>) {
    setDrafts((prev) => ({
      ...prev,
      [productId]: { ...(prev[productId] ?? DEFAULT_DRAFT), ...patch },
    }));
  }

  const reviewableItems = timeline?.items.filter((it) => it.product_id && !it.is_substituted) ?? [];
  const hasAnyRating = reviewableItems.some((it) => (drafts[it.product_id!]?.rating ?? 0) > 0);
  const isDelivered = timeline?.workflow_status === 'delivered';

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary-700" />
      </div>
    );
  }

  if (!timeline || !isDelivered) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4 p-6 text-center">
        <p className="text-lg font-semibold text-foreground">
          {!timeline ? 'Pedido no encontrado' : 'Este pedido aún no fue entregado'}
        </p>
        <button onClick={() => router.back()} className="btn-outline">
          Volver
        </button>
      </div>
    );
  }

  // ── Pantalla de éxito ────────────────────────────────────────────────────
  if (submitted) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="min-h-screen flex flex-col items-center justify-center gap-6 px-6 py-12 text-center"
      >
        <div className="w-20 h-20 rounded-full bg-emerald-100 flex items-center justify-center">
          <CheckCircle className="w-10 h-10 text-emerald-600" />
        </div>
        <div>
          <h1 className="font-display text-2xl font-bold text-foreground mb-2">
            ¡Gracias por tu reseña! 🐾
          </h1>
          {totalPts > 0 && (
            <p className="text-primary-700 font-semibold text-lg">
              Ganaste {totalPts} Puntos Bigotes ✨
            </p>
          )}
          <p className="text-muted text-sm mt-2 max-w-xs mx-auto">
            Tu opinión ayuda a otras familias a elegir mejor para sus mascotas.
          </p>
        </div>

        {/* CTA Google Review */}
        <div className="w-full max-w-sm rounded-2xl bg-amber-50 border border-amber-200 p-5">
          <p className="font-bold text-amber-900 text-sm mb-1">🌟 Gana 50 Puntos extra</p>
          <p className="text-amber-800 text-xs mb-3">
            Déjanos una reseña en Google y te acreditamos 50 Puntos Bigotes adicionales.
          </p>
          <a
            href="https://g.page/r/CfL67OgLB-10EBM/review"
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => trackEvent('gbp_click', { source: 'review_success' })}
            className="inline-flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white rounded-xl text-sm font-semibold transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Reseñar en Google
          </a>
        </div>

        <button onClick={() => router.replace('/dashboard')} className="btn-primary">
          Ir al dashboard
        </button>
      </motion.div>
    );
  }

  // ── Formulario ───────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-warm pb-32">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white/90 backdrop-blur-sm border-b border-border px-4 py-3 flex items-center gap-3">
        <button onClick={() => router.back()} className="p-2 -ml-2 rounded-full hover:bg-gray-100">
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div>
          <h1 className="font-display font-bold text-base text-foreground">Califica tu pedido</h1>
          <p className="text-xs text-muted">Pedido #{id.slice(-8).toUpperCase()}</p>
        </div>
      </div>

      <div className="px-4 py-6 space-y-6 max-w-lg mx-auto">
        {/* Explicación de puntos */}
        <div className="rounded-2xl bg-primary-50 border border-primary-100 p-4">
          <p className="text-primary-800 text-sm font-semibold mb-1">🎁 Gana puntos por reseñar</p>
          <p className="text-primary-700 text-xs">
            20 pts por reseña · 30 pts si subes foto de tu mascota · 5 estrellas = publicación inmediata
          </p>
        </div>

        {/* Card por producto */}
        {reviewableItems.map((item) => {
          const pid = item.product_id!;
          const draft = drafts[pid] ?? DEFAULT_DRAFT;
          const hasRating = draft.rating > 0;
          const isAutoPublish = draft.rating === 5;

          return (
            <motion.div
              key={pid}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-2xl bg-white border border-border shadow-sm overflow-hidden"
            >
              {/* Producto */}
              <div className="flex gap-3 p-4 border-b border-border">
                {item.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={item.image_url} alt={item.name ?? ''} className="w-14 h-14 rounded-xl object-contain bg-gray-50" />
                ) : (
                  <div className="w-14 h-14 rounded-xl bg-gray-100 flex items-center justify-center text-2xl">🐾</div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-sm text-foreground line-clamp-2">{item.name}</p>
                  <p className="text-xs text-muted mt-0.5">x{item.quantity}</p>
                </div>
              </div>

              {/* Rating */}
              <div className="p-4 space-y-4">
                <div>
                  <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block">
                    ¿Cómo lo calificás?
                  </label>
                  <StarRating value={draft.rating} onChange={(r) => updateDraft(pid, { rating: r })} />
                  <AnimatePresence>
                    {hasRating && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className={`text-xs mt-2 font-medium ${isAutoPublish ? 'text-emerald-600' : 'text-amber-600'}`}
                      >
                        {isAutoPublish
                          ? '✅ Se publicará automáticamente'
                          : '⏳ Se revisará antes de publicar (< 24h)'}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>

                <AnimatePresence>
                  {hasRating && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      className="space-y-3 overflow-hidden"
                    >
                      <input
                        type="text"
                        placeholder="Título (ej. ¡A mi perro le encantó!)"
                        value={draft.title}
                        onChange={(e) => updateDraft(pid, { title: e.target.value })}
                        maxLength={200}
                        className="input-field text-sm"
                      />
                      <textarea
                        rows={3}
                        placeholder="¿Cómo le fue a tu mascota? (opcional)"
                        value={draft.comment}
                        onChange={(e) => updateDraft(pid, { comment: e.target.value })}
                        maxLength={2000}
                        className="input-field text-sm resize-none"
                      />
                      <input
                        type="text"
                        placeholder="Nombre de tu mascota (opcional)"
                        value={draft.petName}
                        onChange={(e) => updateDraft(pid, { petName: e.target.value })}
                        className="input-field text-sm"
                      />

                      {/* Fotos */}
                      <div>
                        <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 block flex items-center gap-1">
                          <Upload className="w-3 h-3" /> Foto de tu mascota usando el producto
                          <span className="text-primary-600 font-bold">(+10 pts extra)</span>
                        </label>
                        <PhotoUpload
                          urls={draft.photoUrls}
                          onAdd={(url) => updateDraft(pid, { photoUrls: [...draft.photoUrls, url] })}
                          onRemove={(i) => updateDraft(pid, { photoUrls: draft.photoUrls.filter((_, idx) => idx !== i) })}
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Botón sticky bottom */}
      <div className="fixed bottom-0 left-0 right-0 bg-white border-t border-border p-4 pb-safe">
        <button
          onClick={() => submitMut.mutate()}
          disabled={!hasAnyRating || submitMut.isPending}
          className="btn-primary w-full py-4 text-base disabled:opacity-50"
        >
          {submitMut.isPending ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            'Enviar reseñas ✨'
          )}
        </button>
        {!hasAnyRating && (
          <p className="text-center text-xs text-muted mt-2">Califica al menos un producto</p>
        )}
      </div>
    </div>
  );
}
