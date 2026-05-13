/**
 * Cliente HTTP tipado para el backend FastAPI.
 * Lee el token del localStorage en el cliente; en server components usar cookies.
 */
export const API_BASE =
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
  stock_qty: number;
  in_stock: boolean;
}

export interface PaginatedProducts {
  items: Product[];
  total: number;
  page: number;
  page_size: number;
}

export const products = {
  list: (params: { page?: number; page_size?: number; q?: string; is_published?: boolean; category?: string } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    if (params.q) qs.set('q', params.q);
    if (params.is_published !== undefined) qs.set('is_published', String(params.is_published));
    if (params.category) qs.set('category', params.category);
    return api<PaginatedProducts>(`/v1/products?${qs.toString()}`);
  },
  get: (id: string) => api<Product>(`/v1/products/${id}`),
  create: (payload: Partial<Product> & { sku: string; name: string }) =>
    api<Product>('/v1/products', { method: 'POST', body: JSON.stringify(payload) }),
  update: (id: string, payload: Partial<Product>) =>
    api<Product>(`/v1/products/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }),
  brands: () => api<{ id: string; name: string; slug: string }[]>('/v1/brands'),
  categories: () => api<{ id: string; name: string; slug: string }[]>('/v1/categories'),
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
    return api<{ items: Order[]; total: number; page: number; page_size: number }>(`/v1/sales/orders?${qs.toString()}`);
  },
  get: (id: string) => api<Order>(`/v1/sales/orders/${id}`),
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
  city: string | null;
  notes: string | null;
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
  update: (id: string, payload: {
    full_name?: string;
    document_id?: string;
    email?: string;
    phone?: string;
    city?: string;
    notes?: string;
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
  legacy_id: string;
  fecha: string;
  ventas_efectivo: number;
  gastos_efectivo: number;
  saldo_inicial: number;
  saldo_final: number;
  diferencia: number;
  notas: string;
}

export const cashClosings = {
  list: (params: { page?: number; page_size?: number } = {}) => {
    const qs = new URLSearchParams();
    if (params.page) qs.set('page', String(params.page));
    if (params.page_size) qs.set('page_size', String(params.page_size));
    return api<{ items: CashClosing[]; total: number; page: number; page_size: number }>(`/v1/cash-closings?${qs.toString()}`);
  },
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
  listSkus: (id: string) => api<{ items: { sku_proveedor: string; product_id: string; product_sku: string; product_name: string; factor_pack: number; last_unit_cost: number; last_tax_pct: number; last_seen_at: string }[] }>(`/v1/suppliers/${id}/skus`),
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

