/** Cliente del backend (lectura pública). */
const API_BASE =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_BASE_URL || '';

export interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  short_description: string | null;
  description?: string | null;
  brand_id: string | null;
  category_id: string | null;
  price: string;
  compare_at_price: string | null;
  primary_image_url: string | null;
  images: string[];
  tags: string[];
  is_featured: boolean;
}

export interface ProductsPage {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const storeApi = {
  featured: async (): Promise<Product[]> => {
    try {
      const r = await get<ProductsPage>('/v1/products?is_featured=true&is_published=true&page_size=12');
      return r.items;
    } catch { return []; }
  },
  list: async (params: { q?: string; page?: number; page_size?: number } = {}): Promise<ProductsPage> => {
    const qs = new URLSearchParams({ is_published: 'true' });
    if (params.q) qs.set('q', params.q);
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    try {
      return await get<ProductsPage>(`/v1/products?${qs.toString()}`);
    } catch {
      return { items: [], total: 0, page: 1, page_size: 12 };
    }
  },
  bySlug: async (slug: string): Promise<Product | null> => {
    try { return await get<Product>(`/v1/products/by-slug/${slug}`); } catch { return null; }
  },
};
