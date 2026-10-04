'use client';

import { useEffect, useState } from 'react';

/**
 * Temporada activa de la tienda.
 *
 * Una sola fuente de verdad para "¿estamos en Halloween?". Todo lo que se
 * disfrace (fondo, cinta, acentos de color) pregunta aquí y nada más.
 *
 * POR QUE SE CALCULA EN EL CLIENTE Y NO EN EL SERVIDOR:
 * las páginas de la tienda se generan estáticas y se revalidan. Si la fecha se
 * leyera al construir, el disfraz quedaría congelado en el HTML: se encendería
 * cuando Google reconstruya, no el 1 de octubre, y peor todavía, seguiría
 * puesto en diciembre. En el cliente también se resuelve solo el huso horario:
 * `new Date()` es la hora del visitante, que en Pereira es la que importa.
 *
 * El precio es que el disfraz aparece un cuadro después de pintar. Para una
 * capa decorativa que vive detrás del contenido, no se nota; y evita que el
 * HTML cacheado mienta sobre la fecha.
 */

export type Temporada = 'halloween' | null;

/** 1 de octubre → 2 de noviembre (el día de difuntos todavía cuenta acá). */
export function temporadaDe(fecha: Date): Temporada {
  const mes = fecha.getMonth(); // 0-11
  const dia = fecha.getDate();
  if (mes === 9) return 'halloween';
  if (mes === 10 && dia <= 2) return 'halloween';
  return null;
}

export function useTemporada(): Temporada {
  const [temporada, setTemporada] = useState<Temporada>(null);
  useEffect(() => setTemporada(temporadaDe(new Date())), []);
  return temporada;
}
