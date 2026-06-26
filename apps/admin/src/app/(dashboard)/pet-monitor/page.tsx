'use client';

import { useEffect, useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Users, ShoppingCart, Calendar, Star,
  RefreshCw, CheckCircle, Clock, AlertCircle,
} from 'lucide-react';
import { api } from '@/lib/api';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'hace un momento';
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs} h`;
  return `hace ${Math.floor(hrs / 24)} días`;
}
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

// ── Tipos del endpoint /v1/admin/pet-monitor ──────────────────────────

interface MonitorKPIs {
  active_sessions_24h: number;
  orders_pending: number;
  appointments_today: number;
  loyalty_points_issued_30d: number;
}

interface PendingOrder {
  id: string;
  customer_name: string | null;
  product_name: string;
  quantity: number;
  status: string;
  created_at: string;
}

interface UpcomingAppointment {
  id: string;
  customer_name: string | null;
  pet_name: string | null;
  service_type: string;
  scheduled_at: string;
  status: string;
}

interface MonitorData {
  kpis: MonitorKPIs;
  pending_orders: PendingOrder[];
  upcoming_appointments: UpcomingAppointment[];
  as_of: string;
}

// ── API call (usa el cliente admin existente) ─────────────────────────

async function fetchMonitor(): Promise<MonitorData> {
  return api<MonitorData>('/v1/admin/pet-monitor');
}

// ── Componentes ───────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  icon,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  sub?: string;
  accent?: 'brand' | 'rose' | 'amber' | 'emerald' | 'teal';
}) {
  const colors: Record<string, string> = {
    teal:    'border-teal-200 bg-teal-50/50',
    brand:   'border-brand/20 bg-brand/5',
    rose:    'border-rose-200 bg-rose-50/50',
    amber:   'border-amber-200 bg-amber-50/50',
    emerald: 'border-emerald-200 bg-emerald-50/50',
  };
  return (
    <Card className={`p-4 border ${colors[accent ?? 'teal']}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-medium text-gray-500 mb-1">{label}</p>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        <div className="p-2 rounded-lg bg-white/60">{icon}</div>
      </div>
    </Card>
  );
}

const ORDER_STATUS: Record<string, { label: string; color: string }> = {
  received:   { label: 'Recibido',   color: 'bg-blue-100 text-blue-700' },
  processing: { label: 'En proceso', color: 'bg-amber-100 text-amber-700' },
  ready:      { label: 'Listo',      color: 'bg-green-100 text-green-700' },
  delivered:  { label: 'Entregado',  color: 'bg-gray-100 text-gray-600' },
};

const APPT_STATUS: Record<string, { label: string; color: string }> = {
  pending:   { label: 'Pendiente',  color: 'bg-blue-100 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-green-100 text-green-700' },
};

// ── Página principal ──────────────────────────────────────────────────

export default function PetMonitorPage() {
  const qc = useQueryClient();
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: ['pet-monitor'],
    queryFn: fetchMonitor,
    refetchInterval: 30_000,  // 30 segundos
    refetchIntervalInBackground: true,
  });

  // Actualizar lastRefresh cuando los datos lleguen
  useEffect(() => {
    if (data) setLastRefresh(new Date());
  }, [data]);

  function manualRefresh() {
    refetch();
    setLastRefresh(new Date());
  }

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            🐾 Portal Monitor
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Tiempo real del portal de clientes — polling cada 30 s
          </p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-xs text-gray-400">
            Actualizado{' '}
            {formatAgo(lastRefresh.toISOString())}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={manualRefresh}
            disabled={isFetching}
            className="gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      {isLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="h-24 animate-pulse bg-gray-50" />
          ))}
        </div>
      ) : data ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard
            label="Sesiones activas (24 h)"
            value={data.kpis.active_sessions_24h}
            icon={<Users className="h-5 w-5 text-teal-600" />}
            accent="teal"
            sub="clientes conectados hoy"
          />
          <KpiCard
            label="Pedidos pendientes"
            value={data.kpis.orders_pending}
            icon={<ShoppingCart className="h-5 w-5 text-amber-600" />}
            accent={data.kpis.orders_pending > 0 ? 'amber' : 'teal'}
            sub="recibidos + en proceso"
          />
          <KpiCard
            label="Citas hoy"
            value={data.kpis.appointments_today}
            icon={<Calendar className="h-5 w-5 text-brand" />}
            accent="brand"
            sub="pendientes o confirmadas"
          />
          <KpiCard
            label="Puntos otorgados (30 d)"
            value={data.kpis.loyalty_points_issued_30d.toLocaleString('es-CO')}
            icon={<Star className="h-5 w-5 text-amber-500" />}
            accent="amber"
            sub="puntos de fidelidad"
          />
        </div>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Pedidos pendientes */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <ShoppingCart className="h-4 w-4 text-amber-600" />
              Pedidos por atender
            </h2>
            {data && (
              <Badge variant="secondary" className="text-xs">
                {data.pending_orders.length} pendiente{data.pending_orders.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>

          {isLoading && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-14 rounded-lg bg-gray-50 animate-pulse" />
              ))}
            </div>
          )}

          {data?.pending_orders.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
              <CheckCircle className="h-8 w-8 text-green-400" />
              <p className="text-sm">Sin pedidos pendientes</p>
            </div>
          )}

          <div className="space-y-2">
            {data?.pending_orders.map((order) => {
              const { label, color } = ORDER_STATUS[order.status] ?? { label: order.status, color: 'bg-gray-100 text-gray-600' };
              return (
                <div key={order.id} className="flex items-center gap-3 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                  <div className="text-xl">📦</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 truncate">{order.product_name}</p>
                    <p className="text-xs text-gray-500">
                      {order.customer_name ?? 'Cliente'} · ×{order.quantity} ·{' '}
                      {formatAgo(order.created_at)}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full shrink-0 ${color}`}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>

        {/* Citas próximas */}
        <Card className="p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-gray-900 flex items-center gap-2">
              <Calendar className="h-4 w-4 text-brand" />
              Citas próximas (7 días)
            </h2>
            {data && (
              <Badge variant="secondary" className="text-xs">
                {data.upcoming_appointments.length} cita{data.upcoming_appointments.length !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>

          {isLoading && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-14 rounded-lg bg-gray-50 animate-pulse" />
              ))}
            </div>
          )}

          {data?.upcoming_appointments.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
              <Clock className="h-8 w-8 text-gray-300" />
              <p className="text-sm">Sin citas en los próximos 7 días</p>
            </div>
          )}

          <div className="space-y-2">
            {data?.upcoming_appointments.map((appt) => {
              const { label, color } = APPT_STATUS[appt.status] ?? { label: appt.status, color: 'bg-gray-100 text-gray-600' };
              const dt = new Date(appt.scheduled_at);
              return (
                <div key={appt.id} className="flex items-center gap-3 p-3 rounded-xl bg-gray-50">
                  <div className="text-xl">📅</div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-gray-900 capitalize">
                      {appt.service_type}
                      {appt.pet_name ? ` — ${appt.pet_name}` : ''}
                    </p>
                    <p className="text-xs text-gray-500">
                      {appt.customer_name ?? 'Cliente'} ·{' '}
                      {dt.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })} a las{' '}
                      {dt.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full shrink-0 ${color}`}>
                    {label}
                  </span>
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
