/**
 * Cliente HTTP tipado para el backend FastAPI.
 * Lee el token del localStorage en el cliente; en server components usar cookies.
 * Incluye auto-refresh transparente de token + redirect a login si la sesión venció.
 */
export const API_BASE =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_BASE_URL || '';

const TOKEN_KEY = 'bp_admin_token';
const REFRESH_TOKEN_KEY = 'bp_admin_refresh_token';

export function setToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setRefreshToken(token: string | null) {
  if (typeof window === 'undefined') return;
  if (token) localStorage.setItem(REFRESH_TOKEN_KEY, token);
  else localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function clearAuth() {
  setToken(null);
  setRefreshToken(null);
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

// Singleton promise to avoid parallel refresh races
let _refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = getRefreshToken();
  if (!refreshToken) throw new Error('no_refresh_token');

  const res = await fetch(`${API_BASE}/v1/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: 'no-store',
  });

  if (!res.ok) {
    clearAuth();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('session_expired');
  }

  const data = await res.json();
  setToken(data.access_token);
  if (data.refresh_token) setRefreshToken(data.refresh_token);
  return data.access_token as string;
}

const FETCH_TIMEOUT_MS = 20_000; // 20 s — operaciones de escritura raramente tardan más

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { auth?: boolean; _retry?: boolean; _netRetry?: boolean } = {},
): Promise<T> {
  const { auth = true, _retry = false, _netRetry = false, headers, ...rest } = init;
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const token = auth ? getToken() : null;
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };
  if (token) finalHeaders.Authorization = `Bearer ${token}`;

  // Timeout automático para detectar API caída o red lenta
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(url, { ...rest, headers: finalHeaders, cache: 'no-store', signal: controller.signal });
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    const isAbort = err instanceof DOMException && err.name === 'AbortError';
    const msg = isAbort
      ? 'El servidor tardó demasiado. Verificá tu conexión e intentá de nuevo.'
      : 'No se pudo conectar con el servidor. Verificá tu conexión e intentá de nuevo.';
    // Un reintento automático para errores de red transitorios (API reiniciando)
    if (!_netRetry) {
      await new Promise((r) => setTimeout(r, 1200));
      return api<T>(path, { ...init, _netRetry: true });
    }
    throw new ApiError(msg, 0, null);
  }
  clearTimeout(timeoutId);

  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : await res.text();

  // Auto-refresh on 401 (token expirado) — solo una vez para no entrar en loop
  if (res.status === 401 && auth && !_retry) {
    try {
      if (!_refreshPromise) {
        _refreshPromise = refreshAccessToken().finally(() => { _refreshPromise = null; });
      }
      await _refreshPromise;
      return api<T>(path, { ...init, _retry: true });
    } catch {
      throw new ApiError('Sesión expirada, por favor inicia sesión de nuevo', 401, null);
    }
  }

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
  description: string | null;
  brand_id: string | null;
  category_id: string | null;
  category_name?: string | null;
  cost: string;
  price: string;
  compare_at_price: string | null;
  is_active: boolean;
  is_featured: boolean;
  is_published: boolean;
  primary_image_url: string | null;
  images: string[];
  tags: string[];
  attributes: Record<string, unknown>;
  margin_pct?: string;
  supplier_id?: string | null;
  supplier_name?: string | null;
  stock_qty: number;
  in_stock: boolean;
  // Filtros de catálogo
  life_stage: string | null;
  size_range: string | null;
  pet_type: string | null;
  brand_normalized: string | null;
  health_concerns: string[] | null;
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export const products = {
  list: (params: { page?: number; page_size?: number; q?: string; is_published?: boolean; category?: string; supplier_id?: string; without_supplier?: boolean } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.q) qs.set('q', params.q);
    if (params.is_published !== undefined) qs.set('is_published', String(params.is_published));
    if (params.category) qs.set('category', params.category);
    if (params.supplier_id) qs.set('supplier_id', params.supplier_id);
    if (params.without_supplier) qs.set('without_supplier', 'true');
    return api<PaginatedProducts>(`/v1/products?${qs.toString()}`);
  },
  get: (id: string) => api<Product>(`/v1/products/${id}`),
  create: (payload: Partial<Product> & { sku: string; name: string }) =>
    api<Product>('/v1/products', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<Product>) =>
    api<Product>(`/v1/products/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) =>
    api<{ ok: boolean; id: string }>(`/v1/products/${id}`, { method: 'DELETE' }),
  brands: () => api<{ id: string; name: string; slug: string }[]>('/v1/brands'),
  categories: () => api<{ id: string; name: string; slug: string }[]>('/v1/categories'),
  exportXlsx: async (): Promise<Blob> => {
    const token = getToken();
    const res = await fetch(`${API_BASE}/v1/admin/products/export-xlsx`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    });
    if (!res.ok) throw new Error('Error al exportar');
    return res.blob();
  },
  importXlsx: async (file: File): Promise<{ ok: boolean; updated: number; skipped: number; errors: number; error_details: string[] }> => {
    const token = getToken();
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${API_BASE}/v1/admin/products/import-xlsx`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
      cache: 'no-store',
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al importar');
    return data;
  },
};

export interface OrderItemOut {
  id: string;
  product_id: string;
  sku_snapshot: string;
  name_snapshot: string;
  quantity: number;
  unit_price: string;
  unit_cost: string;
  discount: string;
  line_total: string;
}

export interface PaymentOut {
  id: string;
  method: string;
  amount: string;
  received_at: string;
  reference: string | null;
}

export interface Order {
  id: string;
  order_number: string;
  channel: string;
  status: string;
  customer_id: string | null;
  subtotal: string;
  discount_total: string;
  tax_total: string;
  shipping_total: string;
  grand_total: string;
  paid_amount: string;
  balance_due: string;
  payment_status: string;
  payment_method: string | null;
  occurred_at: string;
  created_at: string;
  notes: string | null;
  items: OrderItemOut[];
  payments: PaymentOut[];
}

export interface OrdersListResponse {
  items: Order[];
  total: number;
  total_revenue: number;
  avg_ticket: number;
  active_count: number;
  page: number;
  page_size: number;
}

export const sales = {
  list: (params: { page?: number; page_size?: number; q?: string; status?: string; payment_status?: string; channel?: string; date_from?: string; date_to?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.q) qs.set('q', params.q);
    if (params.status) qs.set('status', params.status);
    if (params.payment_status) qs.set('payment_status', params.payment_status);
    if (params.channel) qs.set('channel', params.channel);
    if (params.date_from) qs.set('date_from', params.date_from);
    if (params.date_to) qs.set('date_to', params.date_to);
    return api<OrdersListResponse>(`/v1/sales/orders?${qs.toString()}`);
  },
  get: (id: string) => api<Order>(`/v1/sales/orders/${id}`),
  markPaid: (id: string, payload: { method?: string; reference?: string; notes?: string } = {}) =>
    api<{ ok: boolean; order_number: string; amount_applied: number; payment_status: string }>(`/v1/sales/orders/${id}/mark-paid`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  cancel: (id: string, reason?: string) =>
    api<{ ok: boolean; order_number: string }>(`/v1/sales/orders/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  invoiceUrl: (id: string) => `${API_BASE}/v1/sales/orders/${id}/invoice`,
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
  address: string | null;
  city: string | null;
  notes: string | null;
  pet_name: string | null;
  pet_type: string | null;
  pet_notes: string | null;
  pet_birthday?: string | null;
  last_deworming?: string | null;
  rfm_segment: string | null;
  rfm_monetary: number | null;
  last_purchase_at: string | null;
  created_at: string;
  referral_code?: string | null;
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
    address?: string;
    city?: string;
    notes?: string;
    pet_name?: string;
    pet_type?: string;
    pet_notes?: string;
    pet_birthday?: string;
    last_deworming?: string;
  }) =>
    api<Customer>('/v1/customers', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  update: (id: string, payload: {
    full_name?: string;
    document_id?: string;
    email?: string;
    phone?: string;
    address?: string;
    city?: string;
    notes?: string;
    pet_name?: string;
    pet_type?: string;
    pet_notes?: string;
    pet_birthday?: string;
    last_deworming?: string;
  }) =>
    api<Customer>(`/v1/customers/${id}`, {
      method: 'PATCH',
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


// ─── Finance / Expenses / Cash Closings / Suppliers ───────────────
export interface ExpenseRow {
  id: string;
  legacy_id: string;
  fecha: string;
  tipo: string;
  categoria: string;
  descripcion: string;
  monto: number;
  metodo_pago: string;
  banco_origen: string;
}

export interface ExpensesPage {
  items: ExpenseRow[];
  total: number;
  page: number;
  page_size: number;
  total_monto: number;
}

export const expenses = {
  list: (params: { start?: string; end?: string; categoria?: string; metodo_pago?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return api<ExpensesPage>(`/v1/expenses?${qs.toString()}`);
  },
  create: (payload: { fecha: string; tipo: string; categoria: string; descripcion: string; monto: number; metodo_pago: string; banco_origen?: string }) =>
    api<ExpenseRow>('/v1/expenses', { method: 'POST', body: JSON.stringify(payload) }),
  categories: () => api<{ name: string; count: number; total: number }[]>('/v1/expenses/categories'),
};

export interface CashClosing {
  id: string;
  fecha: string;
  status: 'open' | 'closed';
  saldo_inicial: number;
  gastos_efectivo: number;
  ventas_por_metodo: Record<string, number>;
  creditos_por_metodo: Record<string, number>;
  total_ventas: number;
  order_count: number;
  ventas_efectivo: number;
  creditos_efectivo: number;
  saldo_final_efectivo: number;
  saldo_contado: number | null;
  diferencia: number | null;
  notas: string | null;
  closed_at: string | null;
  closed_by: string | null;
}

export const cashClosings = {
  today: () => api<CashClosing>('/v1/cash-closings/today'),
  byDate: (fecha: string) => api<CashClosing>(`/v1/cash-closings/by-date?fecha=${fecha}`),
  list: (params: { page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    return api<{ items: CashClosing[]; total: number; page: number; page_size: number }>(`/v1/cash-closings?${qs.toString()}`);
  },
  get: (id: string) => api<CashClosing>(`/v1/cash-closings/${id}`),
  open: (payload: { fecha?: string; saldo_inicial?: number }) =>
    api<CashClosing>('/v1/cash-closings', { method: 'POST', body: JSON.stringify(payload) }),
  patch: (id: string, payload: { gastos_efectivo?: number; saldo_inicial?: number; notas?: string }) =>
    api<CashClosing>(`/v1/cash-closings/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  close: (id: string, payload: { saldo_contado: number; gastos_efectivo?: number; notas?: string }) =>
    api<CashClosing>(`/v1/cash-closings/${id}/close`, { method: 'POST', body: JSON.stringify(payload) }),
};

export interface SupplierRow {
  id_proveedor: string;
  nombre_proveedor: string;
  sku_proveedor: string;
  sku_interno: string;
  factor_pack: number;
  costo_unidad: number;
}

export interface SupplierGroup {
  nombre_proveedor: string;
  id_proveedor: string;
  sku_count: number;
  skus: { sku_proveedor: string; sku_interno: string; costo: number }[];
}

export const suppliersLegacy = {
  list: (params: { q?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return api<{ items: SupplierRow[]; total: number; page: number; page_size: number }>(`/v1-legacy/suppliers?${qs.toString()}`);
  },
  grouped: () => api<SupplierGroup[]>('/v1-legacy/suppliers/grouped'),
};

// ─── Suppliers (CRUD real, schema purchasing.suppliers) ───────────
export interface Supplier {
  id: string;
  nit: string;
  name: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  contact_name: string | null;
  payment_terms_days: number;
  notes: string | null;
  is_active: boolean;
  sku_count: number;
  created_at: string;
  updated_at: string;
}

export interface SupplierIn {
  nit: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
  contact_name?: string;
  payment_terms_days?: number;
  notes?: string;
}

export interface SupplierSkuInsight {
  id: string;
  sku_proveedor: string;
  product_id: string;
  product_sku: string;
  product_name: string;
  factor_pack: number;
  last_unit_cost: number | null;
  last_tax_pct: number | null;
  last_seen_at: string | null;
  stock_available: number;
  avg_daily_sales: number;
  days_cover: number | null;
  reorder_qty_8d: number;
  reorder_qty_15d: number;
  reorder_qty_20d: number;
  urgency: 'AGOTADO' | 'URGENTE_8D' | 'REPOSICION_15D' | 'MONITOREAR_20D' | 'OK';
}

export interface SupplierSkuSummary {
  associated_products: number;
  urgent_8d: number;
  to_replenish_15d: number;
  monitor_20d: number;
  recommended_units_8d: number;
  recommended_units_15d: number;
  recommended_units_20d: number;
}

export const suppliers = {
  list: (params: { q?: string; is_active?: boolean; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.is_active !== undefined) qs.set('is_active', String(params.is_active));
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    return api<{ items: Supplier[]; total: number; page: number; page_size: number }>(`/v1/suppliers?${qs.toString()}`);
  },
  get: (id: string) => api<Supplier>(`/v1/suppliers/${id}`),
  create: (payload: SupplierIn) => api<Supplier>('/v1/suppliers', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<SupplierIn> & { is_active?: boolean }) =>
    api<Supplier>(`/v1/suppliers/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => api(`/v1/suppliers/${id}`, { method: 'DELETE' }),
  listSkus: (id: string, params: { velocity_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.velocity_days) qs.set('velocity_days', String(params.velocity_days));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<{ items: SupplierSkuInsight[]; summary: SupplierSkuSummary }>(`/v1/suppliers/${id}/skus${suffix}`);
  },
};

export interface FinanceSummary {
  period_start: string;
  period_end: string;
  revenue: number;
  cogs: number;
  gross_profit: number;
  gross_margin_pct: number;
  expenses_total: number;
  net_profit: number;
  net_margin_pct: number;
  expenses_by_category: { category: string; total: number }[];
  revenue_by_method: { method: string; total: number }[];
  daily_cashflow: { date: string; revenue: number; expenses: number }[];
}

export const finance = {
  summary: (start?: string, end?: string) => {
    const qs = new URLSearchParams();
    if (start) qs.set('start', start);
    if (end) qs.set('end', end);
    return api<FinanceSummary>(`/v1/finance/summary?${qs.toString()}`);
  },
};

// ─── Inventory extended ───────────────────────────────────────────
export interface StockRow {
  product_id: string;
  sku: string;
  name: string;
  category_name: string | null;
  quantity: number;
  reserved: number;
  available: number;
  cost: number;
  price: number;
  margin_pct: number;
  stock_value_cost: number;
  stock_value_price: number;
}

export interface StockListResponse {
  items: StockRow[];
  total: number;
  page: number;
  page_size: number;
  total_value_cost: number;
  total_value_price: number;
  out_of_stock: number;
  low_stock: number;
}

export interface MovementRow {
  id: string;
  product_id: string;
  product_name: string | null;
  product_sku: string | null;
  movement_type: string;
  quantity_delta: number;
  quantity_after: number;
  unit_cost: number | null;
  reference_type: string | null;
  reference_id: string | null;
  order_number: string | null;
  notes: string | null;
  occurred_at: string;
  created_by: string | null;
}

export const inventory = {
  list: (params: { q?: string; only_in_stock?: boolean; only_low_stock?: boolean; sort_by?: string; sort_dir?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.q) qs.set('q', params.q);
    if (params.only_in_stock) qs.set('only_in_stock', 'true');
    if (params.only_low_stock) qs.set('only_low_stock', 'true');
    if (params.sort_by) qs.set('sort_by', params.sort_by);
    if (params.sort_dir) qs.set('sort_dir', params.sort_dir);
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    return api<StockListResponse>(`/v1/inventory/stock?${qs.toString()}`);
  },
  movements: (params: { product_id?: string; movement_type?: string; limit?: number } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return api<{ items: MovementRow[]; total: number }>(`/v1/inventory/movements?${qs.toString()}`);
  },
  adjust: (payload: { product_id: string; quantity_delta: number; notes?: string; location_id?: string }) =>
    api('/v1/inventory/adjust', { method: 'POST', body: JSON.stringify(payload) }),
  adjustBatch: (payload: { items: { product_id: string; quantity_delta: number; notes?: string }[]; notes?: string; location_id?: string }) =>
    api<{ applied: number; total_delta: number; items: { product_id: string; quantity_delta: number; quantity_after: number }[] }>(
      '/v1/inventory/adjust/batch',
      { method: 'POST', body: JSON.stringify(payload) },
    ),
  updatePricing: (product_id: string, payload: { cost?: number; price?: number }) =>
    api(`/v1/inventory/stock/${product_id}/pricing`, { method: 'PATCH', body: JSON.stringify(payload) }),
  movementsByProduct: (product_id: string, days = 30) =>
    api<{ product_id: string; days: number; movements: { id: string; type: string; quantity: number; occurred_at: string; reference: string | null; notes: string | null }[] }>(`/v1/inventory/movements/by-product/${product_id}?days=${days}`),
  velocityAnalysis: (days_short = 30, days_long = 90) =>
    api<VelocityAnalysisResponse>(`/v1/inventory/analytics/velocity?days_short=${days_short}&days_long=${days_long}`),
  exportExcel: async (): Promise<Blob> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('bp_admin_token') : null;
    const res = await fetch(`${API_BASE}/v1/inventory/export/excel`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error('Error descargando Excel');
    return res.blob();
  },
};

export interface VelocityProduct {
  product_id: string;
  sku: string;
  name: string;
  category_name: string | null;
  supplier_id: string | null;
  supplier_name: string | null;
  stock: number;
  cost: number;
  price: number;
  v_short: number;
  v_long: number;
  velocidad_diaria: number;
  punto_reorden: number;
  stock_objetivo: number;
  faltante: number;
  dias_cobertura: number | null;
  valor_ventas_long: number;
  estado: 'AGOTADO' | 'COMPRAR' | 'SOBRESTOCK' | 'OK';
  requiere_compra: boolean;
  clase_abc: 'A' | 'B' | 'C';
}

export interface VelocityAnalysisResponse {
  days_short: number;
  days_long: number;
  products: VelocityProduct[];
  summary: {
    total_productos: number;
    agotados: number;
    requieren_compra: number;
    sobrestock: number;
    valor_inventario: number;
  };
}

// ─── Purchases (Compras a proveedores) ────────────────────────────

export interface PurchaseItemIn {
  product_id?: string;
  sku_proveedor?: string;
  sku_interno?: string;
  product_name: string;
  quantity: number;
  factor_pack?: number;
  unit_cost: number;
  tax_pct?: number;
}

export interface PurchaseItemOut {
  id: string;
  product_id: string | null;
  sku_proveedor: string | null;
  sku_interno: string | null;
  product_name: string;
  quantity: number;
  factor_pack: number;
  unit_cost: number;
  tax_pct: number;
  total_cost: number;
}

export interface PurchaseOut {
  id: string;
  folio: string | null;
  supplier_name: string;
  supplier_id: string | null;
  status: string;
  subtotal: number;
  tax_amount: number;
  total: number;
  payment_method: string;
  payment_reference: string | null;
  notes: string | null;
  purchased_at: string;
  created_at: string;
  items: PurchaseItemOut[];
}

export interface PurchaseSummary {
  id: string;
  folio: string | null;
  supplier_name: string;
  status: string;
  total: number;
  items_count: number;
  payment_method: string;
  purchased_at: string;
  created_at: string;
}

export interface PurchaseListResponse {
  items: PurchaseSummary[];
  total: number;
  page: number;
  page_size: number;
  total_spend: number;
}

export interface PurchaseCreate {
  folio?: string;
  supplier_name: string;
  supplier_id?: string;
  payment_method?: string;
  payment_reference?: string;
  notes?: string;
  purchased_at?: string;
  items: PurchaseItemIn[];
  receive_now?: boolean;
}

export const purchases = {
  list: (params: { q?: string; status?: string; page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    Object.entries(params).forEach(([k, v]) => v && qs.set(k, String(v)));
    return api<PurchaseListResponse>(`/v1/purchases?${qs.toString()}`);
  },
  get: (id: string) => api<PurchaseOut>(`/v1/purchases/${id}`),
  create: (payload: PurchaseCreate) =>
    api<PurchaseOut>('/v1/purchases', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<PurchaseCreate & { status: string }>) =>
    api<PurchaseOut>(`/v1/purchases/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  delete: (id: string) => api(`/v1/purchases/${id}`, { method: 'DELETE' }),
  receive: (id: string) => api<PurchaseOut>(`/v1/purchases/${id}/receive`, { method: 'POST' }),
  stats: () => api<{ total_spend_month: number; total_count_month: number; top_suppliers: { supplier_name: string; total: number; count: number }[] }>('/v1/purchases/stats/summary'),
  parseXml: async (file: File): Promise<ParsedInvoice> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('bp_admin_token') : null;
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/v1/purchases/xml/parse`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al procesar XML' }));
      throw new Error(err.detail || 'Error al procesar XML');
    }
    return res.json();
  },
};

export interface ParsedItem {
  sku_proveedor: string | null;
  descripcion: string;
  cantidad: number;
  costo_base_unitario: number;
  iva_pct: number;
  descuento: number;
  total_linea: number;
  suggested_product_id: string | null;
  suggested_product_sku: string | null;
  suggested_product_name: string | null;
  match_reason: string | null;
  match_score: number | null;
}

export interface ParsedInvoice {
  supplier: {
    nit: string | null;
    name: string | null;
    email: string | null;
    phone: string | null;
    address: string | null;
    matched_supplier_id: string | null;
  };
  folio: string | null;
  fecha: string | null;
  subtotal: number;
  tax_amount: number;
  total: number;
  items: ParsedItem[];
}

// ─── BI Analytics ──────────────────────────────────────────────────────────

export interface ChannelBreakdown { channel: string; revenue: number; orders: number; pct: number }
export interface MethodBreakdown { method: string; revenue: number; orders: number; pct: number }
export interface MonthlyPoint { year_month: string; revenue: number; orders: number; avg_ticket: number }
export interface TopCustomer { customer_id: string | null; name: string; orders: number; revenue: number; last_purchase: string | null }
export interface CategoryRevenue { category: string; revenue: number; units: number; pct: number }
export interface HeatmapCell { weekday: number; hour: number; orders: number }

export interface BiFull {
  period_start: string;
  period_end: string;
  revenue_total: number;
  orders_total: number;
  avg_ticket: number;
  gross_margin_pct: number;
  by_channel: ChannelBreakdown[];
  by_method: MethodBreakdown[];
  monthly_trend: MonthlyPoint[];
  top_customers: TopCustomer[];
  by_category: CategoryRevenue[];
  heatmap: HeatmapCell[];
  revenue: number;
  cogs: number;
  gross_profit: number;
  expenses_total: number;
  net_profit: number;
  expenses_by_category: { category: string; total: number }[];
}

export interface SalesPeriodComparison {
  current_revenue: number;
  prev_revenue: number;
  delta_pct: number;
  current_orders: number;
  prev_orders: number;
  daily_current: DailySale[];
  daily_prev: DailySale[];
}

// Re-export with extended analytics
export const analyticsBI = {
  full: (days = 90) => api<BiFull>(`/v1/analytics/bi?days=${days}`),
  comparison: (days = 30) => api<SalesPeriodComparison>(`/v1/analytics/sales-comparison?days=${days}`),
};

// ─── Inteligencia (recompra predictiva, retención, capital atrapado) ────────

export interface RepurchaseItem {
  customer_id: string;
  name: string;
  phone: string | null;
  last_purchase: string | null;
  days_since: number;
  avg_interval_days: number;
  days_overdue: number;
  orders: number;
  monetary: number;
  favorite_product: string | null;
  urgency: 'vencido' | 'hoy' | 'proximo';
  whatsapp_url: string | null;
}

export interface AtRiskItem {
  customer_id: string;
  name: string;
  phone: string | null;
  last_purchase: string | null;
  days_since: number;
  orders: number;
  monetary: number;
  segment: string | null;
  whatsapp_url: string | null;
}

export interface DeadStockItem {
  product_id: string;
  sku: string;
  name: string;
  available: number;
  unit_cost: number;
  trapped_capital: number;
  days_no_sale: number | null;
}

export interface IntelligenceData {
  generated_at: string;
  summary: {
    customers_total: number;
    customers_active_90d: number;
    repurchase_due: number;
    repurchase_revenue_opportunity: number;
    at_risk_count: number;
    at_risk_value: number;
    dead_stock_count: number;
    trapped_capital: number;
  };
  repurchase: RepurchaseItem[];
  at_risk: AtRiskItem[];
  dead_stock: DeadStockItem[];
}

export const intelligence = {
  overview: (params: { at_risk_days?: number; dead_stock_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.at_risk_days) qs.set('at_risk_days', String(params.at_risk_days));
    if (params.dead_stock_days) qs.set('dead_stock_days', String(params.dead_stock_days));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<IntelligenceData>(`/v1/intelligence/overview${suffix}`);
  },
  frequentlyBought: (productIds: string[], limit = 6) => {
    const qs = new URLSearchParams({ product_ids: productIds.join(','), limit: String(limit) });
    return api<ComboSuggestion[]>(`/v1/intelligence/frequently-bought?${qs.toString()}`);
  },
  stockoutForecast: (params: { velocity_days?: number; target_days?: number; horizon_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.velocity_days) qs.set('velocity_days', String(params.velocity_days));
    if (params.target_days) qs.set('target_days', String(params.target_days));
    if (params.horizon_days) qs.set('horizon_days', String(params.horizon_days));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<StockoutForecastData>(`/v1/intelligence/stockout-forecast${suffix}`);
  },
  replenishment: (params: { velocity_days?: number; target_days?: number; coverage_threshold_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.velocity_days) qs.set('velocity_days', String(params.velocity_days));
    if (params.target_days) qs.set('target_days', String(params.target_days));
    if (params.coverage_threshold_days) qs.set('coverage_threshold_days', String(params.coverage_threshold_days));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<ReplenishmentData>(`/v1/intelligence/replenishment${suffix}`);
  },
  petCare: (params: { deworming_interval_days?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.deworming_interval_days) qs.set('deworming_interval_days', String(params.deworming_interval_days));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<PetCareData>(`/v1/intelligence/pet-care${suffix}`);
  },
};

export interface ComboSuggestion {
  product_id: string;
  sku: string;
  name: string;
  price: number;
  times_together: number;
  stock: number;
}

export interface StockoutItem {
  product_id: string;
  sku: string;
  name: string;
  available: number;
  velocity: number;
  days_cover: number | null;
  stockout_date: string | null;
  suggested_reorder: number;
  supplier_name: string | null;
  level: 'agotado' | 'critico' | 'bajo' | 'ok';
}

export interface StockoutForecastData {
  generated_at: string;
  target_days: number;
  summary: { at_risk: number; agotado: number; critico: number; bajo: number };
  items: StockoutItem[];
}

export interface ReplenishLine {
  product_id: string;
  sku: string;
  name: string;
  available: number;
  velocity: number;
  days_cover: number | null;
  suggested_qty: number;
  unit_cost: number;
  line_cost: number;
}

export interface ReplenishSupplier {
  supplier_id: string | null;
  supplier_name: string;
  supplier_phone: string | null;
  lines: ReplenishLine[];
  total_units: number;
  total_cost: number;
  whatsapp_url: string | null;
}

export interface ReplenishmentData {
  generated_at: string;
  target_days: number;
  total_cost: number;
  suppliers: ReplenishSupplier[];
}

export interface PetReminder {
  customer_id: string;
  customer_name: string;
  phone: string | null;
  pet_name: string | null;
  pet_type: string | null;
  reason: 'cumple' | 'desparasitacion' | 'vacuna';
  detail: string;
  whatsapp_url: string | null;
}

export interface PetCareData {
  generated_at: string;
  summary: { birthdays_this_month: number; deworming_due: number };
  birthdays: PetReminder[];
  deworming_due: PetReminder[];
}

export interface DailyGoalData {
  fecha: string;
  target: number;
  achieved: number;
  progress_pct: number;
  remaining: number;
  orders_today: number;
  projection_eod: number;
  status: 'logrado' | 'en_camino' | 'atrasado';
  target_source: 'manual' | 'auto_weekday';
  weekday_avg: number;
}

export const dailyGoal = {
  get: (params: { fecha?: string; target?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.fecha) qs.set('fecha', params.fecha);
    if (params.target) qs.set('target', String(params.target));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return api<DailyGoalData>(`/v1/finance/daily-goal${suffix}`);
  },
};

// ─── Admin Portal (pet-monitor v2) ────────────────────────────────────────

export interface PortalKPIs {
  active_sessions_24h: number;
  orders_pending: number;
  appointments_today: number;
  loyalty_points_30d: number;
  as_of: string;
}

export interface PortalOrder {
  id: string;
  customer_name: string | null;
  pet_name: string | null;
  product_name: string;
  quantity: number;
  unit_price: number | null;
  status: string;
  workflow_status: string;
  invoice_number: string | null;
  sales_order_id: string | null;
  notes: string | null;
  created_at: string;
  delivered_at: string | null;
  points_awarded: number;
}

export interface PortalOrderItem {
  id: string;
  product_id: string | null;
  sku: string | null;
  name: string | null;
  image_url: string | null;
  quantity: number;
  unit_price: number;
  subtotal: number;
  notes: string | null;
  is_substituted: boolean;
  substituted_from_name: string | null;
}

export interface PortalOrderDetail {
  id: string;
  customer_id: string | null;
  customer_name: string | null;
  customer_phone: string | null;
  customer_email: string | null;
  status: string;
  workflow_status: string;
  payment_method: string | null;
  shipping_address: string | null;
  internal_notes: string | null;
  customer_facing_notes: string | null;
  discount_amount: number;
  discount_reason: string | null;
  subtotal: number;
  shipping: number;
  total: number;
  points_awarded: number;
  invoice_number: string | null;
  last_status_change_at: string | null;
  customer_confirmed_changes_at: string | null;
  customer_confirmation_channel: string | null;
  created_at: string;
  delivered_at: string | null;
  items: PortalOrderItem[];
}

export interface ActivityLogEntry {
  id: string;
  action: string;
  actor_type: string | null;
  actor_name: string | null;
  changes: Record<string, unknown> | null;
  notes: string | null;
  visible_to_customer: boolean;
  notification_sent_at: string | null;
  created_at: string;
}

export interface PendingNotification {
  id: string;
  portal_order_id: string;
  template_code: string;
  rendered_message: string;
  whatsapp_link: string;
  status: 'pending' | 'sent_by_admin' | 'skipped';
  customer_name?: string;
  customer_phone?: string | null;
  invoice_number?: string | null;
  created_at: string | null;
  sent_at?: string | null;
}

export interface PortalAppointment {
  id: string;
  customer_name: string | null;
  pet_name: string | null;
  service_type: string;
  scheduled_at: string;
  duration_min: number;
  status: string;
  price: number | null;
  notes: string | null;
  confirmed_at: string | null;
  completed_at: string | null;
  cancel_reason: string | null;
  created_at: string;
}

export const adminPortal = {
  overview: () => api<PortalKPIs>('/v1/admin/portal/overview'),
  orders: (status?: string) =>
    api<PortalOrder[]>(`/v1/admin/portal/orders${status ? `?status=${status}` : ''}`),
  updateOrder: (id: string, body: { status: string; notes?: string; cancel_reason?: string }) =>
    api<{ ok: boolean; id: string; status: string }>(
      `/v1/admin/portal/orders/${id}`, { method: 'PATCH', body: JSON.stringify(body) }
    ),

  // Sprint-2: order detail + workflow
  orderDetail: (id: string) => api<PortalOrderDetail>(`/v1/admin/portal/orders/${id}/detail`),
  orderActivity: (id: string) => api<ActivityLogEntry[]>(`/v1/admin/portal/orders/${id}/activity`),
  changeWorkflow: (id: string, new_status: string, internal_notes?: string) =>
    api<{ ok: boolean; workflow_status: string; pending_notification?: PendingNotification }>(
      `/v1/admin/portal/orders/${id}/workflow`,
      { method: 'PATCH', body: JSON.stringify({ new_status, internal_notes }) }
    ),
  editItemQty: (orderId: string, itemId: string, new_quantity: number, reason?: string) =>
    api<PortalOrderDetail>(`/v1/admin/portal/orders/${orderId}/items/${itemId}/quantity`,
      { method: 'PATCH', body: JSON.stringify({ new_quantity, reason }) }),
  substituteItem: (orderId: string, itemId: string, body: { new_product_id: string; new_quantity?: number; reason: string }) =>
    api<PortalOrderDetail>(`/v1/admin/portal/orders/${orderId}/items/${itemId}/substitute`,
      { method: 'POST', body: JSON.stringify(body) }),
  addItem: (orderId: string, body: { product_id: string; quantity?: number; notes?: string; reason?: string }) =>
    api<PortalOrderDetail>(`/v1/admin/portal/orders/${orderId}/items`,
      { method: 'POST', body: JSON.stringify(body) }),
  removeItem: (orderId: string, itemId: string, reason: string) =>
    api<PortalOrderDetail>(`/v1/admin/portal/orders/${orderId}/items/${itemId}`,
      { method: 'DELETE', body: JSON.stringify({ reason }) }),
  applyDiscount: (orderId: string, discount_amount: number, reason: string) =>
    api<PortalOrderDetail>(`/v1/admin/portal/orders/${orderId}/discount`,
      { method: 'POST', body: JSON.stringify({ discount_amount, reason }) }),
  updateNotes: (orderId: string, body: { internal_notes?: string; customer_facing_notes?: string }) =>
    api<{ ok: boolean }>(`/v1/admin/portal/orders/${orderId}/notes`,
      { method: 'PATCH', body: JSON.stringify(body) }),
  confirmApproval: (orderId: string, channel: string, notes?: string) =>
    api<{ ok: boolean; workflow_status: string }>(
      `/v1/admin/portal/orders/${orderId}/confirm-customer-approval`,
      { method: 'POST', body: JSON.stringify({ channel, notes }) }
    ),
  markNotifSent: (orderId: string, channel = 'whatsapp') =>
    api<{ ok: boolean; marked_at: string }>(
      `/v1/admin/portal/orders/${orderId}/notifications/mark-sent`,
      { method: 'POST', body: JSON.stringify({ channel }) }
    ),
  cancelOrder: (orderId: string, reason: string) =>
    api<{ ok: boolean }>(`/v1/admin/portal/orders/${orderId}/cancel`,
      { method: 'POST', body: JSON.stringify({ reason }) }),

  // Sprint 5.2: notificaciones pendientes (modal WhatsApp admin)
  pendingNotifications: (minAgeMinutes = 0) =>
    api<PendingNotification[]>(`/v1/admin/portal/notifications/pending?min_age_minutes=${minAgeMinutes}`),
  markNotificationSent: (notifId: string) =>
    api<{ ok: boolean; status: string; sent_at: string }>(
      `/v1/admin/portal/notifications/${notifId}/mark-sent`,
      { method: 'POST', body: JSON.stringify({ channel: 'whatsapp' }) }
    ),
  skipNotification: (notifId: string) =>
    api<{ ok: boolean; status: string }>(
      `/v1/admin/portal/notifications/${notifId}/skip`,
      { method: 'POST', body: '{}' }
    ),

  appointments: (opts?: { date_from?: string; date_to?: string; status?: string }) => {
    const p = new URLSearchParams();
    if (opts?.date_from) p.set('date_from', opts.date_from);
    if (opts?.date_to) p.set('date_to', opts.date_to);
    if (opts?.status) p.set('status', opts.status);
    return api<PortalAppointment[]>(`/v1/admin/portal/appointments?${p}`);
  },
  appointmentDetail: (id: string) => api<Record<string, unknown>>(`/v1/admin/portal/appointments/${id}/detail`),
  updateAppointment: (id: string, body: { status: string; cancel_reason?: string }) =>
    api<{ ok: boolean; id: string; status: string }>(
      `/v1/admin/portal/appointments/${id}`, { method: 'PATCH', body: JSON.stringify(body) }
    ),
  rescheduleAppointment: (id: string, body: { proposed_options: string[]; reason_category: string; reason_notes?: string; compensation_points?: number }) =>
    api<{ ok: boolean; workflow_status: string }>(
      `/v1/admin/portal/appointments/${id}/reschedule`,
      { method: 'PATCH', body: JSON.stringify(body) }
    ),
  confirmApptChoice: (id: string, chosen_datetime: string, customer_confirmed_via?: string) =>
    api<{ ok: boolean }>(
      `/v1/admin/portal/appointments/${id}/confirm-choice`,
      { method: 'PATCH', body: JSON.stringify({ chosen_datetime, customer_confirmed_via }) }
    ),
  completeAppointment: (id: string) =>
    api<{ ok: boolean }>(`/v1/admin/portal/appointments/${id}/complete`, { method: 'PATCH', body: '{}' }),
  noShowAppointment: (id: string) =>
    api<{ ok: boolean }>(`/v1/admin/portal/appointments/${id}/no-show`, { method: 'PATCH', body: '{}' }),
};

// ─── Admin ETL ─────────────────────────────────────────────────────────────

export const adminEtl = {
  status: () => api<Record<string, number>>('/v1/admin/etl/status'),
  runSheets: (tabs?: string[]) => api<{ reports: Record<string, unknown>; global_errors: string[] }>(
    '/v1/admin/etl/sheets', { method: 'POST', body: JSON.stringify({ tabs }) }
  ),
  fixSalesDates: (dry_run = false) => api<{ total_orders: number; updated: number; skipped_no_date: number; skipped_already_ok: number; errors: string[]; sample_fixed: { order_number: string; from: string; to: string }[] }>(
    '/v1/admin/etl/fix-sales-dates', { method: 'POST', body: JSON.stringify({ dry_run }) }
  ),
  bootstrapSuppliers: () => api<{ total_legacy: number; created: number; skipped: number; errors: string[] }>(
    '/v1/admin/etl/bootstrap-suppliers', { method: 'POST', body: '{}' }
  ),
};

// ─── Inventory Counts ──────────────────────────────────────────────────────

export interface CountSessionOut {
  id: string;
  name: string;
  status: 'draft' | 'in_progress' | 'applied' | 'cancelled';
  notes: string | null;
  total_products_counted: number;
  total_with_difference: number;
  total_positive_delta: number;
  total_negative_delta: number;
  total_value_impact: number;
  applied_at: string | null;
  applied_by: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  items_count: number;
}

export interface CountItemOut {
  id: string;
  product_id: string;
  sku: string;
  product_name: string;
  category_name: string | null;
  unit_cost: number;
  system_qty: number;
  counted_qty: number | null;
  delta: number | null;
  value_impact: number | null;
  notes: string | null;
}

export interface CountSessionDetail extends CountSessionOut {
  items: CountItemOut[];
}

export interface UploadPreviewRow {
  sku: string;
  product_name: string;
  category_name: string | null;
  system_qty: number;
  counted_qty: number;
  delta: number;
  value_impact: number;
  unit_cost: number;
  status: 'ok' | 'surplus' | 'shortage' | 'not_found';
}

export interface UploadPreview {
  matched: number;
  not_found: number;
  with_difference: number;
  total_value_impact: number;
  rows: UploadPreviewRow[];
}

export interface CountSessionsResponse {
  items: CountSessionOut[];
  total: number;
  page: number;
  page_size: number;
}

export const inventoryCounts = {
  list: (page = 1) =>
    api<CountSessionsResponse>(`/v1/inventory-counts?page=${page}&page_size=20`),

  get: (id: string) =>
    api<CountSessionDetail>(`/v1/inventory-counts/${id}`),

  create: (payload: { name: string; notes?: string }) =>
    api<CountSessionOut>('/v1/inventory-counts', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  delete: (id: string) =>
    api(`/v1/inventory-counts/${id}`, { method: 'DELETE' }),

  apply: (id: string) =>
    api<{ status: string; products_counted: number; products_adjusted: number; total_positive_delta: number; total_negative_delta: number; total_value_impact: number }>(
      `/v1/inventory-counts/${id}/apply`,
      { method: 'POST', body: '{}' }
    ),

  downloadTemplate: (id: string) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('bp_admin_token') : null;
    const url = `${API_BASE}/v1/inventory-counts/${id}/template`;
    const a = document.createElement('a');
    a.href = url;
    // Attach auth via fetch + blob for proper download
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const burl = URL.createObjectURL(blob);
        a.href = burl;
        a.download = `conteo_${id.slice(0, 8)}.xlsx`;
        a.click();
        URL.revokeObjectURL(burl);
      });
  },

  downloadReport: (id: string) => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('bp_admin_token') : null;
    const url = `${API_BASE}/v1/inventory-counts/${id}/report`;
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => r.blob())
      .then((blob) => {
        const burl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = burl;
        a.download = `reporte_conteo_${id.slice(0, 8)}.xlsx`;
        a.click();
        URL.revokeObjectURL(burl);
      });
  },

  uploadExcel: async (id: string, file: File): Promise<UploadPreview> => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('bp_admin_token') : null;
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/v1/inventory-counts/${id}/upload`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error al procesar archivo' }));
      throw new Error(err.detail || 'Error al procesar archivo');
    }
    return res.json();
  },
};


// ── Stories IA ──────────────────────────────────────────────────────────────

export interface StoryItem {
  id: string;
  template_code: string | null;
  template_name: string | null;
  template_category: string | null;
  creation_mode: string;
  status: 'pending_approval' | 'approved' | 'rejected' | 'published' | 'failed' | 'scheduled';
  video_url: string | null;
  base_image_url: string | null;
  caption: string | null;
  swipe_up_url: string | null;
  scheduled_at: string;
  published_at: string | null;
  instagram_story_id: string | null;
  facebook_story_id: string | null;
  dry_run: boolean;
  image_cost_usd: number | null;
  video_duration_sec: number | null;
  error_message: string | null;
  created_at: string;
}

export interface StoriesResponse {
  stories: StoryItem[];
  total: number;
}

export const stories = {
  list: (status?: string) =>
    api<StoriesResponse>(`/v1/admin/stories${status ? `?status=${status}` : '?limit=100'}`),

  updateStatus: (id: string, status: 'approved' | 'rejected') =>
    api<{ id: string; status: string }>(`/v1/admin/stories/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),

  getConfig: () =>
    api<Record<string, { value: string; description: string }>>('/v1/admin/stories/config'),

  updateConfig: (key: string, value: string) =>
    api<{ key: string; value: string }>(`/v1/admin/stories/config/${key}`, {
      method: 'PATCH',
      body: JSON.stringify({ value }),
    }),

  generate: () =>
    api<{ queued: number; stories: string[] }>('/v1/admin/stories/manual', {
      method: 'POST',
      body: '{}',
    }),
};
