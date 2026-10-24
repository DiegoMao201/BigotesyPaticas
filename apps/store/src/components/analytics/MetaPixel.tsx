'use client';
import Script from 'next/script';
import { useCargaDiferida } from './useCargaDiferida';

export function MetaPixel() {
  const pixelId = process.env.NEXT_PUBLIC_META_PIXEL_ID;
  const cargar = useCargaDiferida();

  if (!pixelId || pixelId === 'PENDIENTE_DIEGO_CREA_BM') return null;

  return (
    <>
      {/* 24-oct-2026: el fragmento oficial inyectaba fbevents.js (111 KB + 33 KB de
          configuración) al instante y competía con la imagen principal en celular. Aquí
          se crea solo la cola fbq (igual que el fragmento, sin pedir el script) y
          fbevents.js llega con la primera interacción o a los 2,5 s: al llegar procesa fbq.queue, así que
          el PageView y los eventos no se pierden. */}
      <Script
        id="meta-pixel"
        strategy="afterInteractive"
        dangerouslySetInnerHTML={{
          __html: `
            !function(f){if(f.fbq)return;var n=f.fbq=function(){n.callMethod?
            n.callMethod.apply(n,arguments):n.queue.push(arguments)};
            if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';n.queue=[]}(window);
            fbq('init', '${pixelId}');
            fbq('track', 'PageView');
          `,
        }}
      />
      {cargar && <Script src="https://connect.facebook.net/en_US/fbevents.js" strategy="afterInteractive" />}
      {/* Sin <noscript><img>: Next la convertía en un <link rel="preload" as="image">
          de facebook.com/tr que se pedía en CADA visita junto con la imagen principal,
          para contar a la poca gente que navega sin JavaScript. */}
    </>
  );
}
