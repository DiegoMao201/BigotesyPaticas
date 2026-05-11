/**
 * Cliente HTTP tipado para el backend FastAPI.
 * Lee el token del localStorage en el cliente; en server components usar cookies.
 */
const API_BASE =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_BASE_URL || '';

const TOKEN_KEY = 'bp_admin_token';

export function setToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { auth?: boolean } = {},
): Promise<T> {
  const { auth = true, headers, ...rest } = init;
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const token = auth ? getToken() : null;
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };
  if (token) finalHeaders.Authorization = `Bearer ${token}`;

  const res = await fetch(url, { ...rest, headers: finalHeaders, cache: 'no-store' });
  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) {
    const detail = typeof data === 'object' ? (data as { detail?: string }).detail : data;
    throw new ApiError(typeof detail === 'string' ? detail : 'Error de API', res.status, data);
  }
  return data as T;
}

// === Endpoints tipados ============================================
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  permissions: string[];
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: User;
}

export const auth = {
  login: (email: string, password: string) =>
    api<LoginResponse>('/v1/auth/login', {
      method: 'POST',
      auth: false,
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<User>('/v1/auth/me'),
};

export interface Product {
  id: string;
  sku: string;
  slug: string;
  name: string;
  short_description: string | null;
  brand_id: string | null;
  category_id: string | null;
  cost: string;
  price: string;
  compare_at_price: string | null;
  is_active: boolean;
  is_featured: boolean;
  is_published: boolean;
  primary_image_url: string | null;
  images: string[];
  tags: string[];
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export const products = {
  list: (params: { page?: number; page_size?: number; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.q) qs.set('q', params.q);
    return api<PaginatedProducts>(`/v1/products?${qs.toString()}`);
  },
};

export interface Order {
  id: string;
  order_number: string;
  channel: string;
  status: string;
  customer_id: string | null;
  subtotal: string;
  grand_total: string;
  paid_amount: string;
  balance_due: string;
  payment_status: string;
  occurred_at: string;
  created_at: string;
}

export const sales = {
  list: (params: { page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    return api<{ items: Order[]; total: number }>(`/v1/sales/orders?${qs.toString()}`);
  },
};

// ─── Analytics ────────────────────────────────────────────────────
export interface DashboardKpis {
  revenue_month: number;
  revenue_prev_month: number;
  revenue_delta_pct: number;
  orders_month: number;
  orders_prev_month: number;
  orders_delta_pct: number;
  avg_ticket: number;
  products_active: number;
  customers_total: number;
  low_stock_count: number;
}

export interface DailySale {
  date: string;
  revenue: number;
  orders: number;
}

export interface TopProduct {
  product_id: string;
  name: string;
  sku: string;
  units_sold: number;
  revenue: number;
  primary_image_url: string | null;
}

export interface DashboardData {
  kpis: DashboardKpis;
  daily_sales: DailySale[];
  top_products: TopProduct[];
  recent_orders: Order[];
}

export interface StockAlert {
  product_id: string;
  sku: string;
  name: string;
  available: number;
  level: 'critical' | 'low';
}

export const analytics = {
  dashboard: () => api<DashboardData>('/v1/analytics/dashboard'),
  stockAlerts: (threshold = 10) =>
    api<StockAlert[]>(`/v1/analytics/stock-alerts?threshold=${threshold}`),
};

// ─── Customers ────────────────────────────────────────────────────
export interface Customer {
  id: string;
  full_name: string;
  document_id: string | null;
  email: string | null;
  phone: string | null;
  city: string | null;
  rfm_segment: string | null;
  rfm_monetary: number | null;
  last_purchase_at: string | null;
  created_at: string;
}

export interface PaginatedCustomers {
  items: Customer[];
  total: number;
  page: number;
  page_size: number;
}

export const customers = {
  list: (params: { page?: number; page_size?: number; q?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.q) qs.set('q', params.q);
    return api<PaginatedCustomers>(`/v1/customers?${qs.toString()}`);
  },
  get: (id: string) => api<Customer>(`/v1/customers/${id}`),
  orders: (id: string) => api<Order[]>(`/v1/customers/${id}/orders`),
  create: (payload: {
    full_name: string;
    document_id?: string;
    email?: string;
    phone?: string;
    city?: string;
    notes?: string;
  }) =>
    api<Customer>('/v1/customers', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

// ─── POS / Sales creation ─────────────────────────────────────────
export interface OrderItemIn {
  product_id: string;
  quantity: number;
  unit_price?: number;
  discount?: number;
}

export interface PaymentIn {
  method: string;
  amount: number;
  reference?: string;
  notes?: string;
}

export interface OrderCreate {
  customer_id?: string;
  channel?: string;
  items: OrderItemIn[];
  payments?: PaymentIn[];
  shipping_total?: number;
  notes?: string;
}

export const pos = {
  createOrder: (payload: OrderCreate) =>
    api<Order>('/v1/sales/orders', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

