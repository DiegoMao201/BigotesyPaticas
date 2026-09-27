import { useEffect, useState } from 'react';

/**
 * true solo después de montar en el navegador. El carrito y la ubicación viven en
 * localStorage: el servidor no los conoce y pinta "vacío". Si el cliente pinta otra
 * cosa en el primer render, React descarta TODO el HTML del servidor y re-dibuja la
 * página (parpadeo y carga más lenta en cada página con algo en el carrito).
 */
export function useMounted(): boolean {
  const [m, setM] = useState(false);
  useEffect(() => setM(true), []);
  return m;
}
