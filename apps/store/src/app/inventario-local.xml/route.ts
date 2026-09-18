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
 * en Merchant Center → Tiendas físicas (viene del Perfil de Empresa). Se configura
 * con la variable de entorno MERCHANT_STORE_CODE; si no está, usa el código de la
 * ubicación por defecto del inventario.
 */

export const revalidate = 1800; // el stock cambia durante el día: cada 30 min

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

const STORE_CODE = process.env.MERCHANT_STORE_CODE || 'MAIN';
const POR_PAGINA = 100;

type ProductoInv = {
  slug: string;
  sku: string | null;
  price: string;
  compare_at_price: string | null;
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

export async function GET() {
  const items: string[] = [];
  let page = 1;

  while (page <= 30) {
    const lote = await traerPagina(page);
    if (lote.length === 0) break;

    for (const p of lote) {
      const precio = Number(p.price);
      if (!precio || precio <= 0) continue;

      const cantidad = Number(p.stock_qty ?? 0);
      const hay = p.in_stock && cantidad > 0;
      // Un producto agotado también se envía: Google necesita saber que existe en
      // esta tienda pero no está disponible, si no lo da por inexistente.
      const disponibilidad = hay ? (cantidad <= 3 ? 'limited_availability' : 'in_stock') : 'out_of_stock';
      const antes = p.compare_at_price ? Number(p.compare_at_price) : 0;
      const enOferta = antes > precio;

      items.push(
        [
          '    <item>',
          `      <g:id>${esc(p.sku || p.slug)}</g:id>`,
          `      <g:store_code>${esc(STORE_CODE)}</g:store_code>`,
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

    if (lote.length < POR_PAGINA) break;
    page++;
  }

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:g="http://base.google.com/ns/1.0">
  <channel>
    <title>Bigotes y Paticas — inventario en tienda</title>
    <link>https://bigotesypaticas.com</link>
    <description>Disponibilidad en el local de Samara Plaza Mall, Dosquebradas</description>
${items.join('\n')}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=1800, stale-while-revalidate=3600',
    },
  });
}
