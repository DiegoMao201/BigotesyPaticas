'use client';

import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';
import { Trash2 } from 'lucide-react';
import { auth } from '@/lib/api';

/**
 * Eliminar mi cuenta (8-nov-2026). Apple (guía 5.1.1(v)) y Google Play exigen que se
 * pueda borrar la cuenta desde la app, y la Ley 1581 da el derecho de supresión.
 * Se dice ANTES qué se borra y qué se conserva por ley, y se confirma escribiendo
 * ELIMINAR para que nadie la borre de un toque accidental.
 */
export function EliminarCuenta() {
  const [abierto, setAbierto] = useState(false);
  const [texto, setTexto] = useState('');
  const [enviando, setEnviando] = useState(false);

  async function confirmar() {
    setEnviando(true);
    try {
      const r = await auth.deleteAccount();
      try { localStorage.clear(); } catch { /* nada */ }
      toast.success('Cuenta eliminada', { description: r.message, duration: 9000 });
      window.location.href = '/login';
    } catch (e) {
      toast.error((e as Error).message || 'No se pudo eliminar. Escríbenos por WhatsApp.');
      setEnviando(false);
    }
  }

  return (
    <>
      {/* 8-nov-2026: visible en "Tu cuenta" (Diego no la encontró: era un texto gris diminuto) */}
      <button onClick={() => setAbierto(true)} className="card flex w-full items-center gap-3 py-3 text-left">
        <div className="h-9 w-9 rounded-xl bg-red-50 flex items-center justify-center shrink-0"><Trash2 className="h-4 w-4 text-red-600" /></div>
        <div className="flex-1">
          <p className="text-sm font-semibold text-red-600">Eliminar mi cuenta</p>
          <p className="text-xs text-muted">Borra tus datos, mascotas y puntos</p>
        </div>
      </button>
      <AnimatePresence>
        {abierto && (
          <motion.div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/50 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => !enviando && setAbierto(false)}>
            <motion.div
              className="w-full max-w-[430px] rounded-t-[1.75rem] bg-white p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
              initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 380, damping: 38 }}
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="font-display text-xl font-bold">¿Eliminar tu cuenta?</h2>
              <ul className="mt-3 space-y-2 text-sm text-gray-600">
                <li>• Se cierra tu sesión en todos tus dispositivos y ya no podrás entrar con esta cuenta.</li>
                <li>• Borramos tus datos personales, tus mascotas, tu ubicación y tus puntos Bigotes en máximo 15 días hábiles.</li>
                <li>• Las facturas de tus compras se conservan porque la ley nos obliga.</li>
              </ul>
              <p className="mt-4 text-sm font-semibold">Escribe <span className="text-red-600">ELIMINAR</span> para confirmar</p>
              <input value={texto} onChange={(e) => setTexto(e.target.value)} autoCapitalize="characters" className="input-field mt-2" placeholder="ELIMINAR" />
              <button
                disabled={texto.trim().toUpperCase() !== 'ELIMINAR' || enviando}
                onClick={confirmar}
                className="mt-4 w-full rounded-full bg-red-600 py-3.5 text-sm font-bold text-white disabled:opacity-40"
              >
                {enviando ? 'Eliminando…' : 'Eliminar mi cuenta para siempre'}
              </button>
              <button disabled={enviando} onClick={() => setAbierto(false)} className="mt-2 w-full py-3 text-sm font-semibold text-gray-600">Cancelar</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
