/**
 * Cliente HTTP tipado para el backend FastAPI — panel de aliados.
 * Token JWT propio (scope: "partner"), separado del de admin/portal.
 * Incluye auto-refresh transparente + logout automático si la sesión venció.
 */
import { useAuth } from './auth-store';

export const API_BASE =
  typeof window === 'undefined'
    ? process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'
    : process.env.NEXT_PUBLIC_API_BASE_URL || '';

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(message: string, status: number, detail: unknown) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

let _refreshPromise: Promise<string> | null = null;

async function refreshAccessToken(): Promise<string> {
  const refreshToken = useAuth.getState().refreshToken;
  if (!refreshToken) throw new Error('no_refresh_token');

  const res = await fetch(`${API_BASE}/v1/partner/auth/refresh`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh_token: refreshToken }),
    cache: 'no-store',
  });

  if (!res.ok) {
    useAuth.getState().clear();
    if (typeof window !== 'undefined') window.location.href = '/login';
    throw new Error('session_expired');
  }

  const data = await res.json();
  useAuth.getState().setSession(data.partner_user, data.access_token, data.refresh_token);
  return data.access_token as string;
}

const FETCH_TIMEOUT_MS = 20_000;

export async function api<T = unknown>(
  path: string,
  init: RequestInit & { auth?: boolean; _retry?: boolean } = {}
): Promise<T> {
  const { auth = true, _retry = false, headers, ...rest } = init;
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`;
  const token = auth ? useAuth.getState().token : null;
  const finalHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(headers as Record<string, string>),
  };
  if (token) finalHeaders.Authorization = `Bearer ${token}`;

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(url, { ...rest, headers: finalHeaders, cache: 'no-store', signal: controller.signal });
  } catch {
    clearTimeout(timeoutId);
    throw new ApiError('No se pudo conectar con el servidor. Verifica tu conexión.', 0, null);
  }
  clearTimeout(timeoutId);

  const ct = res.headers.get('content-type') || '';
  const data = ct.includes('application/json') ? await res.json() : await res.text();

  if (res.status === 401 && auth && !_retry) {
    try {
      if (!_refreshPromise) {
        _refreshPromise = refreshAccessToken().finally(() => {
          _refreshPromise = null;
        });
      }
      await _refreshPromise;
      return api<T>(path, { ...init, _retry: true });
    } catch {
      throw new ApiError('Sesión expirada, inicia sesión de nuevo', 401, null);
    }
  }

  if (!res.ok) {
    const detail = typeof data === 'object' ? (data as { detail?: string }).detail : data;
    throw new ApiError(typeof detail === 'string' ? detail : 'Error de servidor', res.status, data);
  }
  return data as T;
}

// ── Tipos ─────────────────────────────────────────────────────────────

export type PartnerType = 'vet' | 'walker' | 'shelter' | 'groomer';

export interface PartnerInfo {
  id: string;
  slug: string;
  partner_type: PartnerType;
  business_name: string;
  city: string;
  is_published: boolean;
  is_verified: boolean;
}

export interface PartnerUserInfo {
  id: string;
  email: string;
  full_name: string;
  role: string;
  partner: PartnerInfo;
}

export interface PartnerProfile {
  id: string;
  slug: string;
  partner_type: PartnerType;
  business_name: string;
  legal_name: string;
  document_id: string;
  email: string | null;
  phone: string | null;
  whatsapp: string | null;
  address: string | null;
  city: string;
  lat: number | null;
  lng: number | null;
  logo_url: string | null;
  cover_url: string | null;
  bio: string | null;
  rating_avg: number;
  rating_count: number;
  is_published: boolean;
  is_verified: boolean;
}

export interface PartnerServiceItem {
  id: string;
  slug: string;
  name: string;
  description: string | null;
  duration_min: number | null;
  price: number | null;
  price_type: 'fixed' | 'from' | 'quote';
  category: string;
  requires_pet: boolean;
  is_active: boolean;
}

export interface ServiceSlotItem {
  id: string;
  service_id: string | null;
  day_of_week: number;
  start_time: string;
  end_time: string;
  slot_minutes: number;
  max_bookings: number;
  is_active: boolean;
}

export interface BookingItem {
  id: string;
  customer_id: string;
  service_id: string | null;
  pet_id: string | null;
  scheduled_at: string;
  duration_min: number;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled' | 'no_show';
  price_snapshot: number | null;
  notes_customer: string | null;
  notes_partner: string | null;
  cancelled_reason: string | null;
  created_at: string;
}

export interface PartnerReviewItem {
  id: string;
  rating: number;
  comment: string | null;
  created_at: string;
}

export interface DashboardData {
  partner: PartnerProfile;
  pending_bookings: number;
  today_bookings: number;
}

// ── Auth ──────────────────────────────────────────────────────────────

export interface RegisterPayload {
  partner_type: PartnerType;
  business_name: string;
  legal_name: string;
  document_id: string;
  city: string;
  address?: string;
  phone?: string;
  whatsapp?: string;
  lat?: number;
  lng?: number;
  bio?: string;
  full_name: string;
  email: string;
  password: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  partner_user: PartnerUserInfo;
}

export const partnerAuth = {
  register: (payload: RegisterPayload) =>
    api<TokenResponse>('/v1/partner/auth/register', {
      method: 'POST',
      auth: false,
      body: JSON.stringify(payload),
    }),
  login: (email: string, password: string) =>
    api<TokenResponse>('/v1/partner/auth/login', {
      method: 'POST',
      auth: false,
      body: JSON.stringify({ email, password }),
    }),
  me: () => api<PartnerUserInfo>('/v1/partner/auth/me'),
};

// ── Panel del aliado ─────────────────────────────────────────────────

export const partner = {
  dashboard: () => api<DashboardData>('/v1/partner/dashboard'),

  profile: {
    get: () => api<PartnerProfile>('/v1/partner/profile'),
    update: (payload: Partial<PartnerProfile>) =>
      api<PartnerProfile>('/v1/partner/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  },

  services: {
    list: () => api<PartnerServiceItem[]>('/v1/partner/services'),
    create: (payload: Omit<PartnerServiceItem, 'id' | 'slug' | 'is_active'>) =>
      api<PartnerServiceItem>('/v1/partner/services', { method: 'POST', body: JSON.stringify(payload) }),
    update: (id: string, payload: Omit<PartnerServiceItem, 'id' | 'slug' | 'is_active'>) =>
      api<PartnerServiceItem>(`/v1/partner/services/${id}`, { method: 'PUT', body: JSON.stringify(payload) }),
    remove: (id: string) => api<{ ok: boolean }>(`/v1/partner/services/${id}`, { method: 'DELETE' }),
  },

  slots: {
    list: () => api<ServiceSlotItem[]>('/v1/partner/slots'),
    create: (payload: {
      service_id?: string | null;
      day_of_week: number;
      start_time: string;
      end_time: string;
      slot_minutes: number;
      max_bookings: number;
    }) => api<ServiceSlotItem>('/v1/partner/slots', { method: 'POST', body: JSON.stringify(payload) }),
    remove: (id: string) => api<{ ok: boolean }>(`/v1/partner/slots/${id}`, { method: 'DELETE' }),
  },

  bookings: {
    list: (status?: string) =>
      api<BookingItem[]>(`/v1/partner/bookings${status ? `?status=${status}` : ''}`),
    confirm: (id: string, notes_partner?: string) =>
      api<BookingItem>(`/v1/partner/bookings/${id}/confirm`, {
        method: 'PATCH',
        body: JSON.stringify({ notes_partner }),
      }),
    complete: (id: string, notes_partner?: string) =>
      api<BookingItem>(`/v1/partner/bookings/${id}/complete`, {
        method: 'PATCH',
        body: JSON.stringify({ notes_partner }),
      }),
    noShow: (id: string) => api<BookingItem>(`/v1/partner/bookings/${id}/no-show`, { method: 'PATCH' }),
    cancel: (id: string, reason?: string) =>
      api<BookingItem>(`/v1/partner/bookings/${id}/cancel`, {
        method: 'PATCH',
        body: JSON.stringify({ reason }),
      }),
  },

  reviews: {
    list: () => api<PartnerReviewItem[]>('/v1/partner/reviews'),
  },
};
