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

export interface FAQ {
  pregunta: string;
  respuesta: string;
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
  faqs?: FAQ[];
  seo?: {
    meta_title?: string;
    meta_description?: string;
    keywords?: string[];
    slug?: string;
  };
}

export interface SeoLanding {
  id: string;
  slug: string;
  target_keyword: string;
  title: string;
  h1: string;
  meta_description: string | null;
  intro_content: string | null;
  category_slug: string | null;
  geographic_focus: string | null;
  cta_text: string | null;
  is_active: boolean;
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
  catalogFiltered: async (params: {
    category_slug?: string;
    life_stage?: string;
    size_range?: string;
    brand?: string;
    pet_type?: string;
    price_min?: number;
    price_max?: number;
    in_stock?: boolean;
    sort?: string;
    page?: number;
    page_size?: number;
  } = {}): Promise<{ items: Product[]; total: number; page: number; page_size: number; facets: Record<string, Record<string, number>> }> => {
    const qs = new URLSearchParams();
    if (params.category_slug) qs.set('category_slug', params.category_slug);
    if (params.life_stage) qs.set('life_stage', params.life_stage);
    if (params.size_range) qs.set('size_range', params.size_range);
    if (params.brand) qs.set('brand', params.brand);
    if (params.pet_type) qs.set('pet_type', params.pet_type);
    if (params.price_min != null) qs.set('price_min', String(params.price_min));
    if (params.price_max != null) qs.set('price_max', String(params.price_max));
    if (params.in_stock != null) qs.set('in_stock', String(params.in_stock));
    if (params.sort) qs.set('sort', params.sort);
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    try {
      return await get<any>(`/v1/products/catalog?${qs.toString()}`);
    } catch {
      return { items: [], total: 0, page: 1, page_size: 40, facets: {} };
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
  landingBySlug: async (slug: string): Promise<SeoLanding | null> => {
    try { return await get<SeoLanding>(`/v1/landings/${slug}`); } catch { return null; }
  },
  landings: async (): Promise<SeoLanding[]> => {
    try { return await get<SeoLanding[]>('/v1/landings'); } catch { return []; }
  },
};
