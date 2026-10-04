/**
 * Las figuras de Halloween, dibujadas como siluetas planas igual que la huella
 * de la marca: un solo `fill`, sin degradados ni trazos finos.
 *
 * Se ven a 28-50 px y con opacidad entre 0,10 y 0,18. A ese tamaño el detalle
 * fino desaparece, así que todo está resuelto con formas gruesas y huecos
 * grandes. Lo que NO se puede perder es la silueta: si apagas el relleno y la
 * mancha ya no se reconoce de lejos, el dibujo está mal.
 *
 * La idea de la que cuelga todo: la calabaza NO tiene la cara de siempre.
 * Tiene una huella de perro tallada. Es la marca disfrazada, no un adorno de
 * Halloween comprado hecho.
 */

/** Un óvalo escrito como path, para poder recortarlo con `fill-rule="evenodd"`. */
function ovalo(cx: number, cy: number, rx: number, ry: number) {
  return `M${cx - rx},${cy}a${rx},${ry} 0 1,0 ${rx * 2},0a${rx},${ry} 0 1,0 ${-rx * 2},0Z`;
}

/** Los 4 dedos + la almohadilla, en las proporciones de la huella de la marca. */
const HUELLA_TALLADA = [
  ovalo(22, 32, 3.4, 4.6),
  ovalo(28.8, 28.8, 3.2, 4.8),
  ovalo(35.8, 28.8, 3.2, 4.8),
  ovalo(42.4, 32, 3.4, 4.6),
  ovalo(32, 45, 8.4, 6.6),
].join('');

/** Calabaza con la huella tallada donde va la cara. La figura principal. */
export function Calabaza({ color }: { color: string }) {
  return (
    <>
      {/* tallo y hojita, en el verde oscuro de la marca */}
      <path d="M29.5,18.5c0-4,0.5-6.5,2.5-8c2,1.5,2.5,4,2.5,8z" fill="#0d4a45" />
      <path d="M34.5,13c3-2.5,6.5-2.5,9-1c-2,3-5,4.5-9,4z" fill="#187f77" />
      <path
        fill={color}
        fillRule="evenodd"
        d={
          'M32,17c13.8,0,24,9.6,24,22s-10.2,20-24,20S8,51.4,8,39S18.2,17,32,17Z' +
          HUELLA_TALLADA
        }
      />
    </>
  );
}

/** Fantasma con orejas de perro: es una mascota debajo de la sábana, no un fantasma. */
export function Fantasma({ color }: { color: string }) {
  return (
    <path
      fill={color}
      fillRule="evenodd"
      d={
        // orejas caídas asomando bajo la sábana + cuerpo con el borde ondulado
        'M16,22c-1-5,1-8,4-8c2.5,0,4,2,4.5,5zM48,22c1-5,-1-8,-4-8c-2.5,0-4,2-4.5,5z' +
        'M32,8c10,0,16,7.5,16,17v22c0,2-2,3-3.5,1.5L41,45l-3.5,4c-1,1.2-2.5,1.2-3.5,0L32,46l-2,3' +
        'c-1,1.2-2.5,1.2-3.5,0L23,45l-3.5,3.5C18,50,16,49,16,47V25C16,15.5,22,8,32,8Z' +
        // ojos
        ovalo(26, 24, 2.6, 3.4) +
        ovalo(38, 24, 2.6, 3.4)
      }
    />
  );
}

/** Murciélago con orejas de gato: el gato de la tienda, disfrazado. */
export function Murcielago({ color }: { color: string }) {
  return (
    <path
      fill={color}
      fillRule="evenodd"
      d={
        // ala izquierda, cuerpo, ala derecha — un solo trazo cerrado
        'M32,22c4.5,0,7.5,3.5,7.5,8.5c0,4-2,7.5-7.5,11.5c-5.5-4-7.5-7.5-7.5-11.5C24.5,25.5,27.5,22,32,22Z' +
        'M25.5,26C20,19,12,16,5,17c3,2.5,4.5,5.5,4.5,9c0,3.5-1.5,6-4,8.5c6-1,11,0.5,15,5c-0.5-3-0.5-6.5,0.5-10z' +
        'M38.5,26c5.5-7,13.5-10,20.5-9c-3,2.5-4.5,5.5-4.5,9c0,3.5,1.5,6,4,8.5c-6-1-11,0.5-15,5c0.5-3,0.5-6.5-0.5-10z' +
        // orejas de gato, no de murciélago
        'M26,22.5c-1.5-4-1.5-7,0-9.5c2.5,1.5,4.5,4,5.5,7z' +
        'M38,22.5c1.5-4,1.5-7,0-9.5c-2.5,1.5-4.5,4-5.5,7z' +
        // ojitos
        ovalo(29, 30, 1.6, 2.1) +
        ovalo(35, 30, 1.6, 2.1)
      }
    />
  );
}

/**
 * La huella de la marca, con sombrero de bruja. Es la misma huella de
 * `HuellasFondo` (no una parecida: los mismos óvalos), encogida al 78 % y
 * bajada para dejarle sitio al sombrero. Si alguien cambia la huella de la
 * marca, esta tiene que cambiar con ella.
 */
export function HuellaBruja({ color }: { color: string }) {
  return (
    <>
      <g transform="translate(3,17) scale(0.78)">
        <path
          fill={color}
          d={
            ovalo(20, 17, 7.5, 10) +
            ovalo(33.5, 12, 7, 10.5) +
            ovalo(46, 18, 7, 9.5) +
            ovalo(53, 31, 6.5, 8.5) +
            'M34,28c9,0,16,7,16,14c0,6-5,9-11,9c-3,0-4,1-5,1s-2-1-5-1c-6,0-11-3-11-9C18,35,25,28,34,28Z'
          }
        />
      </g>
      {/* sombrero ladeado: cono, ala y la cinta amarilla de la marca */}
      <path fill="#4c1d95" d="M21,3L36,17L24,20Z" />
      <ellipse cx="29" cy="19.5" rx="12.5" ry="3.4" fill="#4c1d95" transform="rotate(-7 29 19.5)" />
      <path fill="#f5a641" d="M25.5,14.5l8,4.2l-0.8,2.6l-8.4-4.3Z" />
    </>
  );
}
