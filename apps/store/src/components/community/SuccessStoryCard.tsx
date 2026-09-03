import Link from 'next/link';
import { PetPhoto } from '@/components/ui/PetPhoto';

/**
 * Tarjeta de "final feliz" (mascota en casa / reunidos / adoptado). Misma
 * pieza en /mascotas-perdidas, /mascotas-encontradas, /adopcion y
 * /finales-felices para que la comunidad reconozca el patrón.
 */
export function SuccessStoryCard({
  href,
  photo,
  title,
  subtitle,
  headline,
  note,
  badge,
  date,
}: {
  href: string;
  photo: string | null | undefined;
  title: string;
  subtitle?: string | null;
  headline: string;
  note: string;
  badge: string;
  date?: string | null;
}) {
  return (
    <Link
      href={href}
      className="group block rounded-3xl border-2 border-emerald-200 bg-emerald-50/40 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
    >
      {photo ? (
        <div className="relative w-full h-48 overflow-hidden bg-[#F8F9FA]">
          <PetPhoto src={photo} alt={title} sizes="(max-width: 768px) 100vw, (max-width: 1024px) 50vw, 33vw" className="group-hover:scale-105 transition-transform duration-300" />
        </div>
      ) : (
        <div className="w-full h-48 bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center text-5xl">🎉</div>
      )}
      <div className="p-5">
        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500 text-white text-[10px] font-bold uppercase tracking-wide px-2.5 py-1 mb-2">
          {badge}
        </span>
        <h3 className="font-display font-bold text-lg leading-tight mb-0.5">{headline}</h3>
        <p className="text-sm text-muted-foreground mb-2">
          {title}
          {subtitle ? <span className="capitalize"> · {subtitle}</span> : null}
        </p>
        <p className="text-sm text-emerald-900 leading-relaxed line-clamp-3">{note}</p>
        {date && (
          <p className="text-[11px] text-muted-foreground mt-3">
            {new Date(date).toLocaleDateString('es-CO', { day: 'numeric', month: 'long', year: 'numeric' })}
          </p>
        )}
      </div>
    </Link>
  );
}

export const SUCCESS_BADGE: Record<string, string> = {
  lost: 'Ya en casa',
  found: 'Reunidos',
  adoption_offer: 'Adoptado',
  adoption_want: 'Ya adoptó',
};
