'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, ShoppingCart, Calendar, Star,
  RefreshCw, CheckCircle, Clock, ChevronRight,
  Play, Package, Truck, XCircle, Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { adminPortal, type PortalOrder, type PortalAppointment } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';

function formatAgo(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'hace un momento';
  if (mins < 60) return `hace ${mins} min`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `hace ${hrs} h`;
  return `hace ${Math.floor(hrs / 24)} días`;
}

function formatCOP(n: number | null) {
  if (!n) return '—';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(n);
}

// ── KPI Card ──────────────────────────────────────────────────────────

function KpiCard({ label, value, icon, sub, accent }: {
  label: string; value: string | number; icon: React.ReactNode; sub?: string;
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

// ── Order status config ────────────────────────────────────────────────

const ORDER_STATUS: Record<string, { label: string; color: string }> = {
  received:   { label: 'Recibido',   color: 'bg-blue-100 text-blue-700' },
  processing: { label: 'En proceso', color: 'bg-amber-100 text-amber-700' },
  invoiced:   { label: 'Facturado',  color: 'bg-purple-100 text-purple-700' },
  ready:      { label: 'Listo',      color: 'bg-green-100 text-green-700' },
  delivered:  { label: 'Entregado',  color: 'bg-gray-100 text-gray-600' },
  cancelled:  { label: 'Cancelado',  color: 'bg-red-100 text-red-600' },
};

const ORDER_NEXT: Record<string, { next: string; label: string; icon: React.ReactNode } | null> = {
  received:   { next: 'processing', label: 'Aceptar', icon: <Play className="h-3.5 w-3.5" /> },
  processing: { next: 'invoiced',   label: 'Facturar', icon: <Package className="h-3.5 w-3.5" /> },
  invoiced:   { next: 'ready',      label: 'Listo',    icon: <CheckCircle className="h-3.5 w-3.5" /> },
  ready:      { next: 'delivered',  label: 'Entregado', icon: <Truck className="h-3.5 w-3.5" /> },
  delivered:  null,
  cancelled:  null,
};

const APPT_STATUS: Record<string, { label: string; color: string }> = {
  pending:   { label: 'Pendiente',  color: 'bg-blue-100 text-blue-700' },
  confirmed: { label: 'Confirmada', color: 'bg-green-100 text-green-700' },
  completed: { label: 'Completada', color: 'bg-gray-100 text-gray-600' },
  cancelled: { label: 'Cancelada',  color: 'bg-red-100 text-red-600' },
};

// ── Página principal ──────────────────────────────────────────────────

export default function PetMonitorPage() {
  const qc = useQueryClient();
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [tab, setTab] = useState<'orders' | 'appointments'>('orders');

  const { data: kpis, isLoading: kpisLoading, isFetching, refetch: refetchKpis } = useQuery({
    queryKey: ['admin-portal-overview'],
    queryFn: adminPortal.overview,
    refetchInterval: 30_000,
    refetchIntervalInBackground: true,
  });

  const { data: pendingOrders, isLoading: ordersLoading, refetch: refetchOrders } = useQuery({
    queryKey: ['admin-portal-orders'],
    queryFn: () => adminPortal.orders(),
    refetchInterval: 30_000,
  });

  const { data: appointments, isLoading: apptLoading, refetch: refetchAppts } = useQuery({
    queryKey: ['admin-portal-appointments'],
    queryFn: () => adminPortal.appointments(),
    refetchInterval: 30_000,
  });

  useEffect(() => {
    if (kpis) setLastRefresh(new Date());
  }, [kpis]);

  function manualRefresh() {
    refetchKpis();
    refetchOrders();
    refetchAppts();
    setLastRefresh(new Date());
  }

  const { mutate: updateOrder, isPending: updatingOrder } = useMutation({
    mutationFn: ({ id, status, notes }: { id: string; status: string; notes?: string }) =>
      adminPortal.updateOrder(id, { status, notes }),
    onSuccess: (_, vars) => {
      toast.success(`Pedido → ${ORDER_STATUS[vars.status]?.label ?? vars.status}`);
      qc.invalidateQueries({ queryKey: ['admin-portal-orders'] });
      qc.invalidateQueries({ queryKey: ['admin-portal-overview'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const { mutate: updateAppt, isPending: updatingAppt } = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      adminPortal.updateAppointment(id, { status }),
    onSuccess: (_, vars) => {
      toast.success(`Cita → ${APPT_STATUS[vars.status]?.label ?? vars.status}`);
      qc.invalidateQueries({ queryKey: ['admin-portal-appointments'] });
      qc.invalidateQueries({ queryKey: ['admin-portal-overview'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const activeOrders = pendingOrders?.filter((o) => !['delivered', 'cancelled'].includes(o.status)) ?? [];

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">🐾 Portal Monitor</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Tiempo real del portal de clientes — polling cada 30 s
          </p>
        </div>
        <div className="flex items-center gap-3">
          <p className="text-xs text-gray-400">Actualizado {formatAgo(lastRefresh.toISOString())}</p>
          <Button variant="outline" size="sm" onClick={manualRefresh} disabled={isFetching} className="gap-2">
            <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
            Actualizar
          </Button>
        </div>
      </div>

      {/* KPIs */}
      {kpisLoading ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <Card key={i} className="h-24 animate-pulse bg-gray-50" />)}
        </div>
      ) : kpis ? (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <KpiCard label="Sesiones activas (24 h)" value={kpis.active_sessions_24h}
            icon={<Users className="h-5 w-5 text-teal-600" />} accent="teal" sub="clientes conectados hoy" />
          <KpiCard label="Pedidos pendientes" value={kpis.orders_pending}
            icon={<ShoppingCart className="h-5 w-5 text-amber-600" />}
            accent={kpis.orders_pending > 0 ? 'amber' : 'teal'} sub="recibidos + en proceso" />
          <KpiCard label="Citas hoy" value={kpis.appointments_today}
            icon={<Calendar className="h-5 w-5 text-brand" />} accent="brand" sub="pendientes o confirmadas" />
          <KpiCard label="Puntos otorgados (30 d)" value={(kpis.loyalty_points_30d ?? 0).toLocaleString('es-CO')}
            icon={<Star className="h-5 w-5 text-amber-500" />} accent="amber" sub="puntos de fidelidad" />
        </div>
      ) : null}

      {/* Tabs */}
      <div className="flex gap-2 border-b border-gray-200">
        {(['orders', 'appointments'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px ${
              tab === t ? 'border-teal-600 text-teal-700' : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'orders' ? (
              <span className="flex items-center gap-1.5">
                <ShoppingCart className="h-4 w-4" />
                Pedidos
                {activeOrders.length > 0 && (
                  <span className="bg-amber-100 text-amber-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {activeOrders.length}
                  </span>
                )}
              </span>
            ) : (
              <span className="flex items-center gap-1.5">
                <Calendar className="h-4 w-4" />
                Citas
                {(kpis?.appointments_today ?? 0) > 0 && (
                  <span className="bg-blue-100 text-blue-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {kpis?.appointments_today}
                  </span>
                )}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* ── PEDIDOS ──────────────────────────────────────────────────────── */}
      {tab === 'orders' && (
        <Card className="p-5">
          {ordersLoading && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => <div key={i} className="h-16 rounded-lg bg-gray-50 animate-pulse" />)}
            </div>
          )}

          {!ordersLoading && (pendingOrders ?? []).length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
              <CheckCircle className="h-8 w-8 text-green-400" />
              <p className="text-sm">Sin pedidos activos</p>
            </div>
          )}

          <div className="space-y-3">
            {pendingOrders?.map((order) => {
              const { label, color } = ORDER_STATUS[order.status] ?? { label: order.status, color: 'bg-gray-100 text-gray-600' };
              const nextAction = ORDER_NEXT[order.status];
              return (
                <div key={order.id} className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                  <div className="text-xl mt-0.5">📦</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-gray-900">{order.product_name}</p>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>{label}</span>
                      {order.invoice_number && (
                        <span className="text-xs text-purple-600 font-mono">{order.invoice_number}</span>
                      )}
                      {order.sales_order_id && (
                        <span className="text-[10px] bg-emerald-100 text-emerald-700 font-semibold px-1.5 py-0.5 rounded-full">
                          ✓ En ventas
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {order.customer_name ?? 'Cliente'}{order.pet_name ? ` · ${order.pet_name}` : ''} · ×{order.quantity}
                      {order.unit_price ? ` · ${formatCOP(order.unit_price * order.quantity)}` : ''} · {formatAgo(order.created_at)}
                    </p>
                  </div>
                  {nextAction && (
                    <Button
                      size="sm"
                      variant="outline"
                      disabled={updatingOrder}
                      onClick={() => updateOrder({ id: order.id, status: nextAction.next })}
                      className="shrink-0 gap-1.5 text-xs"
                    >
                      {updatingOrder ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : nextAction.icon}
                      {nextAction.label}
                    </Button>
                  )}
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── CITAS ────────────────────────────────────────────────────────── */}
      {tab === 'appointments' && (
        <Card className="p-5">
          {apptLoading && (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => <div key={i} className="h-16 rounded-lg bg-gray-50 animate-pulse" />)}
            </div>
          )}

          {!apptLoading && (appointments ?? []).length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
              <Clock className="h-8 w-8 text-gray-300" />
              <p className="text-sm">Sin citas programadas</p>
            </div>
          )}

          <div className="space-y-3">
            {appointments?.map((appt) => {
              const { label, color } = APPT_STATUS[appt.status] ?? { label: appt.status, color: 'bg-gray-100 text-gray-600' };
              const dt = new Date(appt.scheduled_at);
              return (
                <div key={appt.id} className="flex items-start gap-3 p-3 rounded-xl bg-gray-50 hover:bg-gray-100 transition-colors">
                  <div className="text-xl mt-0.5">📅</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-semibold text-gray-900 capitalize">
                        {appt.service_type}{appt.pet_name ? ` — ${appt.pet_name}` : ''}
                      </p>
                      <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>{label}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">
                      {appt.customer_name ?? 'Cliente'} ·{' '}
                      {dt.toLocaleDateString('es-CO', { weekday: 'short', day: 'numeric', month: 'short' })} a las{' '}
                      {dt.toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {appt.status === 'pending' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={updatingAppt}
                        onClick={() => updateAppt({ id: appt.id, status: 'confirmed' })}
                        className="gap-1.5 text-xs"
                      >
                        {updatingAppt ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <CheckCircle className="h-3.5 w-3.5" />}
                        Confirmar
                      </Button>
                    )}
                    {appt.status === 'confirmed' && (
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={updatingAppt}
                        onClick={() => updateAppt({ id: appt.id, status: 'completed' })}
                        className="gap-1.5 text-xs"
                      >
                        <CheckCircle className="h-3.5 w-3.5" />
                        Completar
                      </Button>
                    )}
                    {['pending', 'confirmed'].includes(appt.status) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={updatingAppt}
                        onClick={() => {
                          if (confirm('¿Cancelar esta cita?')) {
                            updateAppt({ id: appt.id, status: 'cancelled' });
                          }
                        }}
                        className="text-red-500 hover:text-red-600 hover:bg-red-50 text-xs"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                      </Button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}
    </div>
  );
}
