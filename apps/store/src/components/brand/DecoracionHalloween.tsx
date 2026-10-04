'use client';

/**
 * La decoración de Halloween que SÍ se ve: telarañas en las esquinas, una araña
 * que baja de su hilo, murciélagos que cruzan aleteando, un fantasma que
 * atraviesa la pantalla ondeando la sábana y un gato negro que camina por el
 * borde de abajo moviendo las patas.
 *
 * POR QUÉ EXISTE APARTE DE LAS FIGURAS DEL FONDO (4-oct-2026): las figuras de
 * `HuellasFondo` viven en los márgenes, están quietas salvo por un flotar
 * mínimo, y se ocultan en pantallas angostas porque en el celular no hay margen
 * que decorar. Resultado: en el teléfono no se veía nada de la temporada salvo
 * la cinta. Diego: *"esos iconos en los lados se ven estáticos, quietos, no hay
 * un fantasma andando por la pantalla"*. Tenía razón en las dos cosas.
 *
 * Esto va POR ENCIMA del contenido, se ve en todas las pantallas, y cada pieza
 * se mueve de verdad:
 *
 * | Pieza | Qué hace | Cada cuánto |
 * |---|---|---|
 * | Telarañas | marco fijo en las dos esquinas de arriba | siempre |
 * | Araña | baja y sube de su hilo | ciclo de 7 s |
 * | Murciélagos | cruzan en diagonal, aleteando | 22-31 s |
 * | Fantasma | atraviesa ondeando, aparece y se desvanece | cada 34 s |
 * | Gato negro | camina por el borde inferior | cada 46 s |
 *
 * Lo que lo mantiene del lado del adorno y no del estorbo: `pointer-events-none`
 * en todo (jamás se come un clic), `aria-hidden`, nada por encima del menú del
 * celular (que va en z-[70]), solo `transform` y `opacity` —que corren en la GPU
 * y no recalculan la página— y `prefers-reduced-motion` deja la decoración
 * puesta pero quieta, en vez de borrarla.
 *
 * Nada de esto pesa en la descarga: son SVG escritos a mano, sin una sola
 * imagen. El icono de 2 MB que costó 11 s de LCP sigue siendo la lección.
 */

import { useTemporada } from '@/lib/temporada';

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

/** Araña de ocho patas, colgando de su hilo. */
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

/** Murciélago de perfil: plano a propósito, para que el aleteo lo estreche. */
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

/**
 * Los tres estados del borde de la sábana. Tienen EXACTAMENTE la misma
 * estructura de comandos —solo cambian las alturas de los picos— porque SMIL
 * interpola punto por punto: si un estado tuviera una curva de más, el fantasma
 * daría un salto en vez de ondear. La onda recorre la tela de izquierda a
 * derecha y vuelve.
 */
const SABANA = [
  'M35,4C50,4,58,15,58,30v33c0,4-4,5-6.5,2l-4.5,-8.5l-4,5c-1.6,2-4,2-5.6,0l-3.4,-1.2l-3.4,7.2c-1.6,2-4,2-5.6,0l-4,-8l-4.5,5.5C13,69,12,68,12,64V30C12,15,20,4,35,4Z',
  'M35,4C50,4,58,15,58,30v30c0,4-4,5-6.5,2l-4.5,-2.5l-4,8c-1.6,2-4,2-5.6,0l-3.4,-7.2l-3.4,4.2c-1.6,2-4,2-5.6,0l-4,-2l-4.5,8.5C13,72,12,71,12,67V30C12,15,20,4,35,4Z',
  'M35,4C50,4,58,15,58,30v33c0,4-4,5-6.5,2l-4.5,-8.5l-4,5c-1.6,2-4,2-5.6,0l-3.4,-1.2l-3.4,7.2c-1.6,2-4,2-5.6,0l-4,-8l-4.5,5.5C13,69,12,68,12,64V30C12,15,20,4,35,4Z',
].join(';');

/** Fantasma con la sábana ondeando. La onda va en SMIL, no en CSS: CSS no sabe
 *  interpolar la `d` de un path, y es justo lo que hace falta aquí. */
function Fantasma() {
  return (
    <svg viewBox="0 0 70 92" className="h-full w-full">
      <path fill="#f6f2ff" stroke="#6d28d9" strokeWidth="2" d={SABANA.split(';')[0]}>
        <animate attributeName="d" values={SABANA} dur="1.6s" repeatCount="indefinite" />
      </path>
      {/* bracitos */}
      <path fill="#f6f2ff" stroke="#6d28d9" strokeWidth="2" d="M11,34c-4,1-6,4-5,7c1,2.6,4,3,6,1z" />
      <path fill="#f6f2ff" stroke="#6d28d9" strokeWidth="2" d="M59,34c4,1,6,4,5,7c-1,2.6-4,3-6,1z" />
      {/* cara */}
      <ellipse cx="27" cy="28" rx="4.4" ry="5.8" fill="#4c1d95" />
      <ellipse cx="43" cy="28" rx="4.4" ry="5.8" fill="#4c1d95" />
      <path d="M30,41c1.6,3.4,8.4,3.4,10,0c-1.6,5-8.4,5-10,0z" fill="#4c1d95" />
    </svg>
  );
}

/**
 * Gato negro caminando. Las cuatro patas giran desde donde se unen al cuerpo,
 * en dos parejas cruzadas —delantera izquierda con trasera derecha— que es como
 * camina un gato de verdad; si las cuatro fueran a la vez, saltaría.
 * `transformBox: 'view-box'` para poder dar el centro de giro en coordenadas del
 * dibujo: con el `fill-box` por defecto, el eje de una pata inclinada cae en la
 * esquina de su caja y la pata gira desde el aire.
 */
function GatoCamina() {
  const eje = (x: number, y: number) => ({
    transformBox: 'view-box' as const,
    transformOrigin: `${x}px ${y}px`,
  });
  return (
    <svg viewBox="0 0 120 64" className="h-full w-full">
      {/* cola: se mueve aparte, con su propio ritmo */}
      <path
        className="gato-cola"
        d="M28,32c-10-2-16-12-13-22c1,8,7,14,14,15z"
        fill="currentColor"
        style={eje(30, 33)}
      />
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
      {/* el ojo ámbar: lo único que no es negro, y es lo que le da la mirada */}
      <circle cx="95" cy="22" r="2.2" fill="#f5a641" />
    </svg>
  );
}

/** Dónde cruza cada murciélago, cuánto tarda y cuándo entra. */
const VUELOS = [
  { arriba: '13%', tam: 40, dur: 22, retraso: 3, aleteo: 0.42, op: 0.4 },
  { arriba: '37%', tam: 28, dur: 31, retraso: 14, aleteo: 0.52, op: 0.32 },
  { arriba: '64%', tam: 34, dur: 26, retraso: 25, aleteo: 0.46, op: 0.28 },
];

export function DecoracionHalloween() {
  const temporada = useTemporada();
  if (temporada !== 'halloween') return null;

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-[55] overflow-hidden">
      {/* TELARAÑAS — marco fijo, por encima del encabezado y por debajo del
          menú del celular, que va en z-[70]. */}
      <div className="absolute left-0 top-0 h-24 w-24 text-ink/35 sm:h-36 sm:w-36 lg:h-44 lg:w-44">
        <Telarana />
      </div>
      <div className="absolute right-0 top-0 h-24 w-24 -scale-x-100 text-ink/35 sm:h-36 sm:w-36 lg:h-44 lg:w-44">
        <Telarana />
      </div>

      {/* ARAÑA — arranca por encima del borde para que el hilo nunca deje hueco
          al bajar. */}
      <div className="arana-cuelga absolute -top-7 left-[17%] flex flex-col items-center sm:left-[12%]">
        <span className="block w-px bg-ink/30" style={{ height: 'clamp(42px, 8vw, 80px)' }} />
        <span className="block h-5 w-6 text-ink/55 sm:h-7 sm:w-8">
          <Arana />
        </span>
      </div>

      {/* MURCIÉLAGOS */}
      {VUELOS.map((v, i) => (
        <span
          key={i}
          className="murcielago-cruza absolute text-ink"
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

      {/* FANTASMA — atraviesa la pantalla por la mitad. Entra y sale
          desvaneciéndose, y pasa la mayor parte del ciclo invisible: si
          estuviera siempre ahí dejaría de ser una aparición. */}
      <span
        className="fantasma-pasa absolute"
        style={{ top: '32%', width: 'clamp(74px, 8vw, 104px)', height: 'clamp(97px, 10.5vw, 137px)' }}
      >
        <span className="fantasma-flota block h-full w-full">
          <Fantasma />
        </span>
      </span>

      {/* GATO — camina por el borde de abajo. Se para sobre el borde inferior
          del viewport, que es donde el ojo espera que esté el suelo. */}
      <span
        className="gato-pasea absolute bottom-0"
        style={{ width: 'clamp(92px, 11vw, 150px)', height: 'clamp(49px, 5.9vw, 80px)', color: 'rgba(28,27,34,0.82)' }}
      >
        <GatoCamina />
      </span>
    </div>
  );
}
