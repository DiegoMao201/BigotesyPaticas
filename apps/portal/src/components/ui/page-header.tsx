'use client';

import type { ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { Logo } from '@/components/brand/Logo';

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  /** Si se pasa, muestra flecha "volver" en vez del lockup de marca (para páginas de detalle/creación). */
  back?: boolean;
}

/**
 * Encabezado consistente para todas las páginas del portal (excepto Dashboard,
 * que tiene su propio saludo personalizado). Da presencia de marca constante
 * y el mismo ritmo tipográfico en toda la app.
 */
export function PageHeader({ title, subtitle, action, back }: PageHeaderProps) {
  const router = useRouter();

  return (
    <div className="flex flex-col gap-3 mb-1">
      {back ? (
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1 -ml-2 p-2 w-fit rounded-xl text-muted hover:bg-black/5 transition-colors"
          aria-label="Volver"
        >
          <ArrowLeft className="h-5 w-5" />
        </button>
      ) : (
        <div className="flex items-center gap-1.5">
          <Logo size={16} />
          <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-primary-700">
            Bigotes y Paticas
          </span>
        </div>
      )}

      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <h1 className="font-display text-[26px] font-extrabold leading-tight text-foreground tracking-tight truncate">
            {title}
          </h1>
          {subtitle && <p className="text-muted text-sm mt-0.5">{subtitle}</p>}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </div>
    </div>
  );
}
