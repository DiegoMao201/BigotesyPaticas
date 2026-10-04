'use client';

/**
 * La cinta de temporada: una franja delgada sobre el encabezado, solo en
 * octubre. Desaparece sola el 3 de noviembre, sin que nadie tenga que acordarse
 * de quitarla.
 *
 * Va ANTES del `<header>`, que es `sticky top-0`: la cinta se va con el scroll
 * y el encabezado se queda pegado. Así no le roba altura permanente a la
 * pantalla, que es lo que vuelve molestas estas franjas.
 *
 * ⚠️ DIEGO: el texto de abajo NO promete nada que no sea cierto hoy (el
 * domicilio el mismo día ya está en la portada). Si vas a hacer concurso,
 * descuento o jornada de disfraces, cambia `MENSAJE` y `CTA` por lo que de
 * verdad vas a cumplir. No lo dejes genérico si tienes algo mejor que contar.
 */

import Link from 'next/link';
import { useTemporada } from '@/lib/temporada';

const MENSAJE = 'Feliz Halloween — domicilio el mismo día en Pereira y Dosquebradas';
const CTA = { texto: 'Ver catálogo', href: '/categorias/todos' };

export function CintaTemporada() {
  const temporada = useTemporada();
  if (temporada !== 'halloween') return null;

  return (
    <div className="cinta-halloween relative overflow-hidden text-white">
      <div className="container-wide flex min-h-10 items-center justify-center gap-2 py-1.5 text-center text-[12.5px] font-medium leading-snug sm:py-0 sm:text-sm">
        <span aria-hidden="true" className="cinta-calabaza shrink-0 text-base leading-none">
          🎃
        </span>
        <span>{MENSAJE}</span>
        <Link
          href={CTA.href}
          className="hidden shrink-0 rounded-full bg-white/20 px-3 py-0.5 text-[12px] font-semibold transition-colors duration-150 hover:bg-white/30 sm:inline-block"
        >
          {CTA.texto}
        </Link>
      </div>
    </div>
  );
}
