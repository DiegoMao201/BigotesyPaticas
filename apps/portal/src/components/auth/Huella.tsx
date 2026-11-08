'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { Fingerprint, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { activarPasskey, passkeysDisponibles } from '@/lib/passkeys';
import { useAuthStore } from '@/lib/auth-store';
import { tomarTurno } from '@/lib/turno';

type Llave = { id: string; nombre: string | null; creada: string | null; usada: string | null };
const lista = () => fetch('/api/v1/portal/auth/passkeys', { credentials: 'include' }).then((r) => (r.ok ? r.json() : [])) as Promise<Llave[]>;

function nombreEquipo() {
  const ua = navigator.userAgent;
  if (/iPhone/.test(ua)) return 'iPhone';
  if (/iPad/.test(ua)) return 'iPad';
  if (/Android/.test(ua)) return 'Celular Android';
  if (/Mac/.test(ua)) return 'Mac';
  return 'Este equipo';
}

/** Tarjeta del perfil: activar/quitar la huella o Face ID de cada celular. */
export function HuellaPerfil() {
  const qc = useQueryClient();
  const [soporta, setSoporta] = useState(false);
  const { data: llaves = [] } = useQuery({ queryKey: ['passkeys'], queryFn: lista });
  useEffect(() => { passkeysDisponibles().then(setSoporta); }, []);

  async function activar() {
    try {
      await activarPasskey(nombreEquipo());
      toast.success('Listo: la próxima vez entras con tu huella o Face ID');
      qc.invalidateQueries({ queryKey: ['passkeys'] });
    } catch (e) {
      const m = (e as Error).message || '';
      if (!/abort|cancel|NotAllowed/i.test(m + (e as Error).name)) toast.error(m || 'No se pudo activar');
    }
  }
  async function quitar(id: string) {
    await fetch(`/api/v1/portal/auth/passkeys/${encodeURIComponent(id)}`, { method: 'DELETE', credentials: 'include' });
    qc.invalidateQueries({ queryKey: ['passkeys'] });
  }

  if (!soporta && llaves.length === 0) return null;
  return (
    <div className="rounded-2xl bg-white p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gray-900 text-white"><Fingerprint className="h-5 w-5" /></div>
        <div className="flex-1">
          <p className="text-sm font-bold">Entrar con huella o Face ID</p>
          <p className="text-xs text-muted">Más rápido y más seguro que la cédula: la llave nunca sale de tu celular.</p>
        </div>
      </div>
      {llaves.map((l) => (
        <div key={l.id} className="mt-3 flex items-center justify-between rounded-xl bg-gray-50 px-3 py-2 text-sm">
          <span>{l.nombre ?? 'Celular'}</span>
          <button onClick={() => quitar(l.id)} className="text-gray-400" aria-label="Quitar"><Trash2 className="h-4 w-4" /></button>
        </div>
      ))}
      {soporta && (
        <button onClick={activar} className="mt-3 w-full rounded-full bg-gray-900 py-3 text-sm font-bold text-white">
          {llaves.length ? 'Agregar este celular' : 'Activar en este celular'}
        </button>
      )}
    </div>
  );
}

/** Ofrece activar la huella UNA vez, después del login, si el celular la soporta. */
export function HuellaOferta() {
  const qc = useQueryClient();
  const terminos = useAuthStore((s) => s.customer?.terms_accepted_at);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!terminos) return;
    let vivo = true;
    (async () => {
      try { if (localStorage.getItem('bp_huella_ofrecida')) return; } catch { return; }
      if (!(await passkeysDisponibles())) return;
      const ll = await lista();
      if (!vivo || ll.length) return;
      setTimeout(() => { if (vivo && tomarTurno('huella')) setAbierto(true); }, 1500);
    })();
    return () => { vivo = false; };
  }, [terminos]);

  function cerrar() {
    try { localStorage.setItem('bp_huella_ofrecida', String(Date.now())); } catch { /* nada */ }
    setAbierto(false);
  }
  async function activar() {
    try {
      await activarPasskey(nombreEquipo());
      toast.success('Listo: la próxima vez entras con un toque');
      qc.invalidateQueries({ queryKey: ['passkeys'] });
    } catch { /* canceló */ }
    cerrar();
  }

  return (
    <AnimatePresence>
      {abierto && (
        <motion.div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/45 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={cerrar}>
          <motion.div
            className="w-full max-w-[430px] rounded-t-[1.75rem] bg-white p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))] text-center"
            initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 380, damping: 38 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-gray-900 text-white"><Fingerprint className="h-8 w-8" /></div>
            <h2 className="mt-4 font-display text-xl font-bold">Entra con tu huella o Face ID</h2>
            <p className="mt-2 text-sm text-gray-600">Sin escribir la cédula cada vez. Es más seguro: nadie puede entrar a tu cuenta aunque sepa tus datos.</p>
            <button onClick={activar} className="mt-5 w-full rounded-full bg-gray-900 py-3.5 text-sm font-bold text-white">Activar</button>
            <button onClick={cerrar} className="mt-2 w-full py-3 text-sm font-semibold text-gray-500">Ahora no</button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
