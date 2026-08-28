'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

export interface LightboxPhoto {
  url: string;
  caption?: string | null;
}

interface Props {
  photos: LightboxPhoto[];
  index: number;
  onClose: () => void;
  onIndexChange: (i: number) => void;
}

export function PhotoLightbox({ photos, index, onClose, onIndexChange }: Props) {
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  const go = (delta: number) => {
    const next = (index + delta + photos.length) % photos.length;
    onIndexChange(next);
  };

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onClose();
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'ArrowRight') go(1);
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, photos.length]);

  if (typeof document === 'undefined') return null;
  const photo = photos[index];
  if (!photo) return null;

  return createPortal(
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100] bg-black/95 flex flex-col"
        onClick={onClose}
        onTouchStart={(e) => setTouchStartX(e.touches[0].clientX)}
        onTouchEnd={(e) => {
          if (touchStartX == null) return;
          const dx = e.changedTouches[0].clientX - touchStartX;
          if (dx > 50) go(-1);
          else if (dx < -50) go(1);
          setTouchStartX(null);
        }}
      >
        <div className="flex items-center justify-between px-4 pt-[calc(env(safe-area-inset-top,0px)+12px)] pb-3">
          <span className="text-white/70 text-xs font-semibold">
            {index + 1} / {photos.length}
          </span>
          <button
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            className="h-9 w-9 rounded-full bg-white/10 flex items-center justify-center text-white active:scale-90 transition-transform"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="flex-1 flex items-center justify-center relative px-2" onClick={(e) => e.stopPropagation()}>
          {photos.length > 1 && (
            <button
              onClick={() => go(-1)}
              className="hidden sm:flex absolute left-3 h-10 w-10 rounded-full bg-white/10 items-center justify-center text-white active:scale-90 transition-transform"
            >
              <ChevronLeft className="h-6 w-6" />
            </button>
          )}
          <motion.img
            key={photo.url}
            initial={{ opacity: 0, scale: 0.97 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.18 }}
            src={photo.url}
            alt={photo.caption ?? 'Foto'}
            className="max-h-[70vh] max-w-full object-contain rounded-lg"
          />
          {photos.length > 1 && (
            <button
              onClick={() => go(1)}
              className="hidden sm:flex absolute right-3 h-10 w-10 rounded-full bg-white/10 items-center justify-center text-white active:scale-90 transition-transform"
            >
              <ChevronRight className="h-6 w-6" />
            </button>
          )}
        </div>

        {photo.caption && (
          <p className="text-white/90 text-sm text-center px-6 pb-[calc(env(safe-area-inset-bottom,0px)+20px)] pt-2">
            {photo.caption}
          </p>
        )}
      </motion.div>
    </AnimatePresence>,
    document.body
  );
}
