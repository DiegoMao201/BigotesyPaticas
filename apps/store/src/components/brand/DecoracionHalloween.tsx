'use client';

/**
 * La decoración de Halloween. Diego pidió "infestar", no decorar: *"murciélagos
 * de esos chiquitos pasando de lado a lado, más fantasmas y más telarañas
 * colgantes que bajan y suben y desaparecen, y un fondo telarañoso pasando de
 * lado a lado... unos 3 o 4 fantasmas en diferentes figuras"*.
 *
 * Lo que hay en pantalla a la vez:
 *
 * | Pieza | Cuántas | Qué hace |
 * |---|---|---|
 * | Fondo de telaraña | 1 | se desliza de lado a lado, sin fin |
 * | Telarañas de esquina | 2 | marco fijo, arriba |
 * | Telarañas colgantes | 6 | bajan, se quedan, suben y se desvanecen |
 * | Araña del hilo | 1 | baja y sube al lado del logo |
 * | Murciélagos | 9 | cruzan en las dos direcciones, aleteando |
 * | Fantasmas | 4 figuras | clásico, gato, perro y chiquito |
 * | Gato negro | 1 | camina por el borde de abajo |
 *
 * **Los cuatro fantasmas comparten cuerpo y se distinguen por lo de encima**:
 * orejas, bigotes, lengua, color y tamaño. Es lo que los hace reconocibles de un
 * vistazo sin cuadruplicar el código, y lo que permite que la sábana de los
 * cuatro ondee con la misma animación.
 *
 * Qué lo mantiene del lado del adorno aunque sean dos docenas de piezas:
 * `pointer-events-none` en todo (jamás se come un clic), `aria-hidden`, nada por
 * encima del menú del celular (z-[70]), **solo `transform` y `opacity`** —que el
 * navegador compone en la GPU sin recalcular ni repintar la página— y
 * `prefers-reduced-motion` deja la decoración puesta y quieta.
 *
 * Y nada de esto se descarga: son dibujos escritos a mano, ni una sola imagen.
 * El icono de 2 MB que costó 11 s de LCP sigue siendo la lección.
 */

import { useTemporada } from '@/lib/temporada';

/* ─── Telarañas ──────────────────────────────────────────────────────────── */

/** Telaraña de esquina: hilos radiales desde el vértice y arcos con comba. */
function Telarana() {
  return (
    <svg viewBox="0 0 110 110" className="h-full w-full" fill="none">
      <path
        d="M0,0L91.8,6.4M0,0L84.1,37.4M0,0L65.1,65.1M0,0L37.4,84.1M0,0L6.4,91.8
           M25.9,1.8Q24.8,10.1 23.7,10.6M23.7,10.6Q20.0,17.6 18.4,18.4M18.4,18.4Q13.3,22.9 10.6,23.7M10.6,23.7Q4.4,24.9 1.8,25.9
           M47.9,3.3Q45.8,18.7 43.8,19.6M43.8,19.6Q36.9,32.4 33.9,33.9M33.9,33.9Q24.6,42.2 19.6,43.8M19.6,43.8Q8.1,46.0 3.3,47.9
           M69.8,4.9Q66.8,27.2 63.8,28.6M63.8,28.6Q53.8,47.3 49.5,49.5M49.5,49.5Q35.9,61.5 28.6,63.8M28.6,63.8Q11.8,67.1 4.9,69.8
           M91.8,6.4Q87.7,35.8 83.9,37.6M83.9,37.6Q70.8,62.1 65.1,65.1M65.1,65.1Q47.2,80.9 37.6,83.9M37.6,83.9Q15.5,88.2 6.4,91.8"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  );
}

/** Telaraña redonda, de las que cuelgan de un hilo. */
function TelaranaColgante() {
  return (
    <svg viewBox="0 0 64 64" className="h-full w-full" fill="none">
      <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
        <path d="M32,32L32,2M32,32L53,11M32,32L62,32M32,32L53,53M32,32L32,62M32,32L11,53M32,32L2,32M32,32L11,11" />
        <path d="M32,12Q27,13 25.8,18.2Q20,20 18.2,25.8Q13,27 12,32Q13,37 18.2,38.2Q20,44 25.8,45.8Q27,51 32,52Q37,51 38.2,45.8Q44,44 45.8,38.2Q51,37 52,32Q51,27 45.8,25.8Q44,20 38.2,18.2Q37,13 32,12Z" />
        <path d="M32,2Q23,4 20.5,11.5Q13,14 11,22.5Q4,25 2,32Q4,39 11,41.5Q13,50 20.5,52.5Q23,60 32,62Q41,60 43.5,52.5Q51,50 53,41.5Q60,39 62,32Q60,25 53,22.5Q51,14 43.5,11.5Q41,4 32,2Z" />
      </g>
    </svg>
  );
}

/** Araña de ocho patas. */
function Arana() {
  return (
    <svg viewBox="0 0 40 34" className="h-full w-full" fill="currentColor">
      <g stroke="currentColor" strokeWidth="2" strokeLinecap="round" fill="none">
        <path d="M15,14L6,8L1,13M15,17L4,16L0,21M15,20L5,24L2,30M16,23L9,30L8,34" />
        <path d="M25,14L34,8L39,13M25,17L36,16L40,21M25,20L35,24L38,30M24,23L31,30L32,34" />
      </g>
      <ellipse cx="20" cy="12" rx="5" ry="4.5" />
      <ellipse cx="20" cy="21" rx="7" ry="8" />
      <circle cx="18" cy="11" r="1.1" fill="#fff" />
      <circle cx="22" cy="11" r="1.1" fill="#fff" />
    </svg>
  );
}

/* ─── Murciélago ─────────────────────────────────────────────────────────── */

/** Plano a propósito: el aleteo lo estrecha en horizontal. */
function MurcielagoVuelo() {
  return (
    <svg viewBox="0 0 64 34" className="h-full w-full" fill="currentColor">
      <path
        d="M32,8c3.4,0,5.6,2.6,5.6,6.4c0,3-1.5,5.6-5.6,8.6c-4.1-3-5.6-5.6-5.6-8.6C26.4,10.6,28.6,8,32,8Z
           M27.1,11C23,5.8,17,3.5,11.8,4.3c2.2,1.9,3.4,4.1,3.4,6.7c0,2.6-1.1,4.5-3,6.4c4.5-0.8,8.2,0.4,11.2,3.7c-0.4-2.2-0.4-4.9,0.4-7.5z
           M36.9,11c4.1-5.2,10.1-7.5,15.3-6.7c-2.2,1.9-3.4,4.1-3.4,6.7c0,2.6,1.1,4.5,3,6.4c-4.5-0.8-8.2,0.4-11.2,3.7c0.4-2.2,0.4-4.9-0.4-7.5z
           M28.3,8.4c-1.1-3-1.1-5.2,0-7.1c1.9,1.1,3.4,3,4.1,5.2z
           M35.7,8.4c1.1-3,1.1-5.2,0-7.1c-1.9,1.1-3.4,3-4.1,5.2z"
      />
    </svg>
  );
}

/* ─── Fantasmas ──────────────────────────────────────────────────────────── */

/**
 * Los tres estados del borde de la sábana. Misma estructura de comandos en los
 * tres —solo cambian las alturas de los picos— porque SMIL interpola punto por
 * punto: con una curva de más, el fantasma daría un salto en vez de ondear.
 */
const SABANA = [
  'M35,4C50,4,58,15,58,30v33c0,4-4,5-6.5,2l-4.5,-8.5l-4,5c-1.6,2-4,2-5.6,0l-3.4,-1.2l-3.4,7.2c-1.6,2-4,2-5.6,0l-4,-8l-4.5,5.5C13,69,12,68,12,64V30C12,15,20,4,35,4Z',
  'M35,4C50,4,58,15,58,30v30c0,4-4,5-6.5,2l-4.5,-2.5l-4,8c-1.6,2-4,2-5.6,0l-3.4,-7.2l-3.4,4.2c-1.6,2-4,2-5.6,0l-4,-2l-4.5,8.5C13,72,12,71,12,67V30C12,15,20,4,35,4Z',
  'M35,4C50,4,58,15,58,30v33c0,4-4,5-6.5,2l-4.5,-8.5l-4,5c-1.6,2-4,2-5.6,0l-3.4,-1.2l-3.4,7.2c-1.6,2-4,2-5.6,0l-4,-8l-4.5,5.5C13,69,12,68,12,64V30C12,15,20,4,35,4Z',
].join(';');

type Piel = { relleno: string; trazo: string; cara: string };

/** El cuerpo con la sábana ondeando. Lo que va encima llega por `children`. */
function Cuerpo({ piel, children }: { piel: Piel; children?: React.ReactNode }) {
  return (
    <svg viewBox="0 0 70 92" className="h-full w-full">
      <path fill={piel.relleno} stroke={piel.trazo} strokeWidth="2" d={SABANA.split(';')[0]}>
        <animate attributeName="d" values={SABANA} dur="1.6s" repeatCount="indefinite" />
      </path>
      {children}
    </svg>
  );
}

const LILA: Piel = { relleno: '#f6f2ff', trazo: '#6d28d9', cara: '#4c1d95' };
const MENTA: Piel = { relleno: '#eefcfa', trazo: '#0d9488', cara: '#115e59' };
const DURAZNO: Piel = { relleno: '#fff4ec', trazo: '#c2410c', cara: '#7c2d12' };
const MIEL: Piel = { relleno: '#fffbe8', trazo: '#b45309', cara: '#78350f' };

/** El de siempre: bracitos y boca de sorpresa. */
function FantasmaClasico() {
  return (
    <Cuerpo piel={LILA}>
      <path fill={LILA.relleno} stroke={LILA.trazo} strokeWidth="2" d="M11,34c-4,1-6,4-5,7c1,2.6,4,3,6,1z" />
      <path fill={LILA.relleno} stroke={LILA.trazo} strokeWidth="2" d="M59,34c4,1,6,4,5,7c-1,2.6-4,3-6,1z" />
      <ellipse cx="27" cy="28" rx="4.4" ry="5.8" fill={LILA.cara} />
      <ellipse cx="43" cy="28" rx="4.4" ry="5.8" fill={LILA.cara} />
      <path d="M30,41c1.6,3.4,8.4,3.4,10,0c-1.6,5-8.4,5-10,0z" fill={LILA.cara} />
    </Cuerpo>
  );
}

/** Gato fantasma: orejas en punta y bigotes. */
function FantasmaGato() {
  return (
    <Cuerpo piel={MENTA}>
      <path fill={MENTA.relleno} stroke={MENTA.trazo} strokeWidth="2" d="M18,14l-1-12l12,7zM52,14l1-12l-12,7z" />
      <ellipse cx="27" cy="28" rx="3" ry="6" fill={MENTA.cara} />
      <ellipse cx="43" cy="28" rx="3" ry="6" fill={MENTA.cara} />
      <path d="M32,38q3,3 6,0" stroke={MENTA.cara} strokeWidth="2" fill="none" />
      <g stroke={MENTA.cara} strokeWidth="1.4">
        <path d="M20,36h-8M20,39h-8M50,36h8M50,39h8" />
      </g>
    </Cuerpo>
  );
}

/** Perro fantasma: orejas caídas y la lengua afuera. */
function FantasmaPerro() {
  return (
    <Cuerpo piel={DURAZNO}>
      <path fill={DURAZNO.relleno} stroke={DURAZNO.trazo} strokeWidth="2" d="M14,16c-6,2-8,12-5,20c3,5,8,3,8-3z" />
      <path fill={DURAZNO.relleno} stroke={DURAZNO.trazo} strokeWidth="2" d="M56,16c6,2,8,12,5,20c-3,5-8,3-8-3z" />
      <ellipse cx="28" cy="29" rx="3.6" ry="5" fill={DURAZNO.cara} />
      <ellipse cx="42" cy="29" rx="3.6" ry="5" fill={DURAZNO.cara} />
      <ellipse cx="35" cy="39" rx="3.4" ry="2.6" fill={DURAZNO.cara} />
      <path d="M33,43q2,6 4,0" fill="#fb7185" />
    </Cuerpo>
  );
}

/** El pequeño: sin apéndices, todo ojos. */
function FantasmaChiquito() {
  return (
    <Cuerpo piel={MIEL}>
      <ellipse cx="28" cy="27" rx="4.6" ry="6" fill={MIEL.cara} />
      <ellipse cx="44" cy="27" rx="4.6" ry="6" fill={MIEL.cara} />
      <ellipse cx="36" cy="40" rx="3.6" ry="4.6" fill={MIEL.cara} />
    </Cuerpo>
  );
}

/* ─── Gato que camina ────────────────────────────────────────────────────── */

/**
 * Las cuatro patas giran desde donde se unen al cuerpo, en dos parejas CRUZADAS
 * —delantera izquierda con trasera derecha—, que es como camina un gato; las
 * cuatro a la vez sería un salto. `transformBox: 'view-box'` para dar el eje en
 * coordenadas del dibujo: con el `fill-box` por defecto, el eje de una pata
 * inclinada cae en la esquina de su caja y la pata gira desde el aire.
 */
function GatoCamina() {
  const eje = (x: number, y: number) => ({
    transformBox: 'view-box' as const,
    transformOrigin: `${x}px ${y}px`,
  });
  return (
    <svg viewBox="0 0 120 64" className="h-full w-full">
      <path className="gato-cola" d="M28,32c-10-2-16-12-13-22c1,8,7,14,14,15z" fill="currentColor" style={eje(30, 33)} />
      <g fill="currentColor">
        <ellipse cx="58" cy="34" rx="30" ry="14" />
        <circle cx="90" cy="24" r="12" />
        <path d="M80,16l-2-11l10,6zM96,14l6-10l3,11z" />
      </g>
      <g stroke="currentColor" strokeWidth="6" strokeLinecap="round">
        <path className="gato-pata" d="M44,44L40,60" style={eje(44, 44)} />
        <path className="gato-pata gato-pata-b" d="M52,45L56,60" style={eje(52, 45)} />
        <path className="gato-pata gato-pata-b" d="M70,45L66,60" style={eje(70, 45)} />
        <path className="gato-pata" d="M78,44L82,60" style={eje(78, 44)} />
      </g>
      <circle cx="95" cy="22" r="2.2" fill="#f5a641" />
    </svg>
  );
}

/* ─── El reparto ─────────────────────────────────────────────────────────── */

/** `rev` = cruza de derecha a izquierda. Mezclar las dos direcciones es lo que
 *  hace que parezca una bandada y no una fila. */
const MURCIELAGOS = [
  { arriba: '7%', tam: 26, dur: 17, retraso: -2, aleteo: 0.36, op: 0.42, rev: false },
  { arriba: '15%', tam: 18, dur: 23, retraso: -9, aleteo: 0.3, op: 0.3, rev: true },
  { arriba: '24%', tam: 32, dur: 20, retraso: -14, aleteo: 0.44, op: 0.38, rev: false },
  { arriba: '33%', tam: 20, dur: 28, retraso: -4, aleteo: 0.32, op: 0.28, rev: true },
  { arriba: '45%', tam: 24, dur: 19, retraso: -11, aleteo: 0.38, op: 0.34, rev: false },
  { arriba: '56%', tam: 16, dur: 25, retraso: -17, aleteo: 0.28, op: 0.26, rev: true },
  { arriba: '66%', tam: 30, dur: 22, retraso: -6, aleteo: 0.42, op: 0.36, rev: false },
  { arriba: '77%', tam: 19, dur: 30, retraso: -21, aleteo: 0.34, op: 0.27, rev: true },
  { arriba: '87%', tam: 23, dur: 18, retraso: -13, aleteo: 0.4, op: 0.3, rev: false },
];

/** Alturas, tamaños y ritmos repartidos para que nunca crucen dos a la vez. */
const FANTASMAS = [
  { Comp: FantasmaClasico, arriba: '30%', ancho: 78, dur: 24, retraso: -5, op: 0.62, rev: false },
  { Comp: FantasmaGato, arriba: '58%', ancho: 64, dur: 31, retraso: -19, op: 0.55, rev: true },
  { Comp: FantasmaPerro, arriba: '12%', ancho: 70, dur: 28, retraso: -12, op: 0.5, rev: false },
  { Comp: FantasmaChiquito, arriba: '73%', ancho: 46, dur: 21, retraso: -2, op: 0.58, rev: true },
];

/** Las colgantes van repartidas a lo ancho y cada una con su propio compás. */
const COLGANTES = [
  { izq: '26%', tam: 30, hilo: 30, dur: 13, retraso: 0 },
  { izq: '41%', tam: 22, hilo: 54, dur: 17, retraso: -5 },
  { izq: '57%', tam: 34, hilo: 24, dur: 15, retraso: -9 },
  { izq: '69%', tam: 20, hilo: 66, dur: 19, retraso: -3 },
  { izq: '83%', tam: 27, hilo: 40, dur: 14, retraso: -11 },
  { izq: '92%', tam: 18, hilo: 72, dur: 21, retraso: -7 },
];

export function DecoracionHalloween() {
  const temporada = useTemporada();
  if (temporada !== 'halloween') return null;

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-[55] overflow-hidden">
      {/* FONDO DE TELARAÑA — una banda del doble de ancho que se desliza media
          anchura y vuelve a empezar: como el patrón se repite, el salto no se
          ve y el deslizamiento parece infinito. Va con `transform`, no con
          `background-position`, para que lo mueva la GPU sin repintar. */}
      <div className="telarana-fondo absolute -left-1/2 top-0 h-full w-[200%]" />

      {/* TELARAÑAS DE ESQUINA — marco fijo, por encima del encabezado y por
          debajo del menú del celular, que va en z-[70]. */}
      <div className="absolute left-0 top-0 h-24 w-24 text-ink/35 sm:h-36 sm:w-36 lg:h-44 lg:w-44">
        <Telarana />
      </div>
      <div className="absolute right-0 top-0 h-24 w-24 -scale-x-100 text-ink/35 sm:h-36 sm:w-36 lg:h-44 lg:w-44">
        <Telarana />
      </div>

      {/* TELARAÑAS COLGANTES — bajan, se quedan un momento, suben y se van. */}
      {COLGANTES.map((c, i) => (
        <div
          key={i}
          className="colgante absolute top-0 flex flex-col items-center"
          style={{ left: c.izq, animationDuration: `${c.dur}s`, animationDelay: `${c.retraso}s` }}
        >
          <span className="block w-px bg-ink/25" style={{ height: c.hilo }} />
          <span className="block text-ink/30" style={{ width: c.tam, height: c.tam }}>
            <TelaranaColgante />
          </span>
        </div>
      ))}

      {/* ARAÑA — arranca por encima del borde para que el hilo no deje hueco. */}
      <div className="arana-cuelga absolute -top-7 left-[17%] flex flex-col items-center sm:left-[12%]">
        <span className="block w-px bg-ink/30" style={{ height: 'clamp(42px, 8vw, 80px)' }} />
        <span className="block h-5 w-6 text-ink/55 sm:h-7 sm:w-8">
          <Arana />
        </span>
      </div>

      {/* MURCIÉLAGOS */}
      {MURCIELAGOS.map((v, i) => (
        <span
          key={i}
          className={`${v.rev ? 'murcielago-cruza-rev' : 'murcielago-cruza'} absolute text-ink`}
          style={{
            top: v.arriba,
            opacity: v.op,
            animationDuration: `${v.dur}s`,
            animationDelay: `${v.retraso}s`,
          }}
        >
          <span
            className="murcielago-aletea block"
            style={{ width: v.tam, height: v.tam * 0.53, animationDuration: `${v.aleteo}s` }}
          >
            <MurcielagoVuelo />
          </span>
        </span>
      ))}

      {/* FANTASMAS — la posición y el tamaño van en `style` y no en clases
          arbitrarias: `top-[30%]` no llegó a generarse en el CSS servido y el
          fantasma se quedó sin `top`, aunque `w-[4.6rem]` del mismo archivo sí
          estaba. Para algo que debe aparecer sí o sí, `style` no falla. */}
      {FANTASMAS.map(({ Comp, arriba, ancho, dur, retraso, op, rev }, i) => (
        <span
          key={i}
          className={rev ? 'fantasma-pasa-rev absolute' : 'fantasma-pasa absolute'}
          style={{
            top: arriba,
            width: `clamp(${ancho * 0.66}px, ${ancho / 13}vw, ${ancho}px)`,
            height: `clamp(${ancho * 0.87}px, ${ancho / 9.9}vw, ${ancho * 1.31}px)`,
            animationDuration: `${dur}s`,
            animationDelay: `${retraso}s`,
            ['--op' as string]: op,
          }}
        >
          <span className="fantasma-flota block h-full w-full">
            <Comp />
          </span>
        </span>
      ))}

      {/* GATO — camina por el borde de abajo, que es donde el ojo espera el suelo. */}
      <span
        className="gato-pasea absolute bottom-0"
        style={{
          width: 'clamp(92px, 11vw, 150px)',
          height: 'clamp(49px, 5.9vw, 80px)',
          color: 'rgba(28,27,34,0.82)',
        }}
      >
        <GatoCamina />
      </span>
    </div>
  );
}
