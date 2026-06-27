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
  enriched_content?: EnrichedContent | null;
  enriched_at?: string | null;
  enriched_model?: string | null;
}

export interface EnrichedContent {
  descripcion_corta?: string;
  descripcion?: string;
  beneficios?: string[];
  detalles_tecnicos?: {
    presentacion?: string | null;
    principio_activo?: string | null;
    ingredientes_principales?: string | null;
    edad_recomendada?: string | null;
    tamano_recomendado?: string | null;
  };
  modo_de_uso?: string;
  recomendado_para?: string[];
  advertencias?: string[];
  seo?: {
    meta_title?: string;
    meta_description?: string;
    keywords?: string[];
    slug?: string;
  };
}

export interface BlogPost {
  id: string;
  slug: string;
  title: string;
  excerpt: string | null;
  content?: string;
  cover_image_url: string | null;
  category: string | null;
  keywords: string[];
  meta_title: string | null;
  meta_description: string | null;
  author: string;
  published_at: string | null;
  updated_at: string | null;
  view_count: number;
}

export interface BlogListResponse {
  posts: BlogPost[];
  total: number;
  page: number;
  per_page: number;
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
  blogList: async (params: { page?: number; per_page?: number; category?: string } = {}): Promise<BlogListResponse> => {
    const qs = new URLSearchParams({ published: 'true' });
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    if (params.category) qs.set('category', params.category);
    try {
      return await get<BlogListResponse>(`/v1/blog/posts?${qs.toString()}`);
    } catch {
      return { posts: [], total: 0, page: 1, per_page: 12 };
    }
  },
  blogBySlug: async (slug: string): Promise<BlogPost | null> => {
    try { return await get<BlogPost>(`/v1/blog/posts/${slug}`); } catch { return null; }
  },
};
