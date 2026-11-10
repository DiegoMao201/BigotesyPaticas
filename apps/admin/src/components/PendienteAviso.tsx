'use client';

import { useState } from 'react';
import { Clock } from 'lucide-react';

/** Franja que dice QUÉ quedó a medias en esta pantalla y deja retomarlo o borrarlo.
 *  Diego (10-nov-2026): el menú marcaba "en curso" en Compras y Clientes y no había
 *  forma de ver qué era: el borrador vivía en una pestaña o un diálogo cerrados. */
export function PendienteAviso({ texto, onContinuar, onDescartar }: {
  texto: React.ReactNode;
  onContinuar: () => void;
  onDescartar: () => void;
}) {
  const [confirmar, setConfirmar] = useState(false);
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 text-sm text-amber-900 dark:border-amber-700 dark:bg-amber-950/40 dark:text-amber-200">
      <Clock className="h-4 w-4 shrink-0" />
      <span className="min-w-0 flex-1">{texto}</span>
      <span className="flex gap-2">
        {confirmar ? (
          <>
            <button className="rounded-md bg-red-600 px-2.5 py-1 text-xs font-semibold text-white hover:bg-red-700" onClick={() => { onDescartar(); setConfirmar(false); }}>
              Sí, borrarlo
            </button>
            <button className="rounded-md border px-2.5 py-1 text-xs" onClick={() => setConfirmar(false)}>No</button>
          </>
        ) : (
          <>
            <button className="rounded-md bg-amber-500 px-3 py-1 text-xs font-bold text-white hover:bg-amber-600" onClick={onContinuar}>
              Continuar
            </button>
            <button className="rounded-md border border-amber-400 px-2.5 py-1 text-xs hover:bg-amber-100 dark:hover:bg-amber-900" onClick={() => setConfirmar(true)}>
              Descartar
            </button>
          </>
        )}
      </span>
    </div>
  );
}
