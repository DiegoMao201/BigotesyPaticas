/**
 * Cola de eventos que llegaron antes que gtag.
 *
 * `GoogleAnalytics` carga gtag.js con `strategy="afterInteractive"`, o sea
 * DESPUÉS de la hidratación. Un `useEffect` que dispara al montar —el caso de
 * `view_item` en la ficha de producto— corre ANTES de que exista `window.gtag`,
 * y la versión anterior de `trackEvent` se rendía en silencio: el evento se
 * perdía sin dejar rastro. Por eso el 25-sep-2026 Analytics tenía `page_view`
 * (lo emite el propio `gtag('config')`) y `whatsapp_float_click` (el usuario
 * hace clic segundos después, cuando gtag ya cargó), pero CERO `view_item`.
 *
 * Los eventos que llegan temprano se guardan y se envían en cuanto gtag
 * aparece. Después de 10 s se descartan: si gtag no cargó, no va a cargar.
 */
const enEspera: Array<[string, Record<string, unknown>]> = [];
let vigilando = false;

function vigilarGtag() {
  if (vigilando) return;
  vigilando = true;
  const desde = Date.now();
  const reloj = window.setInterval(() => {
    if (typeof window.gtag === 'function') {
      window.clearInterval(reloj);
      vigilando = false;
      let siguiente = enEspera.shift();
      while (siguiente) {
        window.gtag('event', siguiente[0], siguiente[1]);
        siguiente = enEspera.shift();
      }
    } else if (Date.now() - desde > 10_000) {
      window.clearInterval(reloj);
      vigilando = false;
      enEspera.length = 0;
    }
  }, 200);
}

export function trackEvent(name: string, params: Record<string, unknown> = {}) {
  if (typeof window === 'undefined') return;
  if (typeof window.gtag === 'function') {
    window.gtag('event', name, params);
    return;
  }
  enEspera.push([name, params]);
  vigilarGtag();
}

export function trackViewItem(product: {
  id: string;
  name: string;
  category?: string;
  brand?: string;
  price: number;
}) {
  trackEvent('view_item', {
    currency: 'COP',
    value: product.price,
    items: [{
      item_id: product.id,
      item_name: product.name,
      item_category: product.category,
      item_brand: product.brand,
      price: product.price,
      quantity: 1,
    }],
  });
}

export function trackAddToCart(product: {
  id: string;
  name: string;
  price: number;
  quantity?: number;
}) {
  trackEvent('add_to_cart', {
    currency: 'COP',
    value: product.price * (product.quantity ?? 1),
    items: [{
      item_id: product.id,
      item_name: product.name,
      price: product.price,
      quantity: product.quantity ?? 1,
    }],
  });
}

export function trackSearch(query: string) {
  trackEvent('search', { search_term: query });
}
