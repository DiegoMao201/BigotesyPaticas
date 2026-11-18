import type { MetadataRoute } from 'next';
import { ZONAS } from '@/data/zonas';

export const revalidate = 3600; // regenerar cada hora

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

const BASE = 'https://bigotesypaticas.com';

// 18-nov-2026: antes un fallo de la API devolvía null y el sitemap salía, en silencio,
// solo con las páginas fijas (sin un solo producto) y así quedaba guardado una hora. Si
// Google lo bajaba en ese rato veía desaparecer el catálogo. Ahora se reintenta y, si la
// API sigue sin contestar, se lanza el error: Next conserva el último sitemap bueno.
async function fetchJson<T>(path: string): Promise<T | null> {
  for (let intento = 1; ; intento++) {
    try {
      const res = await fetch(`${API}${path}`, {
        next: { revalidate: 3600 },
        headers: { Accept: 'application/json' },
      });
      if (res.ok) return (await res.json()) as T;
      if (res.status < 500) return null; // 4xx: la consulta está mal, reintentar no la arregla
      throw new Error(`API ${res.status}: ${path}`);
    } catch (e) {
      if (intento === 3) throw e;
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Sin `lastModified` donde no hay fecha real: con la hora actual en las 856 URL, cada
  // hora, Google deja de creerle al campo entero (también al de los artículos, que sí
  // traen su fecha verdadera).
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, changeFrequency: 'daily', priority: 1.0 },
    { url: `${BASE}/categorias/perros`, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/categorias/gatos`, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/categorias/accesorios`, changeFrequency: 'weekly', priority: 0.85 },
    { url: `${BASE}/categorias/snacks`, changeFrequency: 'weekly', priority: 0.85 },
    { url: `${BASE}/categorias/todos`, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/blog`, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${BASE}/noticias`, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/nosotros`, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE}/contacto`, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE}/pereira-dosquebradas-mascotas`, changeFrequency: 'monthly', priority: 0.9 },
    { url: `${BASE}/tarjeta.html`, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE}/adopcion`, changeFrequency: 'daily', priority: 0.85 },
    { url: `${BASE}/mascotas-perdidas`, changeFrequency: 'daily', priority: 0.85 },
    { url: `${BASE}/mascotas-encontradas`, changeFrequency: 'daily', priority: 0.85 },
    { url: `${BASE}/finales-felices`, changeFrequency: 'daily', priority: 0.8 },
    { url: `${BASE}/domicilio-mascotas`, changeFrequency: 'monthly', priority: 0.85 },
    { url: `${BASE}/peluqueria`, changeFrequency: 'monthly', priority: 0.9 },
  ];

  // Una entrada por zona de Pereira y Dosquebradas. Sin esto Google tardaría
  // semanas en descubrirlas, porque solo se enlazan entre ellas y desde su índice.
  const zonaPages: MetadataRoute.Sitemap = ZONAS.map((z) => ({
    url: `${BASE}/domicilio-mascotas/${z.slug}`,
    changeFrequency: 'monthly' as const,
    priority: 0.8,
  }));

  // Todos los productos publicados
  // OJO: la API tope `per_page` en 100 (Query(..., le=100)). Con 200 devuelve 422
  // y `fetchJson` se traga el error devolviendo null, así que el sitemap salía SIN
  // un solo producto y SIN un solo artículo, en silencio, desde siempre. Detectado
  // el 13-sep-2026: 71 URLs en el sitemap con más de 500 productos y 33 artículos
  // publicados. Si algún día sube el tope de la API, súbelo aquí también.
  const POR_PAGINA = 100;

  const productPages: MetadataRoute.Sitemap = [];
  let page = 1;
  while (true) {
    const data = await fetchJson<{
      items: { slug: string }[];
      total: number;
    }>(`/v1/products?is_published=true&per_page=${POR_PAGINA}&page=${page}`);
    if (!data || data.items.length === 0) break;
    productPages.push(
      ...data.items.map((p) => ({
        url: `${BASE}/producto/${p.slug}`,
            changeFrequency: 'weekly' as const,
        priority: 0.7,
      })),
    );
    if (data.items.length < POR_PAGINA) break;
    page++;
  }

  // Posts de blog (SIN las noticias: van aparte, cada URL una sola vez)
  const blogPages: MetadataRoute.Sitemap = [];
  const blogData = await fetchJson<{ posts: { slug: string; updated_at?: string }[] }>(
    `/v1/blog/posts?published=true&per_page=${POR_PAGINA}&exclude_category=noticias`,
  );
  if (blogData?.posts) {
    blogPages.push(
      ...blogData.posts.map((p) => ({
        url: `${BASE}/blog/${p.slug}`,
        lastModified: p.updated_at ? new Date(p.updated_at) : now,
        changeFrequency: 'monthly' as const,
        priority: 0.6,
      })),
    );
  }

  // Noticias de interés. Prioridad y frecuencia altas a propósito: son hechos
  // con fecha y su valor de búsqueda se cae a los pocos días, así que a Google
  // hay que decirle que vuelva pronto.
  const newsPages: MetadataRoute.Sitemap = [];
  const newsData = await fetchJson<{ posts: { slug: string; updated_at?: string; published_at?: string }[] }>(
    `/v1/blog/posts?published=true&per_page=${POR_PAGINA}&category=noticias`,
  );
  if (newsData?.posts) {
    newsPages.push(
      ...newsData.posts.map((p) => ({
        url: `${BASE}/noticias/${p.slug}`,
        lastModified: p.updated_at ? new Date(p.updated_at) : now,
        changeFrequency: 'daily' as const,
        priority: 0.8,
      })),
    );
  }

  // Landing pages SEO programáticas
  const landingPages: MetadataRoute.Sitemap = [];
  const landingsData = await fetchJson<{ slug: string; updated_at?: string }[]>('/v1/landings');
  if (landingsData) {
    landingPages.push(
      ...landingsData
        // 7-nov-2026: las dos landings que ceden su canonical a /pereira-dosquebradas-mascotas
        // no se anuncian en el sitemap (ver CANONICAL_A en landing/[slug]/page.tsx).
        .filter((l) => !l.slug.startsWith('test') && !['tienda-mascotas-risaralda', 'mejor-tienda-mascotas-pereira'].includes(l.slug))
        .map((l) => ({
          url: `${BASE}/landing/${l.slug}`,
          lastModified: l.updated_at ? new Date(l.updated_at) : now,
          changeFrequency: 'weekly' as const,
          priority: 0.75,
        })),
    );
  }

  // Comunidad: mascotas perdidas, animales encontrados, foro de adopción
  const lostPages: MetadataRoute.Sitemap = [];
  const lostData = await fetchJson<{ id: string; created_at?: string }[]>('/v1/public/community/lost');
  if (lostData) {
    lostPages.push(
      ...lostData.map((p) => ({
        url: `${BASE}/mascotas-perdidas/${p.id}`,
        lastModified: p.created_at ? new Date(p.created_at) : now,
        changeFrequency: 'daily' as const,
        priority: 0.65,
      })),
    );
  }

  const foundPages: MetadataRoute.Sitemap = [];
  const foundData = await fetchJson<{ id: string; created_at?: string }[]>('/v1/public/community/found');
  if (foundData) {
    foundPages.push(
      ...foundData.map((p) => ({
        url: `${BASE}/mascotas-encontradas/${p.id}`,
        lastModified: p.created_at ? new Date(p.created_at) : now,
        changeFrequency: 'daily' as const,
        priority: 0.65,
      })),
    );
  }

  const adoptionPages: MetadataRoute.Sitemap = [];
  const adoptionData = await fetchJson<{ id: string; created_at?: string }[]>('/v1/public/community/adoption');
  if (adoptionData) {
    adoptionPages.push(
      ...adoptionData.map((p) => ({
        url: `${BASE}/adopcion/${p.id}`,
        lastModified: p.created_at ? new Date(p.created_at) : now,
        changeFrequency: 'weekly' as const,
        priority: 0.6,
      })),
    );
  }

  // Finales felices (resueltas, visibles 30 días): la API ya las excluye
  // pasada su ventana, así que aquí nunca se publica una URL que dé 404.
  const successPages: MetadataRoute.Sitemap = [];
  const successData = await fetchJson<{ path: string; resolved_at?: string }[]>('/v1/public/community/success?limit=200');
  if (successData) {
    successPages.push(
      ...successData.map((s) => ({
        url: `${BASE}${s.path}`,
        lastModified: s.resolved_at ? new Date(s.resolved_at) : now,
        changeFrequency: 'weekly' as const,
        priority: 0.7,
      })),
    );
  }

  return [
    ...staticPages,
    ...zonaPages,
    ...productPages,
    ...blogPages,
    ...newsPages,
    ...landingPages,
    ...lostPages,
    ...foundPages,
    ...adoptionPages,
    ...successPages,
  ];
}
