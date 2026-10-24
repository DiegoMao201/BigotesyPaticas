'use client';
import { useEffect, useState } from 'react';

/**
 * true cuando el visitante toca, hace scroll o teclea, o a los `ms` de cargar la
 * página, lo que pase primero.
 *
 * 24-oct-2026: gtag.js (191 KB), la etiqueta de Ads (149 KB) y fbevents.js (111 KB)
 * se ejecutaban justo cuando la página intentaba pintarse; en un celular la portada
 * quedaba en blanco 2,6 s y PageSpeed medía 10,7 s de LCP. Cargados así, llegan
 * cuando la página ya se ve. No se pierde nada: gtag y fbq quedan definidos al
 * instante como colas, y los scripts procesan la cola al llegar (un clic a WhatsApp
 * es una interacción, así que también dispara la carga).
 */
export function useCargaDiferida(ms = 2500): boolean {
  const [listo, setListo] = useState(false);
  useEffect(() => {
    if (listo) return;
    const ya = () => setListo(true);
    const eventos = ['pointerdown', 'scroll', 'keydown', 'touchstart'] as const;
    eventos.forEach((e) => window.addEventListener(e, ya, { once: true, passive: true }));
    const t = window.setTimeout(ya, ms);
    return () => {
      window.clearTimeout(t);
      eventos.forEach((e) => window.removeEventListener(e, ya));
    };
  }, [listo, ms]);
  return listo;
}
