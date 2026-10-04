'use client';

/**
 * Capa decorativa de temporada para el portal. Solo existe en octubre: fuera de
 * la temporada este componente no pinta nada y el portal queda exactamente como
 * estaba.
 *
 * Es la hermana de `HuellasFondo` de la tienda (apps/store) y sigue el mismo
 * contrato, que es lo que la hace inofensiva:
 *  - `pointer-events-none` y `aria-hidden`: ni se come un clic ni la lee un
 *    lector de pantalla.
 *  - Detrás de todo (`-z-10`) y solo en pantallas anchas: el portal se usa
 *    sobre todo en el celular, donde no hay margen que decorar y cada píxel es
 *    para la tarea.
 *  - Solo `transform`, y se apaga con `prefers-reduced-motion`.
 *
 * Si cambias las figuras, cambian en los dos sitios: este archivo y
 * apps/store/src/components/brand/HuellasFondo.tsx. No hay paquete compartido
 * entre las apps y no vale la pena crearlo por cuatro dibujos.
 */

import { useTemporada } from '@/lib/temporada';
import { Calabaza, Fantasma, Murcielago, HuellaBruja } from './figuras-halloween';

const NARANJA = '#FF6B35';
const MORADO = '#7c3aed';
const TINTA = '#262730';

/**
 * Las opacidades están medidas en pantalla, no elegidas a ojo: estas figuras
 * van caladas (la calabaza tiene la huella recortada, el murciélago son tres
 * piezas) y por debajo de 0,19 el negro se lee como una pelusa gris en vez de
 * un murciélago. Y el murciélago va además más grande que el resto: es ancho
 * y bajito, así que dentro de un cuadro de 64 solo ocupa un tercio del alto.
 */
const FIGURAS = [
  { Figura: Calabaza, color: NARANJA, izq: '2%', arriba: '14%', tam: 55, giro: -16, dur: 11.5, retraso: 0, op: 0.3 },
  { Figura: Murcielago, color: TINTA, izq: '6%', arriba: '52%', tam: 60, giro: 10, dur: 14, retraso: 2.2, op: 0.28 },
  { Figura: HuellaBruja, color: MORADO, izq: '3%', arriba: '79%', tam: 47, giro: 6, dur: 12.5, retraso: 1.4, op: 0.28 },
  { Figura: Fantasma, color: MORADO, der: '3%', arriba: '22%', tam: 46, giro: 12, dur: 13, retraso: 0.9, op: 0.3 },
  { Figura: Calabaza, color: NARANJA, der: '7%', arriba: '58%', tam: 52, giro: -22, dur: 10.5, retraso: 3, op: 0.28 },
  { Figura: Murcielago, color: TINTA, der: '2%', arriba: '85%', tam: 53, giro: 26, dur: 15, retraso: 1.8, op: 0.26 },
];

export function FondoTemporada() {
  const temporada = useTemporada();
  if (temporada !== 'halloween') return null;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      {FIGURAS.map(({ Figura, color, izq, der, arriba, tam, giro, dur, retraso, op }, i) => (
        <span
          key={i}
          className="figura-flota absolute"
          style={{
            left: izq,
            right: der,
            top: arriba,
            opacity: op,
            animationDuration: `${dur}s`,
            animationDelay: `${retraso}s`,
          }}
        >
          <svg width={tam} height={tam} viewBox="0 0 64 64" style={{ transform: `rotate(${giro}deg)` }}>
            <Figura color={color} />
          </svg>
        </span>
      ))}
    </div>
  );
}
