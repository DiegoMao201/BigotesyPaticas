'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LifeBuoy, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { portalLocation } from '@/lib/api';

const STORAGE_KEY = 'bp_last_geo_prompt';
const THROTTLE_MS = 4 * 60 * 60 * 1000; // 4 horas

/**
 * Antes de disparar el permiso nativo del navegador, explicamos por qué lo
 * pedimos — mejora muchísimo la tasa de aceptación vs. pedirlo en frío.
 * Throttled a 1 vez cada 4h (acepte o no) para no ser invasivos.
 */
export function LocationTracker() {
  const [show, setShow] = useState(false);
  const [requesting, setRequesting] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || !navigator.geolocation) return;
    const last = Number(localStorage.getItem(STORAGE_KEY) ?? 0);
    if (Date.now() - last < THROTTLE_MS) return;
    setShow(true);
  }, []);

  function dismiss() {
    localStorage.setItem(STORAGE_KEY, String(Date.now()));
    setShow(false);
  }

  function accept() {
    setRequesting(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        localStorage.setItem(STORAGE_KEY, String(Date.now()));
        portalLocation.update(pos.coords.latitude, pos.coords.longitude).catch(() => {});
        toast.success('¡Gracias! Ya puedes recibir alertas de mascotas perdidas cerca de ti 🐾');
        setRequesting(false);
        setShow(false);
      },
      () => {
        localStorage.setItem(STORAGE_KEY, String(Date.now()));
        setRequesting(false);
        setShow(false);
      },
      { enableHighAccuracy: false, timeout: 10_000, maximumAge: 60 * 60 * 1000 }
    );
  }

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center"
          style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)' }}
        >
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 40, opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="w-full max-w-sm bg-white rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl"
          >
            <div
              className="flex flex-col items-center gap-3 py-7 px-6 text-center"
              style={{ background: 'linear-gradient(135deg, #ff7a63, #e8433a)' }}
            >
              <div className="h-14 w-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
                <LifeBuoy className="h-7 w-7 text-white" strokeWidth={2} />
              </div>
              <h2 className="font-display font-bold text-white text-xl leading-tight">
                Ayudemos a encontrar mascotas perdidas
              </h2>
            </div>

            <div className="p-6 flex flex-col gap-4">
              <p className="text-sm text-foreground leading-relaxed">
                Con tu ubicación te avisamos solo cuando haya una mascota perdida{' '}
                <strong>cerca de ti</strong>, y si tú reportas una, la comunidad de Bigotes y
                Paticas se entera al instante. Entre todos somos más 🐾
              </p>
              <p className="text-xs text-muted">
                Nunca compartimos tu ubicación exacta con otros clientes, solo la usamos para
                calcular cercanía.
              </p>

              <div className="flex flex-col gap-2 pt-1">
                <button
                  onClick={accept}
                  disabled={requesting}
                  className="sos-submit-btn w-full disabled:opacity-70"
                >
                  {requesting ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Sí, quiero ayudar'}
                </button>
                <button
                  onClick={dismiss}
                  disabled={requesting}
                  className="w-full py-2.5 text-sm font-semibold text-muted"
                >
                  Ahora no
                </button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
