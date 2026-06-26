'use client';

import { useEffect } from 'react';
import Link from 'next/link';

export default function PortalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error('[Portal Error]', error.message, error.stack);
  }, [error]);

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-6 gap-6 text-center">
      <div className="text-5xl">⚠️</div>
      <div>
        <h2 className="font-display text-xl font-bold text-foreground mb-1">Algo salió mal</h2>
        <p className="text-muted text-sm max-w-xs">
          {error.message || 'Ocurrió un error inesperado en el portal.'}
        </p>
      </div>
      <pre className="bg-red-50 text-red-700 text-[10px] rounded-xl p-4 max-w-xs w-full text-left overflow-auto max-h-40 whitespace-pre-wrap">
        {error.stack ?? error.message}
      </pre>
      <div className="flex gap-3">
        <button
          onClick={reset}
          className="btn-primary text-sm py-2.5 px-5"
        >
          Reintentar
        </button>
        <Link href="/dashboard" className="btn-outline text-sm py-2.5 px-5">
          Ir al inicio
        </Link>
      </div>
    </div>
  );
}
