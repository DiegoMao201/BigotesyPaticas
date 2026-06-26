/** Cliente del backend (lectura pública). */
const API_BASE =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_BASE_URL || '';

export interface Category {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  parent_id: string | null;
  sort_order: number;
  is_active: boolean;
}

export interface Brand {
  id: string;
  name: string;
  slug: string;
  logo_url: string | null;
  is_active: boolean;
}

export interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  short_description: string | null;
  description?: string | null;
  brand_id: string | null;
  category_id: string | null;
  category?: Category | null;
  brand?: Brand | null;
  attributes?: Record<string, unknown>;
  price: string;
  compare_at_price: string | null;
  primary_image_url: string | null;
  images: string[];
  tags: string[];
  is_featured: boolean;
  stock_qty: number;
  in_stock: boolean;
}

export interface ProductsPage {
  items: Product[];
  total: number;
  page: number;
  per_page: number;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { next: { revalidate: 60 } });
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const storeApi = {
  categories: async (): Promise<Category[]> => {
    try { return await get<Category[]>('/v1/categories'); } catch { return []; }
  },
  featured: async (): Promise<Product[]> => {
    try {
      const r = await get<ProductsPage>('/v1/products?is_featured=true&is_published=true&per_page=12');
      return r.items;
    } catch { return []; }
  },
  list: async (params: {
    q?: string;
    page?: number;
    per_page?: number;
    category_slug?: string;
    species?: string;
  } = {}): Promise<ProductsPage> => {
    const qs = new URLSearchParams({ is_published: 'true' });
    if (params.q) qs.set('q', params.q);
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    if (params.category_slug) qs.set('category_slug', params.category_slug);
    if (params.species) qs.set('species', params.species);
    try {
      return await get<ProductsPage>(`/v1/products?${qs.toString()}`);
    } catch {
      return { items: [], total: 0, page: 1, per_page: 24 };
    }
  },
  bySlug: async (slug: string): Promise<Product | null> => {
    try { return await get<Product>(`/v1/products/by-slug/${slug}`); } catch { return null; }
  },
  related: async (productId: string, limit = 4): Promise<Product[]> => {
    try { return await get<Product[]>(`/v1/products/${productId}/related?limit=${limit}`); } catch { return []; }
  },
};
