'use client';
import Script from 'next/script';

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
  if (!GA_ID) return null;

  return (
    <>
      <Script
        src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`}
        strategy="afterInteractive"
      />
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
