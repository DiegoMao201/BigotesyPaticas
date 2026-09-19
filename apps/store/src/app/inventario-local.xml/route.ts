/**
 * Feed de INVENTARIO LOCAL para Google Merchant Center.
 *
 * Es el que habilita las "Fichas locales sin coste": los productos que hay HOY en
 * el local aparecen gratis en la Búsqueda de Google, en Maps, en la pestaña
 * Shopping, en Imágenes y en Lens, con el sello de disponible en tienda. Colombia
 * está soportado. Es la palanca más directa para el objetivo de Diego: salir
 * primero en las búsquedas de mascotas en Pereira y Dosquebradas.
 *
 * En Merchant Center: Productos → Fuentes de datos → Añadir → Inventario local
 *   https://bigotesypaticas.com/inventario-local.xml
 *
 * OJO con `store_code`: tiene que ser EXACTAMENTE el código de tienda que aparece
 * en Merchant Center → Información de empresa → Tiendas (viene del Perfil de
 * Empresa). Si no coincide, Google rechaza el feed entero con "[Perfil de Empresa]
 * Código de tienda no válido" — nos pasó el 18-sep-2026 con las 522 filas.
 *
 * Por eso el código se puede pasar de tres formas, en este orden:
 *   1. En la propia URL:  /inventario-local.xml?store=EL_CODIGO   ← la más rápida,
 *      se cambia desde Merchant Center sin tocar el código ni redesplegar.
 *      Admite VARIOS separados por coma: ?store=A,B,C. Entonces cada producto
 *      sale una vez por código. Sirve para dos cosas: el día que haya un segundo
 *      local, y para averiguar el código cuando Google no lo enseña por ningún
 *      lado — se mandan los candidatos y su informe de errores dice cuál acepta.
 *   2. Variable de entorno MERCHANT_STORE_CODE.
 *   3. El código del local, fijo aquí abajo. Es el camino normal: la URL que
 *      Merchant Center tiene registrada va limpia, sin parámetros.
 */

// La respuesta depende de ?store=, así que se genera por petición. El coste real
// es bajo: los datos de la API siguen cacheados 30 min (el stock cambia durante
// el día) y Google consulta el feed una vez al día.
export const dynamic = 'force-dynamic';

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

// El código del local de Samara Plaza Mall, el que Diego encontró en el Perfil de
// Empresa el 18-sep-2026 tras descartar 'MAIN' y el ID de la cuenta omnicanal.
const STORE_POR_DEFECTO = process.env.MERCHANT_STORE_CODE || '16216148396074054431';
const POR_PAGINA = 100;

type ProductoInv = {
  slug: string;
  sku: string | null;
  price: string;
  compare_at_price: string | null;
  primary_image_url: string | null;
  in_stock: boolean;
  stock_qty?: number;
};

function esc(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

async function traerPagina(page: number): Promise<ProductoInv[]> {
  try {
    const res = await fetch(
      `${API}/v1/products?is_published=true&per_page=${POR_PAGINA}&page=${page}`,
      { next: { revalidate: 1800 }, headers: { Accept: 'application/json' } },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as { items?: ProductoInv[] };
    return data.items ?? [];
  } catch {
    return [];
  }
}

export async function GET(request: Request) {
  const pedido = new URL(request.url).searchParams.get('store');
  const codigos = (pedido ?? STORE_POR_DEFECTO)
    .split(',')
    .map((c) => c.trim())
    .filter(Boolean);
  if (codigos.length === 0) codigos.push(STORE_POR_DEFECTO);

  const items: string[] = [];
  let page = 1;

  while (page <= 30) {
    const lote = await traerPagina(page);
    if (lote.length === 0) break;

    for (const p of lote) {
      const precio = Number(p.price);
      // Mismos descartes que merchant.xml: un id que no existe en el feed de
      // productos no se puede emparejar y Google lo cuenta como no coincidente.
      if (!precio || precio <= 0 || !p.primary_image_url) continue;

      const cantidad = Number(p.stock_qty ?? 0);
      const hay = p.in_stock && cantidad > 0;
      // Un producto agotado también se envía: Google necesita saber que existe en
      // esta tienda pero no está disponible, si no lo da por inexistente.
      const disponibilidad = hay ? (cantidad <= 3 ? 'limited_availability' : 'in_stock') : 'out_of_stock';
      const antes = p.compare_at_price ? Number(p.compare_at_price) : 0;
      const enOferta = antes > precio;

      for (const codigo of codigos) {
        items.push(
          [
            '    <item>',
            `      <g:id>${esc(p.sku || p.slug)}</g:id>`,
            `      <g:store_code>${esc(codigo)}</g:store_code>`,
            `      <g:availability>${disponibilidad}</g:availability>`,
            ...(hay ? [`      <g:quantity>${cantidad}</g:quantity>`] : []),
            `      <g:price>${(enOferta ? antes : precio).toFixed(2)} COP</g:price>`,
            ...(enOferta ? [`      <g:sale_price>${precio.toFixed(2)} COP</g:sale_price>`] : []),
            `      <g:pickup_method>buy</g:pickup_method>`,
            `      <g:pickup_sla>same_day</g:pickup_sla>`,
            '    </item>',
          ].join('\n'),
        );
      }
    }

    if (lote.length < POR_PAGINA) break;
    page++;
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Bigotes y Paticas — inventario en tienda</title>
    <link>https://bigotesypaticas.com</link>
    <description>Disponibilidad en el local de Samara Plaza Mall, Dosquebradas (códigos de tienda: ${esc(codigos.join(', '))})</description>
${items.join('\n')}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=1800, stale-while-revalidate=3600',
      // Sirve para verificar de un vistazo con qué código salió el feed.
      'X-Store-Code': codigos.join(','),
    },
  });
}
