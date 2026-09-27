'use client';

/**
 * Ventana de bienvenida de la reactivación del groomer (27-sep-2026). Diego: "que le
 * salga 10% de descuento si reserva, bien bonito, como pop apenas inicia sesión".
 * Sale una vez por sesión en el inicio del portal (no interrumpe si ya está reservando).
 */
import { useEffect, useState } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';

const CLAVE = 'bp_promo_groomer_vista';

export function PromoGroomer() {
  const pathname = usePathname();
  const router = useRouter();
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (pathname !== '/dashboard') return;
    try {
      if (sessionStorage.getItem(CLAVE)) return;
      sessionStorage.setItem(CLAVE, '1');
    } catch { /* sin storage: igual se muestra */ }
    const t = setTimeout(() => setAbierto(true), 600);
    return () => clearTimeout(t);
  }, [pathname]);

  function reservar() {
    setAbierto(false);
    router.push('/appointments/new');
  }

  return (
    <AnimatePresence>
      {abierto && (
        <motion.div
          className="fixed inset-0 z-[80] flex items-center justify-center p-5 bg-black/55 backdrop-blur-sm"
          initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
          onClick={() => setAbierto(false)}
        >
          <motion.div
            role="dialog" aria-modal="true" aria-label="Promoción peluquería"
            onClick={(e) => e.stopPropagation()}
            initial={{ scale: 0.7, y: 40, opacity: 0 }}
            animate={{ scale: 1, y: 0, opacity: 1 }}
            exit={{ scale: 0.85, y: 20, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 260, damping: 20 }}
            className="relative w-full max-w-sm overflow-hidden rounded-[28px] shadow-2xl"
            style={{ background: 'linear-gradient(160deg,#0d4a45 0%,#187f77 55%,#1fa393 100%)' }}
          >
            <button onClick={() => setAbierto(false)} aria-label="Cerrar"
              className="absolute right-3 top-3 z-10 h-9 w-9 rounded-full bg-white/15 text-white flex items-center justify-center">
              <X className="h-5 w-5" />
            </button>
            {/* burbujas de baño */}
            {[...Array(9)].map((_, i) => (
              <motion.span key={i}
                className="absolute rounded-full bg-white/25"
                style={{ width: 10 + (i % 4) * 9, height: 10 + (i % 4) * 9, left: `${8 + i * 10}%`, bottom: -30 }}
                animate={{ y: [-10, -420], opacity: [0, 0.8, 0] }}
                transition={{ duration: 3.2 + (i % 3), repeat: Infinity, delay: i * 0.35, ease: 'easeOut' }}
              />
            ))}
            <div className="relative px-6 pt-8 pb-6 text-center text-white">
              <motion.div
                animate={{ rotate: [-8, 8, -8] }} transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
                className="text-6xl mb-2" aria-hidden
              >🛁</motion.div>
              <p className="text-sm font-bold uppercase tracking-[0.2em] text-[#B2FF59]">¡Volvió la peluquería!</p>
              <p className="mt-1 text-[64px] font-black leading-none text-[#F5A641] drop-shadow-[0_4px_0_rgba(0,0,0,.35)]">10%</p>
              <p className="text-2xl font-extrabold leading-tight">de descuento</p>
              <p className="mt-2 text-sm text-white/90">
                reservando tu cita de baño y peluquería <b>aquí en el portal</b>. Perros y gatos · lunes a sábado, 10 a. m. a 7 p. m.
              </p>
              <button onClick={reservar}
                className="mt-5 w-full py-3.5 rounded-2xl bg-[#F5A641] text-[#0d4a45] text-lg font-black shadow-lg active:scale-[0.98] transition">
                Reservar mi cita ✂️
              </button>
              <button onClick={() => setAbierto(false)} className="mt-3 text-sm text-white/75 underline">
                Ahora no
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
