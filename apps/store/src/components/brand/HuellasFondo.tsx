'use client';

/**
 * Huellitas de colores flotando en el fondo de toda la tienda.
 *
 * Diego (12-sep-2026): "colocarles huellitas de colores que bajen y suban en
 * esos espacios en blanco, no muy intensos pero sí visibles, en todo el store,
 * así le damos más innovación".
 *
 * Tres cosas innegociables para que decore y no estorbe:
 *  - `pointer-events-none` y `aria-hidden`: nunca se come un clic ni la lee un
 *    lector de pantalla.
 *  - Va detrás del contenido, y solo se ven las que caen FUERA de la columna de
 *    lectura (por eso están pegadas a los bordes y se ocultan en pantallas
 *    angostas, donde no hay espacio en blanco que llenar).
 *  - Animación solo con CSS `transform`, que corre en la GPU y no recalcula
 *    la página. Y se apaga entera con `prefers-reduced-motion`.
 *
 * TEMPORADA (4-oct-2026): en octubre las huellitas se disfrazan. Mismo número
 * de figuras, mismas posiciones, mismo peso: solo cambia el dibujo. Es un
 * cambio de vestuario, no una capa nueva encima — así el disfraz no puede
 * costar rendimiento ni tapar nada que antes se viera.
 */

import { useTemporada } from '@/lib/temporada';
import { Calabaza, Fantasma, Murcielago, HuellaBruja } from './figuras-halloween';

const TEAL = '#187f77';
const AMBAR = '#f5a641';
const VERDE = '#0d4a45';
const NARANJA = '#FF6B35';
const MORADO = '#7c3aed';
const TINTA = '#262730';

/** Posición y ritmo. Los dos juegos comparten las mismas 6 ranuras. */
const RANURAS = [
  { izq: '2%', arriba: '12%', tam: 46, giro: -18, dur: 11, retraso: 0, op: 0.13 },
  { izq: '6%', arriba: '46%', tam: 30, giro: 22, dur: 14, retraso: 2.5, op: 0.16 },
  { izq: '3%', arriba: '74%', tam: 38, giro: 8, dur: 12.5, retraso: 1.2, op: 0.1 },
  { der: '3%', arriba: '20%', tam: 34, giro: 14, dur: 13, retraso: 0.8, op: 0.15 },
  { der: '7%', arriba: '55%', tam: 44, giro: -26, dur: 10.5, retraso: 3.1, op: 0.12 },
  { der: '2%', arriba: '84%', tam: 28, giro: 32, dur: 15, retraso: 1.9, op: 0.11 },
];

function Huella({ color }: { color: string }) {
  return (
    <>
      <ellipse cx="20" cy="17" rx="7.5" ry="10" fill={color} />
      <ellipse cx="33.5" cy="12" rx="7" ry="10.5" fill={color} />
      <ellipse cx="46" cy="18" rx="7" ry="9.5" fill={color} />
      <ellipse cx="53" cy="31" rx="6.5" ry="8.5" fill={color} />
      <path
        fill={color}
        d="M34 28c9 0 16 7 16 14 0 6-5 9-11 9-3 0-4 1-5 1s-2-1-5-1c-6 0-11-3-11-9 0-7 7-14 16-14z"
      />
    </>
  );
}

/** Una figura puesta en una ranura. `op` y `escala` solo los usa Halloween. */
type Pieza = {
  Figura: React.ComponentType<{ color: string }>;
  color: string;
  op?: number;
  escala?: number;
};

/** El reparto de cada temporada, en el orden de las ranuras. */
const NORMAL: Pieza[] = [
  { Figura: Huella, color: TEAL },
  { Figura: Huella, color: AMBAR },
  { Figura: Huella, color: VERDE },
  { Figura: Huella, color: AMBAR },
  { Figura: Huella, color: TEAL },
  { Figura: Huella, color: VERDE },
];

/**
 * Octubre: calabaza con huella tallada, fantasma con orejas, gato-murciélago.
 *
 * Llevan opacidad y tamaño propios, y no los de la ranura, porque NO pesan lo
 * mismo que una huella. La huella es una mancha sólida; estas figuras están
 * caladas —la calabaza tiene la huella recortada, el murciélago son tres
 * piezas— y con la opacidad de la huella se deshacen en nada. Medido en
 * pantalla: a 0,13 el murciélago negro se leía como una pelusa gris.
 * Por eso van más opacas y más grandes, y el murciélago más que ninguna: es
 * ancho y bajito, así que dentro de un cuadro de 64 solo ocupa un tercio del
 * alto y se veía la mitad de grande que las demás.
 */
const HALLOWEEN: Pieza[] = [
  { Figura: Calabaza, color: NARANJA, op: 0.3, escala: 1.25 },
  { Figura: Murcielago, color: TINTA, op: 0.28, escala: 1.75 },
  { Figura: HuellaBruja, color: MORADO, op: 0.28, escala: 1.3 },
  { Figura: Fantasma, color: MORADO, op: 0.3, escala: 1.35 },
  { Figura: Calabaza, color: NARANJA, op: 0.28, escala: 1.25 },
  { Figura: Murcielago, color: TINTA, op: 0.26, escala: 1.75 },
];

export function HuellasFondo() {
  const temporada = useTemporada();
  const reparto = temporada === 'halloween' ? HALLOWEEN : NORMAL;

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      {RANURAS.map((r, i) => {
        const { Figura, color, op, escala } = reparto[i];
        const tam = Math.round(r.tam * (escala ?? 1));
        return (
          <span
            key={i}
            className="huella-flota absolute"
            style={{
              left: r.izq,
              right: r.der,
              top: r.arriba,
              opacity: op ?? r.op,
              animationDuration: `${r.dur}s`,
              animationDelay: `${r.retraso}s`,
            }}
          >
            <svg
              width={tam}
              height={tam}
              viewBox="0 0 64 64"
              style={{ transform: `rotate(${r.giro}deg)` }}
            >
              <Figura color={color} />
            </svg>
          </span>
        );
      })}
    </div>
  );
}
