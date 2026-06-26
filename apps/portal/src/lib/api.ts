/**
 * Cliente API del portal — todas las llamadas van a /api/v1/portal/*
 * Las cookies de sesión se envían automáticamente (credentials: 'include').
 */

const BASE = '/api/v1/portal';

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? 'Error del servidor');
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ── Auth ──────────────────────────────────────────────────────────────

export interface LoginResponse {
  status: 'existing' | 'new';
  customer_id: string;
  full_name: string | null;
  has_pets: boolean;
  pet_name: string | null;
  rfm_segment: string | null;
}

export interface MeResponse {
  customer_id: string;
  full_name: string;
  document_id: string | null;
  phone: string | null;
  email: string | null;
  address: string | null;
  city: string | null;
  rfm_segment: string | null;
  rfm_monetary: number | null;
  legacy_pet_name: string | null;
  legacy_pet_type: string | null;
  terms_accepted_at: string | null;
  data_consent_at: string | null;
}

export const auth = {
  login: (document_id: string, phone: string) =>
    request<LoginResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ document_id, phone }),
    }),
  logout: () => request<{ ok: boolean }>('/auth/logout', { method: 'POST' }),
  me: () => request<MeResponse>('/auth/me'),
  updateMe: (data: Partial<MeResponse>) =>
    request<MeResponse>('/auth/me', { method: 'PATCH', body: JSON.stringify(data) }),
  acceptTerms: (version = '1.0') =>
    request<MeResponse>('/auth/me/accept-terms', {
      method: 'POST',
      body: JSON.stringify({ terms: true, data_consent: true, version }),
    }),
};

// ── Pets ──────────────────────────────────────────────────────────────

export interface HealthRecord {
  id: string;
  record_type: string;
  name: string;
  applied_at: string;
  next_due_at: string | null;
  vet_name: string | null;
  notes: string | null;
  created_at: string;
  days_until_due: number | null;
  alert_level: 'ok' | 'soon' | 'overdue' | null;
}

export interface Pet {
  id: string;
  name: string;
  species: string;
  breed: string | null;
  birth_date: string | null;
  weight_kg: number | null;
  food_brand: string | null;
  food_freq_days: number | null;
  color_theme: 'teal' | 'coral' | 'amber' | 'purple' | 'pink' | 'green';
  photo_url: string | null;
  notes: string | null;
  created_at: string;
  age_years: number | null;
  age_months: number | null;
  health_records: HealthRecord[];
}

export type PetCreate = {
  name: string;
  species: string;
  color_theme: Pet['color_theme'];
  breed?: string | null;
  birth_date?: string | null;
  weight_kg?: number | null;
  food_brand?: string | null;
  food_freq_days?: number | null;
  photo_url?: string | null;
  notes?: string | null;
};

export const pets = {
  list: () => request<Pet[]>('/pets'),
  get: (id: string) => request<Pet>(`/pets/${id}`),
  create: (data: PetCreate) =>
    request<Pet>('/pets', { method: 'POST', body: JSON.stringify(data) }),
  update: (id: string, data: Partial<PetCreate>) =>
    request<Pet>(`/pets/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  delete: (id: string) => request<{ ok: boolean }>(`/pets/${id}`, { method: 'DELETE' }),
  addHealthRecord: (petId: string, data: Omit<HealthRecord, 'id' | 'created_at' | 'days_until_due' | 'alert_level'>) =>
    request<HealthRecord>(`/pets/${petId}/health`, { method: 'POST', body: JSON.stringify(data) }),
  uploadPhoto: async (petId: string, file: File): Promise<Pet> => {
    const form = new FormData();
    form.append('file', file);
    const res = await fetch(`${BASE}/pets/${petId}/photo`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail ?? 'Error al subir foto');
    }
    return res.json() as Promise<Pet>;
  },
  carnetUrl: (petId: string) => `${BASE}/pets/${petId}/carnet.pdf`,
};

// ── Orders ────────────────────────────────────────────────────────────

export interface Order {
  id: string;
  product_id: string | null;
  product_name: string;
  pet_id: string | null;
  quantity: number;
  unit_price: number | null;
  status: 'received' | 'processing' | 'ready' | 'delivered' | 'cancelled';
  notes: string | null;
  created_at: string;
  points_earned: number | null;
}

export const orders = {
  list: (page = 1) => request<Order[]>(`/orders?page=${page}`),
  get: (id: string) => request<Order>(`/orders/${id}`),
  create: (data: { product_id: string; pet_id?: string; quantity?: number; notes?: string }) =>
    request<Order>('/orders', { method: 'POST', body: JSON.stringify(data) }),
};

// ── Appointments ──────────────────────────────────────────────────────

export interface Appointment {
  id: string;
  pet_id: string;
  service_type: string;
  scheduled_at: string;
  duration_min: number;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  price: number | null;
  notes: string | null;
  created_at: string;
}

export interface AvailabilitySlot {
  time: string;
  available: boolean;
  reason: string | null;
}

export interface AvailabilityResponse {
  date: string;
  service: string;
  slots: AvailabilitySlot[];
}

export const appointments = {
  list: (upcomingOnly = false) =>
    request<Appointment[]>(`/appointments?upcoming_only=${upcomingOnly}`),
  get: (id: string) => request<Appointment>(`/appointments/${id}`),
  create: (data: { pet_id: string; service_type: string; scheduled_at: string; notes?: string }) =>
    request<Appointment>('/appointments', { method: 'POST', body: JSON.stringify(data) }),
  cancel: (id: string) =>
    request<Appointment>(`/appointments/${id}/cancel`, { method: 'PATCH' }),
  availability: (date: string, service: string) =>
    request<AvailabilityResponse>(`/appointments/availability?date=${date}&service=${encodeURIComponent(service)}`),
};

// ── Notifications ─────────────────────────────────────────────────────────

export interface PortalNotification {
  id: string;
  type: string;
  title: string;
  body: string;
  is_admin: boolean;
  read_at: string | null;
  created_at: string;
  data: Record<string, unknown>;
}

export const notifications = {
  list: (unreadOnly = false) =>
    request<PortalNotification[]>(`/notifications${unreadOnly ? '?unread_only=true' : ''}`),
  unreadCount: () => request<{ unread: number }>('/notifications/unread-count'),
  markAllRead: () => request<{ ok: boolean }>('/notifications/read-all', { method: 'POST' }),
  eventsUrl: () => `${BASE}/notifications/events`,
};

// ── Loyalty ───────────────────────────────────────────────────────────

export interface LoyaltyBalance {
  total_active: number;
  total_earned_lifetime: number;
  history: {
    id: string;
    points: number;
    reason: string;
    description: string | null;
    expires_at: string;
    created_at: string;
  }[];
}

export const loyalty = {
  balance: () => request<LoyaltyBalance>('/loyalty/balance'),
};

// ── Productos públicos (para el catálogo de pedidos) ──────────────────

export interface PublicProduct {
  id: string;
  name: string;
  slug: string;
  price: number;
  image_url: string | null;
  category: string | null;
  species_tag: string | null;
}

export const catalog = {
  list: (search?: string, species?: string) => {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (species) params.set('species', species);
    // Productos públicos — va al endpoint del store, no al portal
    return fetch(`/api/v1/products?${params}&published=true&limit=100`)
      .then((r) => r.json()) as Promise<{ items: PublicProduct[] }>;
  },
};

// ── Inteligencia — Smart Cards + Completion ───────────────────────────

export interface SmartCard {
  type: 'reorder' | 'vaccine_due' | 'appointment' | 'birthday' | 'loyalty';
  pet_id: string | null;
  pet_name: string | null;
  color_theme: string;
  title: string;
  subtitle: string;
  cta: string;
  action_url: string;
  urgency: 'high' | 'medium' | 'low';
  badge: string | null;
}

export interface MissingField {
  entity: 'customer' | 'pet';
  entity_id: string | null;
  field: string;
  label: string;
  reason: string;
  points_reward: number;
  priority: number;
}

export interface CompletionResponse {
  percentage: number;
  missing_fields: MissingField[];
}

export const intelligence = {
  smartCards: () => request<SmartCard[]>('/me/smart-cards'),
  completion: () => request<CompletionResponse>('/me/completion'),
  updateField: (entity: string, entityId: string | null, field: string, value: unknown) => {
    if (entity === 'customer') {
      return request<MeResponse>('/auth/me', {
        method: 'PATCH',
        body: JSON.stringify({ [field]: value }),
      });
    }
    return request<Pet>(`/pets/${entityId}`, {
      method: 'PATCH',
      body: JSON.stringify({ [field]: value }),
    });
  },
};

export { ApiError };
