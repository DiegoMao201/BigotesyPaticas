/**
 * /resenas.xml — feed de valoraciones de productos para Google Merchant Center.
 *
 * POR QUÉ IMPORTA. Las fichas de Bigotes y Paticas salen sin estrellas. La tienda
 * tiene 5,0 en su ficha de Google, pero esa reputación es del NEGOCIO y no se
 * traslada al catálogo: para que un producto muestre estrellas en Shopping, en la
 * Búsqueda y en las fichas gratuitas, Google necesita este archivo aparte.
 *
 * En Merchant Center: Marketing → Valoraciones de productos → subir este archivo.
 * Es el programa gratuito; no confundir con "Opiniones de clientes", que califica
 * a la tienda y se activa por separado.
 *
 * DE DÓNDE SALEN LAS RESEÑAS. De catalog.product_reviews, que ya existía: las
 * escriben los clientes desde el portal sobre pedidos entregados, y pasan por
 * moderación en el admin. Aquí solo salen las que están en 'approved' o
 * 'auto_published', y solo de productos publicados.
 *
 * Formato: Product Reviews Feed de Google. Los nombres de las etiquetas y el orden
 * los fija Google, no nosotros; cambiarlos invalida el archivo entero.
 */

export const revalidate = 3600;

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

const BASE = 'https://bigotesypaticas.com';
const POR_PAGINA = 500;

type Resena = {
  id: string;
  product_slug: string;
  product_sku: string | null;
  product_name: string;
  rating: number;
  title: string | null;
  comment: string | null;
  reviewer: string;
  is_verified_purchase: boolean;
  created_at: string | null;
};

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

/** Google rechaza el archivo si una fecha no es ISO 8601 con zona horaria. */
function fecha(iso: string | null): string {
  const d = iso ? new Date(iso) : new Date();
  return (Number.isNaN(d.getTime()) ? new Date() : d).toISOString();
}

async function traerPagina(page: number): Promise<{ items: Resena[]; total: number }> {
  try {
    const res = await fetch(`${API}/v1/reviews/feed?page=${page}&page_size=${POR_PAGINA}`, {
      next: { revalidate: 3600 },
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) return { items: [], total: 0 };
    return (await res.json()) as { items: Resena[]; total: number };
  } catch {
    return { items: [], total: 0 };
  }
}

export async function GET() {
  const todas: Resena[] = [];
  let page = 1;
  while (page <= 20) {
    const { items } = await traerPagina(page);
    if (items.length === 0) break;
    todas.push(...items);
    if (items.length < POR_PAGINA) break;
    page++;
  }

  const reviews = todas
    .filter((r) => r.rating >= 1 && r.rating <= 5 && (r.comment || r.title))
    .map((r) => {
      const texto = [r.title, r.comment].filter(Boolean).join('. ');
      const url = `${BASE}/producto/${encodeURIComponent(r.product_slug)}`;
      return [
        '    <review>',
        `      <review_id>${esc(r.id)}</review_id>`,
        '      <reviewer>',
        `        <name>${esc(r.reviewer)}</name>`,
        '      </reviewer>',
        `      <review_timestamp>${fecha(r.created_at)}</review_timestamp>`,
        `      <content>${esc(texto.slice(0, 4000))}</content>`,
        `      <review_url type="group">${url}#resenas</review_url>`,
        '      <ratings>',
        `        <overall min="1" max="5">${r.rating}</overall>`,
        '      </ratings>',
        '      <products>',
        '        <product>',
        '          <product_ids>',
        // Sin código de barras en el catálogo: se empareja por SKU, igual que
        // hace merchant.xml, que manda ese mismo valor como g:id y g:mpn.
        ...(r.product_sku
          ? ['            <skus>', `              <sku>${esc(r.product_sku)}</sku>`, '            </skus>']
          : []),
        '          </product_ids>',
        `          <product_name>${esc(r.product_name.slice(0, 150))}</product_name>`,
        `          <product_url>${url}</product_url>`,
        '        </product>',
        '      </products>',
        // Compra verificada: es la señal que más peso le da Google a una reseña.
        `      <is_spam>false</is_spam>`,
        ...(r.is_verified_purchase
          ? ['      <collection_method>post_fulfillment</collection_method>']
          : []),
        '    </review>',
      ].join('\n');
    });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns:vc="http://www.w3.org/2007/XMLSchema-versioning"
      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
      xsi:noNamespaceSchemaLocation="http://www.google.com/shopping/reviews/schema/product/2.3/product_reviews.xsd">
  <version>2.3</version>
  <aggregator>
    <name>Bigotes y Paticas Tienda de Mascotas</name>
  </aggregator>
  <publisher>
    <name>Bigotes y Paticas Tienda de Mascotas</name>
    <favicon>${BASE}/favicon.ico</favicon>
  </publisher>
  <reviews>
${reviews.join('\n')}
  </reviews>
</feed>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400',
      'X-Total-Resenas': String(reviews.length),
    },
  });
}
