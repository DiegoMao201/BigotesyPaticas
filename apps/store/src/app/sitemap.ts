import type { MetadataRoute } from 'next';

export const revalidate = 3600; // regenerar cada hora

const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

const BASE = 'https://bigotesypaticas.com';

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API}${path}`, {
      next: { revalidate: 3600 },
      headers: { Accept: 'application/json' },
    });
    if (!res.ok) return null;
    return res.json() as Promise<T>;
  } catch {
    return null;
  }
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    { url: BASE, lastModified: now, changeFrequency: 'daily', priority: 1.0 },
    { url: `${BASE}/categorias/perros`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/categorias/gatos`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/categorias/accesorios`, lastModified: now, changeFrequency: 'weekly', priority: 0.85 },
    { url: `${BASE}/categorias/snacks`, lastModified: now, changeFrequency: 'weekly', priority: 0.85 },
    { url: `${BASE}/categorias/todos`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },
    { url: `${BASE}/blog`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${BASE}/nosotros`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${BASE}/contacto`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${BASE}/pereira-dosquebradas-mascotas`, lastModified: now, changeFrequency: 'monthly', priority: 0.8 },
    { url: `${BASE}/pet-shop-pereira`, lastModified: now, changeFrequency: 'monthly', priority: 0.9 },
  ];

  // Todos los productos publicados
  const productPages: MetadataRoute.Sitemap = [];
  let page = 1;
  while (true) {
    const data = await fetchJson<{
      items: { slug: string }[];
      total: number;
    }>(`/v1/products?is_published=true&per_page=200&page=${page}`);
    if (!data || data.items.length === 0) break;
    productPages.push(
      ...data.items.map((p) => ({
        url: `${BASE}/producto/${p.slug}`,
        lastModified: now,
        changeFrequency: 'weekly' as const,
        priority: 0.7,
      })),
    );
    if (data.items.length < 200) break;
    page++;
  }

  // Posts de blog
  const blogPages: MetadataRoute.Sitemap = [];
  const blogData = await fetchJson<{ posts: { slug: string; updated_at?: string }[] }>(
    '/v1/blog/posts?published=true&per_page=200',
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

  // Landing pages SEO programáticas
  const landingPages: MetadataRoute.Sitemap = [];
  const landingsData = await fetchJson<{ slug: string; updated_at?: string }[]>('/v1/landings');
  if (landingsData) {
    landingPages.push(
      ...landingsData.map((l) => ({
        url: `${BASE}/landing/${l.slug}`,
        lastModified: l.updated_at ? new Date(l.updated_at) : now,
        changeFrequency: 'weekly' as const,
        priority: 0.75,
      })),
    );
  }

  return [...staticPages, ...productPages, ...blogPages, ...landingPages];
}
