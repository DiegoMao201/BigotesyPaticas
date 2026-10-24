'use client';

import { useState } from 'react';
import { Save } from 'lucide-react';
import { descartarBorrador, useBorradores, useHayBorrador } from '@/lib/borradores';

/** Franja que avisa que lo que se ve es un borrador guardado y deja descartarlo. */
export function BorradorAviso({ prefijo, onDescartar }: { prefijo: string; onDescartar?: () => void }) {
  const hay = useHayBorrador(prefijo);
  const at = useBorradores((s) =>
    Math.max(0, ...Object.entries(s.b).filter(([k]) => k === prefijo || k.startsWith(`${prefijo}:`)).map(([, e]) => e.at)),
  );
  const [confirmar, setConfirmar] = useState(false);
  if (!hay) return null;
  const hora = new Date(at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' });
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
      <Save className="h-4 w-4 shrink-0" />
      <span>Trabajo sin terminar guardado ({hora}). Puedes salir de esta pantalla: aquí te espera.</span>
      <span className="ml-auto flex gap-2">
        {confirmar ? (
          <>
            <button
              className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-700"
              onClick={() => { descartarBorrador(prefijo); onDescartar?.(); setConfirmar(false); }}
            >
              Sí, borrar todo
            </button>
            <button className="rounded-md border px-2.5 py-1 text-xs" onClick={() => setConfirmar(false)}>
              No
            </button>
          </>
        ) : (
          <button className="rounded-md border border-amber-400 px-2.5 py-1 text-xs hover:bg-amber-100 dark:hover:bg-amber-900" onClick={() => setConfirmar(true)}>
            Descartar
          </button>
        )}
      </span>
    </div>
  );
}
