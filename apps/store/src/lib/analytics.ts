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

export function trackBeginCheckout(items: { id: string; name: string; price: number; quantity: number }[], value: number) {
  trackEvent('begin_checkout', {
    currency: 'COP',
    value,
    items: items.map((i) => ({
      item_id: i.id,
      item_name: i.name,
      price: i.price,
      quantity: i.quantity,
    })),
  });
}

/**
 * La huella de Google de ESTA visita, para que la compra se le pueda acreditar.
 *
 * GA4 no atribuye por teléfono ni por IP: atribuye por el id de la cookie `_ga` del
 * navegador. La venta de la tienda no se confirma aquí —se confirma cuando el admin
 * marca el pedido como entregado, horas después, desde otro computador—, así que el
 * `purchase` lo manda la API. Para que Google sepa que esa compra es de ESTE visitante
 * hay que guardar su client_id con el pedido; sin eso la venta entra como "(direct)" y
 * la búsqueda o el anuncio que trajo al cliente no recibe el crédito.
 *
 * Cookies de GA4:
 *   _ga               = "GA1.1.<client_id_1>.<client_id_2>"  → client_id = los dos últimos
 *   _ga_<ID sin G->   = "GS1.1.<session_id>.<n>.<…>"         → session_id = el 3er campo
 *
 * Si el cliente trae las cookies bloqueadas devuelve todo vacío: el pedido se guarda
 * igual y la API manda la compra con un id de respaldo. Se cuenta la venta aunque no se
 * pueda atribuir — eso es decisión tomada, es mejor que no contarla.
 */
export function huellaGoogle(): { ga_client_id?: string; ga_session_id?: string; gclid?: string } {
  if (typeof document === 'undefined') return {};
  const out: { ga_client_id?: string; ga_session_id?: string; gclid?: string } = {};
  try {
    const cookies = document.cookie.split(';').map((c) => c.trim());

    const ga = cookies.find((c) => c.startsWith('_ga='));
    if (ga) {
      // "_ga=GA1.1.1234567890.1696118400" → "1234567890.1696118400"
      const partes = ga.slice(4).split('.');
      if (partes.length >= 4) out.ga_client_id = partes.slice(-2).join('.');
    }

    const sesion = cookies.find((c) => /^_ga_[A-Z0-9]+=/.test(c));
    if (sesion) {
      // El formato de esta cookie CAMBIÓ y nos costó tres días de pedidos perdidos.
      //   GS1 (viejo): "GS1.1.1696118400.3.1.1696118500.0.0.0"       → partes[2] = "1696118400"
      //   GS2 (nuevo): "GS2.1.s1759600000$o5$g1$t1759600123$j60$l0$h0" → partes[2] = todo ese bloque
      // Con GS2, partes[2] trae 39 caracteres y la API lo rechazaba con 422: el
      // pedido ENTERO se perdía por un dato de medición. El id de sesión es el
      // número que sigue a la "s", antes del primer "$".
      const partes = sesion.split('=')[1]?.split('.') ?? [];
      if (partes.length >= 3) {
        const bruto = partes[2] ?? '';
        const gs2 = /^s(\d+)/.exec(bruto);
        const id = gs2 ? gs2[1] : bruto;
        // El recorte es el último seguro: la columna es varchar(32).
        if (id) out.ga_session_id = id.slice(0, 32);
      }
    }

    // El gclid llega en la URL del anuncio y lo guardamos al entrar (ver más abajo).
    const guardado = sessionStorage.getItem('bp_gclid');
    const url = new URLSearchParams(window.location.search).get('gclid');
    if (url) {
      sessionStorage.setItem('bp_gclid', url);
      out.gclid = url;
    } else if (guardado) {
      out.gclid = guardado;
    }
  } catch {
    // cookies bloqueadas o sessionStorage inaccesible (modo incógnito estricto)
  }
  return out;
}

/** Guarda el gclid en cuanto el visitante entra por un anuncio, antes de que navegue. */
export function recordarGclid() {
  if (typeof window === 'undefined') return;
  try {
    const g = new URLSearchParams(window.location.search).get('gclid');
    if (g) sessionStorage.setItem('bp_gclid', g);
  } catch {
    // sin sessionStorage: el gclid se pierde, el pedido se guarda igual
  }
}
