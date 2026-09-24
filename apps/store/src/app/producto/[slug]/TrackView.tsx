'use client';

import { useEffect, useRef } from 'react';
import { trackViewItem } from '@/lib/analytics';

/**
 * Avisa a Analytics de que alguien VIO este producto.
 *
 * El 24-sep-2026 Analytics medía cero comercio: no había ni un `view_item`, así
 * que no se sabía qué productos mira la gente ni cuántos de los que miran
 * terminan agregando. `trackViewItem` ya estaba escrito y nadie lo llamaba.
 *
 * La página de producto es un componente de servidor, por eso este trocito
 * aparte. El `useRef` evita que se dispare dos veces en desarrollo (React monta
 * dos veces en modo estricto y duplicaría el dato).
 */
export function TrackView({
  id, name, price, category, brand,
}: { id: string; name: string; price: number; category?: string; brand?: string }) {
  const enviado = useRef(false);
  useEffect(() => {
    if (enviado.current) return;
    enviado.current = true;
    trackViewItem({ id, name, price, category, brand });
  }, [id, name, price, category, brand]);
  return null;
}
