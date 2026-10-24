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
 * (Actualizado el 24-oct-2026: ahora el valor inicial también se calcula en el
 * servidor; ver useTemporada.)
 */

export type Temporada = 'halloween' | null;

/** 1 de octubre → 2 de noviembre (el día de difuntos todavía cuenta acá), en hora
 *  de Bogotá: el servidor corre en UTC y adelantaría el cambio cinco horas. */
export function temporadaDe(fecha: Date): Temporada {
  const [mes, dia] = fecha
    .toLocaleDateString('en-CA', { timeZone: 'America/Bogota', month: '2-digit', day: '2-digit' })
    .split('-')
    .map(Number);
  if (mes === 10) return 'halloween';
  if (mes === 11 && dia <= 2) return 'halloween';
  return null;
}

/**
 * 24-oct-2026: el valor inicial se calcula YA (también en el servidor), así la cinta
 * sale en el HTML y no empuja la página un cuadro después de pintar. Ese empujón no
 * se veía mientras la portada tardaba en pintarse; al acelerarla apareció como
 * salto de diseño (CLS 0,052). El HTML se regenera cada 10-60 min, así que en el
 * cambio de temporada puede quedar hasta una hora desfasado: el efecto lo corrige.
 */
export function useTemporada(): Temporada {
  const [temporada, setTemporada] = useState<Temporada>(() => temporadaDe(new Date()));
  useEffect(() => setTemporada(temporadaDe(new Date())), []);
  return temporada;
}
