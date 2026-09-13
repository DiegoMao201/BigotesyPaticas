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
 */

const HUELLAS = [
  { izq: '2%', arriba: '12%', tam: 46, color: '#187f77', giro: -18, dur: 11, retraso: 0, op: 0.13 },
  { izq: '6%', arriba: '46%', tam: 30, color: '#f5a641', giro: 22, dur: 14, retraso: 2.5, op: 0.16 },
  { izq: '3%', arriba: '74%', tam: 38, color: '#0d4a45', giro: 8, dur: 12.5, retraso: 1.2, op: 0.1 },
  { der: '3%', arriba: '20%', tam: 34, color: '#f5a641', giro: 14, dur: 13, retraso: 0.8, op: 0.15 },
  { der: '7%', arriba: '55%', tam: 44, color: '#187f77', giro: -26, dur: 10.5, retraso: 3.1, op: 0.12 },
  { der: '2%', arriba: '84%', tam: 28, color: '#0d4a45', giro: 32, dur: 15, retraso: 1.9, op: 0.11 },
];

function Huella({ tam, color, giro }: { tam: number; color: string; giro: number }) {
  return (
    <svg
      width={tam}
      height={tam}
      viewBox="0 0 64 64"
      fill={color}
      style={{ transform: `rotate(${giro}deg)` }}
    >
      <ellipse cx="20" cy="17" rx="7.5" ry="10" />
      <ellipse cx="33.5" cy="12" rx="7" ry="10.5" />
      <ellipse cx="46" cy="18" rx="7" ry="9.5" />
      <ellipse cx="53" cy="31" rx="6.5" ry="8.5" />
      <path d="M34 28c9 0 16 7 16 14 0 6-5 9-11 9-3 0-4 1-5 1s-2-1-5-1c-6 0-11-3-11-9 0-7 7-14 16-14z" />
    </svg>
  );
}

export function HuellasFondo() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 hidden overflow-hidden lg:block"
    >
      {HUELLAS.map((h, i) => (
        <span
          key={i}
          className="huella-flota absolute"
          style={{
            left: h.izq,
            right: h.der,
            top: h.arriba,
            opacity: h.op,
            animationDuration: `${h.dur}s`,
            animationDelay: `${h.retraso}s`,
          }}
        >
          <Huella tam={h.tam} color={h.color} giro={h.giro} />
        </span>
      ))}
    </div>
  );
}
