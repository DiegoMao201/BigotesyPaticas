'use client';

/**
 * Cinta de temporada del portal. Solo en octubre, y desaparece sola el 3 de
 * noviembre sin que nadie tenga que acordarse de quitarla.
 *
 * En la tienda la cinta vende; aquí NO. Quien entra al portal ya es cliente, y
 * lo que le sirve en Halloween es el aviso que de verdad manda gente a
 * urgencias: el chocolate y el dulce son tóxicos para perros y gatos, y el 31
 * de octubre la casa se llena de ambos. Un consejo cierto vale más que un
 * descuento inventado, y es lo que hace que la marca se vea como la que sabe.
 */

import { useTemporada } from '@/lib/temporada';

const MENSAJE = 'Halloween: el chocolate y los dulces son tóxicos para perros y gatos. Guárdalos alto.';

export function CintaTemporada() {
  const temporada = useTemporada();
  if (temporada !== 'halloween') return null;

  return (
    <div className="cinta-halloween px-4 py-2 text-center text-white">
      <p className="mx-auto flex max-w-3xl items-center justify-center gap-2 text-[12.5px] font-medium leading-snug sm:text-sm">
        <span aria-hidden="true" className="cinta-calabaza shrink-0 text-base leading-none">
          🎃
        </span>
        <span>{MENSAJE}</span>
      </p>
    </div>
  );
}
