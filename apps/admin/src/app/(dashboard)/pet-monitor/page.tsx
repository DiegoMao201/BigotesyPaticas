'use client';

import { useEffect, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, ShoppingCart, Calendar, Star,
  RefreshCw, CheckCircle, Clock, ChevronRight,
  Package, Truck, XCircle, Loader2, Eye,
} from 'lucide-react';
import { adminPortal, type PortalOrder, type PortalAppointment } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { OrderDetailDrawer } from './OrderDetailDrawer';

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

// ── Workflow status config (sprint-2) ─────────────────────────────────

const WORKFLOW_STATUS: Record<string, { label: string; color: string; emoji: string }> = {
  received:            { label: 'Recibido',              color: 'bg-blue-100 text-blue-700',     emoji: '📥' },
  under_review:        { label: 'En revisión',           color: 'bg-purple-100 text-purple-700', emoji: '🔍' },
  awaiting_customer:   { label: 'Esp. cliente',          color: 'bg-amber-100 text-amber-700',   emoji: '⏳' },
  ready_to_invoice:    { label: 'Listo/facturar',        color: 'bg-sky-100 text-sky-700',       emoji: '📋' },
  invoiced:            { label: 'Facturado',             color: 'bg-indigo-100 text-indigo-700', emoji: '🧾' },
  in_preparation:      { label: 'Preparando',            color: 'bg-orange-100 text-orange-700', emoji: '🔧' },
  ready_for_delivery:  { label: 'Listo/entregar',        color: 'bg-teal-100 text-teal-700',     emoji: '📦' },
  in_transit:          { label: 'En camino',             color: 'bg-cyan-100 text-cyan-700',     emoji: '🚚' },
  delivered:           { label: 'Entregado',             color: 'bg-green-100 text-green-700',   emoji: '✅' },
  cancelled:           { label: 'Cancelado',             color: 'bg-red-100 text-red-600',       emoji: '❌' },
  returned:            { label: 'Devuelto',              color: 'bg-gray-100 text-gray-600',     emoji: '↩️' },
};

const WORKFLOW_TABS = [
  { key: 'active',  label: 'Activos',    statuses: ['received', 'under_review', 'awaiting_customer', 'ready_to_invoice', 'invoiced', 'in_preparation', 'ready_for_delivery', 'in_transit'] },
  { key: 'delivered', label: 'Entregados', statuses: ['delivered'] },
  { key: 'cancelled', label: 'Cancelados', statuses: ['cancelled', 'returned'] },
];

const APPT_STATUS: Record<string, { label: string; color: string }> = {
  pending:                     { label: 'Pendiente',                  color: 'bg-blue-100 text-blue-700' },
  confirmed:                   { label: 'Confirmada',                 color: 'bg-green-100 text-green-700' },
  awaiting_customer_reschedule:{ label: 'Esp. cliente (reagendar)',   color: 'bg-amber-100 text-amber-700' },
  rescheduled:                 { label: 'Reagendada',                 color: 'bg-purple-100 text-purple-700' },
  in_progress:                 { label: 'En curso',                   color: 'bg-teal-100 text-teal-700' },
  completed:                   { label: 'Completada',                 color: 'bg-gray-100 text-gray-600' },
  no_show:                     { label: 'No asistió',                 color: 'bg-red-100 text-red-600' },
  cancelled:                   { label: 'Cancelada',                  color: 'bg-red-100 text-red-600' },
};

// ── Página principal ──────────────────────────────────────────────────

export default function PetMonitorPage() {
  const qc = useQueryClient();
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [mainTab, setMainTab] = useState<'orders' | 'appointments'>('orders');
  const [workflowTab, setWorkflowTab] = useState<'active' | 'delivered' | 'cancelled'>('active');
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(null);

  const { data: kpis, isLoading: kpisLoading, isFetching, refetch: refetchKpis } = useQuery({
    queryKey: ['admin-portal-overview'],
    queryFn: adminPortal.overview,
    refetchInterval: 30_000,
    refetchIntervalInBackground: true,
  });

  const { data: allOrders = [], isLoading: ordersLoading, refetch: refetchOrders } = useQuery({
    queryKey: ['admin-portal-orders'],
    queryFn: () => adminPortal.orders(),
    refetchInterval: 30_000,
  });

  const { data: appointments = [], isLoading: apptLoading, refetch: refetchAppts } = useQuery({
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

  const { mutate: updateAppt, isPending: updatingAppt } = useMutation({
    mutationFn: ({ id, status, cancel_reason }: { id: string; status: string; cancel_reason?: string }) =>
      adminPortal.updateAppointment(id, { status, cancel_reason }),
    onSuccess: (_, vars) => {
      const label = APPT_STATUS[vars.status]?.label ?? vars.status;
      toast.success(`Cita → ${label}`);
      qc.invalidateQueries({ queryKey: ['admin-portal-appointments'] });
      qc.invalidateQueries({ queryKey: ['admin-portal-overview'] });
    },
    onError: (err: Error) => toast.error(err.message),
  });

  // Filter orders by tab
  const currentTabStatuses = WORKFLOW_TABS.find((t) => t.key === workflowTab)?.statuses ?? [];
  const filteredOrders = allOrders.filter((o) => {
    const ws = o.workflow_status ?? o.status;
    return currentTabStatuses.includes(ws);
  });

  const activeCount = allOrders.filter((o) => {
    const ws = o.workflow_status ?? o.status;
    return ['received', 'under_review', 'awaiting_customer', 'ready_to_invoice', 'invoiced', 'in_preparation', 'ready_for_delivery', 'in_transit'].includes(ws);
  }).length;

  const awaitingCount = allOrders.filter((o) => (o.workflow_status ?? o.status) === 'awaiting_customer').length;

  return (
    <div className="space-y-6 p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Pet Monitor</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Última actualización: {lastRefresh.toLocaleTimeString('es-CO')}
            {isFetching && <Loader2 className="inline h-3 w-3 animate-spin ml-1" />}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={manualRefresh} className="gap-1.5">
          <RefreshCw className="h-4 w-4" /> Actualizar
        </Button>
      </div>

      {/* KPIs */}
      {kpisLoading ? (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Card key={i} className="p-4 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-20 mb-2" />
              <div className="h-8 bg-gray-200 rounded w-12" />
            </Card>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <KpiCard
            label="Sesiones 24h"
            value={kpis?.active_sessions_24h ?? 0}
            icon={<Users className="h-5 w-5 text-teal-600" />}
            accent="teal"
          />
          <KpiCard
            label="Pedidos activos"
            value={activeCount}
            sub={awaitingCount > 0 ? `⏳ ${awaitingCount} esperando cliente` : undefined}
            icon={<ShoppingCart className="h-5 w-5 text-amber-600" />}
            accent="amber"
          />
          <KpiCard
            label="Citas hoy"
            value={kpis?.appointments_today ?? 0}
            icon={<Calendar className="h-5 w-5 text-rose-600" />}
            accent="rose"
          />
          <KpiCard
            label="Puntos 30d"
            value={(kpis?.loyalty_points_30d ?? 0).toLocaleString('es-CO')}
            icon={<Star className="h-5 w-5 text-emerald-600" />}
            accent="emerald"
          />
        </div>
      )}

      {/* Main tabs: Pedidos / Citas */}
      <div className="flex gap-1 bg-gray-100 rounded-xl p-1 w-fit">
        {(['orders', 'appointments'] as const).map((t) => (
          <button
            key={t}
            onClick={() => setMainTab(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
              mainTab === t ? 'bg-white shadow text-gray-900' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t === 'orders' ? `📦 Pedidos${activeCount > 0 ? ` (${activeCount})` : ''}` : '📅 Citas'}
          </button>
        ))}
      </div>

      {/* ORDERS VIEW */}
      {mainTab === 'orders' && (
        <div className="flex flex-col gap-4">
          {/* Workflow sub-tabs */}
          <div className="flex gap-1 border-b">
            {WORKFLOW_TABS.map((t) => {
              const count = allOrders.filter((o) => {
                const ws = o.workflow_status ?? o.status;
                return t.statuses.includes(ws);
              }).length;
              return (
                <button
                  key={t.key}
                  onClick={() => setWorkflowTab(t.key as typeof workflowTab)}
                  className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${
                    workflowTab === t.key
                      ? 'border-teal-600 text-teal-700'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {t.label}
                  {count > 0 && (
                    <span className={`ml-1.5 text-xs px-1.5 py-0.5 rounded-full font-bold ${
                      workflowTab === t.key ? 'bg-teal-100 text-teal-800' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {ordersLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Card key={i} className="p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-gray-100 rounded w-2/3" />
                </Card>
              ))}
            </div>
          ) : filteredOrders.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Package className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No hay pedidos en este estado</p>
            </div>
          ) : (
            <div className="space-y-2">
              {filteredOrders.map((order) => {
                const ws = order.workflow_status ?? order.status;
                const wsInfo = WORKFLOW_STATUS[ws] ?? { label: ws, color: 'bg-gray-100 text-gray-600', emoji: '📦' };
                const isAwaiting = ws === 'awaiting_customer';
                return (
                  <Card key={order.id} className={`p-4 border transition-shadow hover:shadow-md ${isAwaiting ? 'border-amber-300 bg-amber-50/30' : 'border-gray-100'}`}>
                    <div className="flex items-center gap-3">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1 flex-wrap">
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${wsInfo.color}`}>
                            {wsInfo.emoji} {wsInfo.label}
                          </span>
                          {isAwaiting && (
                            <span className="text-xs bg-amber-200 text-amber-800 px-2 py-0.5 rounded-full font-bold animate-pulse">
                              ⏳ Requiere contacto
                            </span>
                          )}
                          {order.invoice_number && (
                            <span className="text-xs text-gray-400">🧾 {order.invoice_number}</span>
                          )}
                        </div>
                        <p className="font-semibold text-gray-900 text-sm">
                          {order.customer_name ?? 'Cliente desconocido'}
                        </p>
                        <p className="text-xs text-gray-500 mt-0.5">
                          {order.product_name} · {order.quantity} und ·{' '}
                          {formatCOP(order.unit_price)} · {formatAgo(order.created_at)}
                        </p>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => setSelectedOrderId(order.id)}
                        className="gap-1.5 shrink-0"
                      >
                        <Eye className="h-3.5 w-3.5" />
                        Ver
                      </Button>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* APPOINTMENTS VIEW */}
      {mainTab === 'appointments' && (
        <div className="flex flex-col gap-3">
          {apptLoading ? (
            <div className="space-y-3">
              {[...Array(3)].map((_, i) => (
                <Card key={i} className="p-4 animate-pulse">
                  <div className="h-4 bg-gray-200 rounded w-1/3 mb-2" />
                  <div className="h-3 bg-gray-100 rounded w-2/3" />
                </Card>
              ))}
            </div>
          ) : appointments.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <Calendar className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p className="font-medium">No hay citas registradas</p>
            </div>
          ) : (
            appointments.map((appt) => {
              const statusInfo = APPT_STATUS[appt.status] ?? { label: appt.status, color: 'bg-gray-100 text-gray-600' };
              const isToday = new Date(appt.scheduled_at).toDateString() === new Date().toDateString();
              return (
                <Card key={appt.id} className={`p-4 border ${isToday ? 'border-teal-200 bg-teal-50/30' : 'border-gray-100'}`}>
                  <div className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${statusInfo.color}`}>
                          {statusInfo.label}
                        </span>
                        {isToday && (
                          <span className="text-xs bg-teal-200 text-teal-800 px-2 py-0.5 rounded-full font-bold">
                            HOY
                          </span>
                        )}
                      </div>
                      <p className="font-semibold text-gray-900 text-sm">
                        {appt.customer_name ?? 'Cliente'} · {appt.pet_name ?? '—'}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">
                        {appt.service_type} ·{' '}
                        {new Date(appt.scheduled_at).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}
                        {' · '}{appt.duration_min} min
                        {appt.price != null && ` · ${formatCOP(appt.price)}`}
                      </p>
                      {appt.notes && (
                        <p className="text-xs text-gray-400 mt-1 line-clamp-1">{appt.notes}</p>
                      )}
                    </div>
                    <div className="flex flex-col gap-1.5 shrink-0">
                      {appt.status === 'pending' && (
                        <>
                          <Button
                            size="sm"
                            className="bg-green-600 hover:bg-green-700 text-white text-xs gap-1"
                            onClick={() => updateAppt({ id: appt.id, status: 'confirmed' })}
                            disabled={updatingAppt}
                          >
                            <CheckCircle className="h-3 w-3" /> Confirmar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 border-red-200 hover:bg-red-50 text-xs gap-1"
                            onClick={() => {
                              const reason = window.prompt('Motivo de cancelación:');
                              if (reason) updateAppt({ id: appt.id, status: 'cancelled', cancel_reason: reason });
                            }}
                            disabled={updatingAppt}
                          >
                            <XCircle className="h-3 w-3" /> Cancelar
                          </Button>
                        </>
                      )}
                      {appt.status === 'confirmed' && (
                        <>
                          <Button
                            size="sm"
                            className="bg-teal-600 hover:bg-teal-700 text-white text-xs"
                            onClick={() => updateAppt({ id: appt.id, status: 'completed' })}
                            disabled={updatingAppt}
                          >
                            ✅ Completar
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-gray-600 text-xs"
                            onClick={() => updateAppt({ id: appt.id, status: 'cancelled', cancel_reason: 'No show' })}
                            disabled={updatingAppt}
                          >
                            No asistió
                          </Button>
                        </>
                      )}
                    </div>
                  </div>
                </Card>
              );
            })
          )}
        </div>
      )}

      {/* Order detail drawer */}
      {selectedOrderId && (
        <OrderDetailDrawer
          orderId={selectedOrderId}
          onClose={() => setSelectedOrderId(null)}
          onRefreshList={manualRefresh}
        />
      )}
    </div>
  );
}
