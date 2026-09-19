/**
 * Feed de productos para Google Merchant Center.
 *
 * Diego (18-sep-2026): "ojo que la ficha de merchant se debe actualizar bien
 * siempre automático con la url". Hasta hoy Merchant tomaba los productos
 * RASTREANDO el sitio (lee los datos estructurados de cada página), y eso tarda
 * días en reflejar un cambio de precio o de stock. Con este feed, Google lee una
 * sola URL y trae el catálogo completo cada vez que la consulta.
 *
 * En Merchant Center: Productos → Fuentes de datos → Añadir → "Feed desde una URL"
 *   https://bigotesypaticas.com/merchant.xml
 * Programarlo a diario. El feed se regenera cada hora (revalidate).
 */

export const revalidate = 3600;

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

const BASE = 'https://bigotesypaticas.com';
// La API topa per_page en 100 (mismo límite que descubrimos en el sitemap el 13-sep).
const POR_PAGINA = 100;

type ProductoFeed = {
  slug: string;
  sku: string | null;
  name: string;
  short_description: string | null;
  description?: string | null;
  price: string;
  compare_at_price: string | null;
  primary_image_url: string | null;
  images?: string[];
  in_stock: boolean;
  stock_qty: number;
  brand?: { name: string } | null;
  category?: { name: string } | null;
};

/**
 * La imagen que se le manda a Google, pasada por /img-feed para que llegue a
 * 1000x1000. Medimos el catálogo el 18-sep-2026: solo 14 de 520 fotos llegaban a
 * los 500 px que Google exige, así que las estaba rechazando por tandas. Ver el
 * comentario de apps/store/src/app/img-feed/[slug]/route.ts.
 *
 * Si la URL no tiene la forma esperada del CDN, se manda tal cual: mejor la foto
 * original que ninguna.
 */
const RE_CDN = /\/bigotesypaticas\/products\/([a-z0-9][a-z0-9-]*)\/main\.webp$/;

function imagenParaGoogle(url: string): string {
  const m = RE_CDN.exec(url);
  return m ? `${BASE}/img-feed/${m[1]}.jpg` : url;
}

function esc(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Limpia la descripción: sin HTML, sin saltos raros y con un largo que Merchant acepta. */
function descripcion(p: ProductoFeed): string {
  const base =
    (p.short_description || p.description || `${p.name} disponible en Bigotes y Paticas.`)
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  const texto = base.length < 40 ? `${base} Tienda de mascotas en Dosquebradas, con domicilio en Pereira y Dosquebradas.` : base;
  return texto.slice(0, 4900);
}

async function traerPagina(page: number): Promise<ProductoFeed[]> {
  try {
    const res = await fetch(
      `${API}/v1/products?is_published=true&per_page=${POR_PAGINA}&page=${page}`,
      { next: { revalidate: 3600 }, headers: { Accept: 'application/json' } },
    );
    if (!res.ok) return [];
    const data = (await res.json()) as { items?: ProductoFeed[] };
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
      // Merchant rechaza un producto sin precio o sin imagen: mejor no enviarlo
      // que ensuciar la cuenta con errores.
      if (!precio || precio <= 0 || !p.primary_image_url) continue;

      const antes = p.compare_at_price ? Number(p.compare_at_price) : 0;
      const enOferta = antes > precio;
      const extras = (p.images ?? []).filter((u) => u && u !== p.primary_image_url).slice(0, 10);

      items.push(
        [
          '    <item>',
          `      <g:id>${esc(p.sku || p.slug)}</g:id>`,
          `      <g:title>${esc(p.name.slice(0, 150))}</g:title>`,
          `      <g:description>${esc(descripcion(p))}</g:description>`,
          `      <g:link>${BASE}/producto/${encodeURIComponent(p.slug)}</g:link>`,
          `      <g:image_link>${esc(imagenParaGoogle(p.primary_image_url))}</g:image_link>`,
          ...extras.map((u) => `      <g:additional_image_link>${esc(imagenParaGoogle(u))}</g:additional_image_link>`),
          `      <g:availability>${p.in_stock && p.stock_qty > 0 ? 'in_stock' : 'out_of_stock'}</g:availability>`,
          `      <g:price>${(enOferta ? antes : precio).toFixed(2)} COP</g:price>`,
          ...(enOferta ? [`      <g:sale_price>${precio.toFixed(2)} COP</g:sale_price>`] : []),
          `      <g:condition>new</g:condition>`,
          `      <g:brand>${esc(p.brand?.name || 'Bigotes y Paticas')}</g:brand>`,
          `      <g:mpn>${esc(p.sku || p.slug)}</g:mpn>`,
          // Sin código de barras en la base: se lo decimos a Google para que no
          // marque el producto como incompleto.
          `      <g:identifier_exists>no</g:identifier_exists>`,
          ...(p.category?.name ? [`      <g:product_type>${esc(p.category.name)}</g:product_type>`] : []),
          `      <g:google_product_category>Animals &amp; Pet Supplies &gt; Pet Supplies</g:google_product_category>`,
          `      <g:shipping><g:country>CO</g:country><g:service>Domicilio Pereira y Dosquebradas</g:service><g:price>${precio >= 30000 ? '0.00' : '5000.00'} COP</g:price></g:shipping>`,
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
    <title>Bigotes y Paticas — Tienda de Mascotas</title>
    <link>${BASE}</link>
    <description>Concentrados, accesorios y medicamentos para perros y gatos. Domicilio en Pereira y Dosquebradas.</description>
${items.join('\n')}
  </channel>
</rss>`;

  return new Response(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}
