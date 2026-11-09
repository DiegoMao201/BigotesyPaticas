'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';
import { CheckCircle2, Mail } from 'lucide-react';
import { auth } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { tomarTurno } from '@/lib/turno';
import { PasoCodigo, PasoCorreo } from '@/components/auth/PasoCodigo';

const CLAVE = 'bp_correo_ofrecido';
const CADA = 3 * 86400 * 1000;

/** Hoja para agregar/confirmar el correo con un código. */
function HojaCorreo({ inicial, onCerrar }: { inicial: string; onCerrar: (listo: boolean) => void }) {
  const qc = useQueryClient();
  const [hint, setHint] = useState<string | null>(null);
  const [enviado, setEnviado] = useState('');
  return (
    <motion.div className="fixed inset-0 z-[90] flex items-end justify-center bg-black/45 backdrop-blur-sm" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => onCerrar(false)}>
      <motion.div
        className="w-full max-w-[430px] rounded-t-[1.75rem] bg-white p-6 pb-[max(1.5rem,env(safe-area-inset-bottom))]"
        initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} transition={{ type: 'spring', stiffness: 380, damping: 38 }}
        onClick={(e) => e.stopPropagation()}
      >
        {hint === null ? (
          <PasoCorreo
            titulo={inicial ? 'Confirma tu correo' : 'Protege tu cuenta'}
            texto={inicial
              ? 'Cuando entres desde otro celular te enviaremos un código a este correo. Confírmalo para no quedarte por fuera.'
              : 'Agrega tu correo: cuando entres desde otro celular te enviaremos un código, así nadie más puede entrar a tu cuenta.'}
            inicial={inicial}
            onEnviar={async (correo) => { const r = await auth.miCorreo(correo); setEnviado(correo); setHint(r.email_hint); }}
            onVolver={() => onCerrar(false)}
          />
        ) : (
          <PasoCodigo
            hint={hint}
            onVerificar={async (codigo) => {
              await auth.miCorreoVerificar(codigo);
              toast.success('Listo: tu cuenta quedó protegida');
              qc.invalidateQueries({ queryKey: ['portal-me'] });
              qc.invalidateQueries({ queryKey: ['seguridad'] });
              onCerrar(true);
            }}
            onReenviar={async () => { const r = await auth.miCorreo(enviado); setHint(r.email_hint); }}
            onVolver={() => setHint(null)}
          />
        )}
      </motion.div>
    </motion.div>
  );
}

/**
 * 8-nov-2026: los clientes que ya están dentro y no tienen correo confirmado. Desde hoy,
 * entrar con cédula + teléfono en un celular nuevo pide un código al correo; sin correo
 * confirmado se quedarían por fuera la próxima vez. Se ofrece cada 3 días hasta que lo hagan.
 */
export function CorreoSeguro() {
  const terminos = useAuthStore((s) => s.customer?.terms_accepted_at);
  const [abierto, setAbierto] = useState(false);
  const [inicial, setInicial] = useState('');

  useEffect(() => {
    if (!terminos) return;
    let vivo = true;
    (async () => {
      try {
        if (Date.now() - Number(localStorage.getItem(CLAVE) ?? 0) < CADA) return;
      } catch { return; }
      const s = await auth.seguridad().catch(() => null);
      if (!vivo || !s || s.correo_verificado) return;
      setInicial(s.email ?? '');
      setTimeout(() => { if (vivo && tomarTurno('correo')) setAbierto(true); }, 1000);
    })();
    return () => { vivo = false; };
  }, [terminos]);

  function cerrar(listo: boolean) {
    try { localStorage.setItem(CLAVE, String(listo ? Date.now() + 3650 * 86400 * 1000 : Date.now())); } catch { /* nada */ }
    setAbierto(false);
  }

  return <AnimatePresence>{abierto && <HojaCorreo inicial={inicial} onCerrar={cerrar} />}</AnimatePresence>;
}

/** Fila del perfil: el correo con su estado y el botón para confirmarlo. */
export function CorreoFila() {
  const { data } = useQuery({ queryKey: ['seguridad'], queryFn: auth.seguridad });
  const [abierto, setAbierto] = useState(false);
  const ok = data?.correo_verificado;
  return (
    <>
      <div className="flex items-center gap-3 py-3">
        <div className="h-9 w-9 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
          {ok ? <CheckCircle2 className="h-4 w-4 text-primary-700" /> : <Mail className="h-4 w-4 text-primary-700" />}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-foreground">Correo</p>
          <p className="truncate text-xs text-muted">{data?.email ? `${data.email}${ok ? ' · confirmado' : ' · sin confirmar'}` : 'Agrégalo para entrar seguro desde otro celular'}</p>
        </div>
        <button onClick={() => setAbierto(true)} className="shrink-0 rounded-full border border-primary-700 px-3.5 py-2 text-xs font-bold text-primary-700">
          {ok ? 'Cambiar' : data?.email ? 'Confirmar' : 'Agregar'}
        </button>
      </div>
      <AnimatePresence>{abierto && <HojaCorreo inicial={ok ? '' : data?.email ?? ''} onCerrar={() => setAbierto(false)} />}</AnimatePresence>
    </>
  );
}
