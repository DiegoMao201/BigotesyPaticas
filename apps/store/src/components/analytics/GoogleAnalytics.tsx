'use client';
import Script from 'next/script';
import { useCargaDiferida } from './useCargaDiferida';

declare global {
  interface Window {
    gtag?: (...args: unknown[]) => void;
    dataLayer: unknown[];
  }
}

// La misma etiqueta de Google sirve para Analytics y para Ads: se cargan los dos
// identificadores sobre el MISMO gtag.js, sin añadir otro script ni peso. Sin el
// de Ads, Google Ads no puede saber que un clic pagado acabó en un WhatsApp, y
// paga a ciegas (24-sep-2026).
const ADS_ID = 'AW-17938999985';

export function GoogleAnalytics() {
  const GA_ID = process.env.NEXT_PUBLIC_GA4_ID;
  const cargar = useCargaDiferida();
  if (!GA_ID) return null;

  return (
    <>
      {/* 24-oct-2026: gtag.js (191 KB) + la etiqueta de Ads (149 KB) se pedían a los
          0,5 s, junto con la página, y en un celular 4G le quitaban ancho de banda a la
          imagen principal: PageSpeed medía 10,7 s de LCP. Ahora el script grande llega con
          la primera interacción o a los 2,5 s (useCargaDiferida). No se pierde nada:
          ga4-init define gtag y la cola dataLayer al instante, y gtag.js la procesa. */}
      {cargar && (
        <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
      )}
      <Script id="ga4-init" strategy="afterInteractive">
        {`
          window.dataLayer = window.dataLayer || [];
          function gtag(){dataLayer.push(arguments);}
          gtag('js', new Date());
          gtag('config', '${GA_ID}', {
            page_path: window.location.pathname,
            cookie_flags: 'samesite=none;secure'
          });
          ${ADS_ID ? `gtag('config', '${ADS_ID}');` : ''}
        `}
      </Script>
    </>
  );
}
