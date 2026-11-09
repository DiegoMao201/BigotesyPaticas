'use client';

import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { BellRing, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { activarPush, estadoPush, probarPush, type EstadoPush } from '@/lib/push';
import { useAuthStore } from '@/lib/auth-store';
import { tomarTurno } from '@/lib/turno';

async function activarConMensaje(): Promise<EstadoPush> {
  try {
    const e = await activarPush();
    if (e === 'activo') toast.success('Listo: te avisaremos aunque la app esté cerrada');
    if (e === 'bloqueado') toast.error('Los avisos están bloqueados', { description: 'Actívalos en Ajustes del celular → Apps → Bigotes y Paticas → Notificaciones.' });
    return e;
  } catch (err) {
    toast.error((err as Error).message);
    return 'apagado';
  }
}

/** Fila del perfil (y de la campana): activar, probar o apagar los avisos de ESTE celular. */
export function AvisosCelular({ compacto = false }: { compacto?: boolean }) {
  const [estado, setEstado] = useState<EstadoPush | null>(null);
  const [cargando, setCargando] = useState(false);
  useEffect(() => { estadoPush().then(setEstado); }, []);
  if (!estado || estado === 'no-soportado') return null;

  async function accion() {
    setCargando(true);
    if (estado === 'activo') {
      const r = await probarPush().catch(() => ({ enviados: 0 }));
      if (r.enviados) toast.success('Te mandamos un aviso de prueba');
      else toast.error('No salió el aviso. Apágalos y vuelve a activarlos.');
    } else {
      setEstado(await activarConMensaje());
    }
    setCargando(false);
  }

  return (
    <div className={compacto ? 'm-3 rounded-2xl bg-primary-50 p-3' : 'flex items-center gap-3 py-3'}>
      <div className={compacto ? 'flex items-center gap-3' : 'contents'}>
        <div className="h-9 w-9 rounded-xl bg-primary-700 flex items-center justify-center shrink-0">
          <BellRing className="h-4 w-4 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground">Avisos en este celular</p>
          <p className="text-xs text-muted">
            {estado === 'activo' ? 'Activos: te llegan aunque la app esté cerrada'
              : estado === 'bloqueado' ? 'Bloqueados en los ajustes del celular'
              : 'Entérate al instante de tu pedido, tus citas y mascotas perdidas'}
          </p>
        </div>
        <button
          onClick={accion}
          disabled={cargando || estado === 'bloqueado'}
          className="shrink-0 rounded-full bg-primary-700 px-3.5 py-2 text-xs font-bold text-white disabled:opacity-50"
        >
          {cargando ? <Loader2 className="h-4 w-4 animate-spin" /> : estado === 'activo' ? 'Probar' : 'Activar'}
        </button>
      </div>
    </div>
  );
}

/** Ofrece los avisos UNA vez, con el porqué, antes del permiso del sistema (que solo se pide una vez). */
export function AvisosOferta() {
  const terminos = useAuthStore((s) => s.customer?.terms_accepted_at);
  const [abierto, setAbierto] = useState(false);

  useEffect(() => {
    if (!terminos) return;
    let vivo = true;
    (async () => {
      try { if (localStorage.getItem('bp_avisos_ofrecidos')) return; } catch { return; }
      if ((await estadoPush()) !== 'apagado' || Notification.permission !== 'default') return;
      setTimeout(() => { if (vivo && tomarTurno('avisos')) setAbierto(true); }, 2000);
    })();
    return () => { vivo = false; };
  }, [terminos]);

  function cerrar() {
    try { localStorage.setItem('bp_avisos_ofrecidos', String(Date.now())); } catch { /* nada */ }
    setAbierto(false);
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
            <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-primary-700 text-white"><BellRing className="h-8 w-8" /></div>
            <h2 className="mt-4 font-display text-xl font-bold">¿Te avisamos al instante?</h2>
            <p className="mt-2 text-sm text-gray-600">Cuando tu pedido salga, cuando se acerque la cita de tu mascota o si se pierde un perro o un gato cerca de ti. Nada de spam.</p>
            <button onClick={async () => { await activarConMensaje(); cerrar(); }} className="mt-5 w-full rounded-full bg-primary-700 py-3.5 text-sm font-bold text-white">Sí, avísame</button>
            <button onClick={cerrar} className="mt-2 w-full py-3 text-sm font-semibold text-gray-500">Ahora no</button>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
