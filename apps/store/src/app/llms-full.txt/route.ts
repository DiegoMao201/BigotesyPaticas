/**
 * /llms-full.txt — la versión completa para los modelos de lenguaje: lo mismo que
 * /llms.txt más el catálogo publicado, producto por producto, con el precio y la
 * disponibilidad que tiene la base en este momento. Nada se escribe a mano: sale
 * de la misma API que alimenta la tienda y el feed de Merchant.
 */
import { BASE, TEXTO } from '@/lib/llms-texto';

export const revalidate = 3600;

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

type Producto = {
  slug: string;
  name: string;
  short_description: string | null;
  price: string;
  compare_at_price: string | null;
  in_stock: boolean;
  brand?: { name: string } | null;
  category?: { name: string } | null;
};

async function traerPagina(page: number): Promise<Producto[]> {
  try {
    const res = await fetch(`${API}/v1/products?is_published=true&per_page=100&page=${page}`, {
      next: { revalidate: 3600 },
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) return [];
    const data = (await res.json()) as { items?: Producto[] };
    return data.items ?? [];
  } catch {
    return [];
  }
}

const pesos = (n: number) => `$${Math.round(n).toLocaleString('es-CO')} COP`;
const limpio = (t: string | null) => (t ?? '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 220);

export async function GET() {
  const porCategoria = new Map<string, string[]>();
  let total = 0;
  for (let page = 1; page <= 30; page++) {
    const lote = await traerPagina(page);
    if (lote.length === 0) break;
    for (const p of lote) {
      const precio = Number(p.price);
      if (!precio || precio <= 0) continue;
      const antes = p.compare_at_price ? Number(p.compare_at_price) : 0;
      const cat = p.category?.name ?? 'Otros';
      const linea =
        `- [${p.name}](${BASE}/producto/${p.slug})` +
        `${p.brand?.name ? ` · ${p.brand.name}` : ''} · ${pesos(precio)}` +
        `${antes > precio ? ` (antes ${pesos(antes)})` : ''}` +
        ` · ${p.in_stock ? 'disponible' : 'agotado'}` +
        `${limpio(p.short_description) ? ` · ${limpio(p.short_description)}` : ''}`;
      porCategoria.set(cat, [...(porCategoria.get(cat) ?? []), linea]);
      total++;
    }
  }

  const fecha = new Intl.DateTimeFormat('es-CO', { dateStyle: 'long', timeStyle: 'short', timeZone: 'America/Bogota' }).format(new Date());
  const catalogo = total
    ? `## Catálogo completo (${total} productos)\n\nPrecios en pesos colombianos y disponibilidad leídos de la tienda el ${fecha} (hora de Colombia). Cambian a diario: la página de cada producto manda.\n\n` +
      [...porCategoria.entries()]
        .sort((a, b) => a[0].localeCompare(b[0], 'es'))
        .map(([cat, lineas]) => `### ${cat}\n\n${lineas.join('\n')}`)
        .join('\n\n')
    : `## Catálogo completo\n\nEl catálogo no se pudo leer en este momento. Está completo en ${BASE}/categorias/todos`;

  return new Response(`${TEXTO}\n${catalogo}\n`, {
    headers: {
      'Content-Type': 'text/plain; charset=utf-8',
      'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400',
    },
  });
}
