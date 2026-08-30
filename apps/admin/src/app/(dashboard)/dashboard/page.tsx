'use client';

import Link from 'next/link';
import {
  TrendingUp, TrendingDown, DollarSign, Package, ShoppingBag,
  AlertTriangle, ArrowUpRight, Clock, Boxes, Percent,
  RotateCcw, UserMinus, Archive, UserPlus, CreditCard,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, formatCurrency } from '@/lib/utils';
import { analytics, dailyGoal, type DashboardData } from '@/lib/api';

// ── KPI card ──────────────────────────────────────────────────────
interface KpiProps {
  label: string;
  value: string;
  delta?: number;
  deltaSuffix?: string;
  icon: React.ComponentType<{ className?: string }>;
  accent?: string;
  loading?: boolean;
}
function Kpi({ label, value, delta, deltaSuffix = '%', icon: Icon, accent = 'from-brand/20 to-brand/5', loading }: KpiProps) {
  const positive = (delta ?? 0) >= 0;
  return (
    <Card className="overflow-hidden relative group hover:shadow-elegant transition-shadow">
      <div className={cn('absolute inset-0 bg-gradient-to-br opacity-60', accent)} />
      <CardHeader className="pb-2 relative">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="relative">
        {loading ? (
          <div className="h-9 w-32 bg-muted/50 animate-pulse rounded-lg" />
        ) : (
          <div className="text-3xl font-display font-bold tracking-tight">{value}</div>
        )}
        {!loading && delta !== undefined && (
          <div className={cn('flex items-center gap-1 text-xs mt-2 font-medium', positive ? 'text-emerald-600' : 'text-rose-600')}>
            {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {positive ? '+' : ''}{delta!.toFixed(1)}{deltaSuffix} vs mismo período mes anterior
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// ── Card de la fila de acción ───────────────────────────────────────
function ActionCard({ label, value, sub, icon: Icon, accent, href = '/intelligence' }: {
  label: string; value: string; sub: string; icon: React.ComponentType<{ className?: string }>; accent: string; href?: string;
}) {
  return (
    <Link href={href}>
      <Card className="overflow-hidden relative group hover:shadow-elegant transition-shadow cursor-pointer h-full">
        <div className={cn('absolute inset-0 bg-gradient-to-br opacity-60', accent)} />
        <CardHeader className="pb-2 relative">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
            <Icon className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="relative">
          <div className="text-2xl font-display font-bold tracking-tight">{value}</div>
          <div className="text-xs text-muted-foreground mt-2 flex items-center gap-1 group-hover:text-brand-600 transition-colors">
            {sub} <ArrowUpRight className="h-3 w-3" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}

// ── Mini sparkline (SVG simple) ───────────────────────────────────
function Sparkline({ data }: { data: { revenue: number }[] }) {
  if (!data.length) return null;
  const maxVal = Math.max(...data.map((d) => d.revenue), 1);
  const W = 280;
  const H = 60;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - (d.revenue / maxVal) * (H - 6) - 3;
    return `${x},${y}`;
  });
  const area = `M0,${H} L${pts.join(' L')} L${W},${H} Z`;
  const line = `M${pts.join(' L')}`;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16">
      <defs>
        <linearGradient id="sparkGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#187f77" stopOpacity="0.3" />
          <stop offset="100%" stopColor="#187f77" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#sparkGrad)" />
      <path d={line} fill="none" stroke="#187f77" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-amber-100 text-amber-800',
  confirmed: 'bg-blue-100 text-blue-800',
  processing: 'bg-violet-100 text-violet-800',
  completed: 'bg-emerald-100 text-emerald-800',
  cancelled: 'bg-rose-100 text-rose-800',
};

// ── Meta diaria con semáforo (P5) ─────────────────────────────────
function DailyGoalBanner() {
  const { data, isLoading } = useQuery({
    queryKey: ['daily-goal'],
    queryFn: () => dailyGoal.get(),
    staleTime: 60_000,
    refetchInterval: 5 * 60_000,
  });
  if (isLoading || !data) {
    return <div className="h-24 rounded-xl bg-muted/30 animate-pulse" />;
  }
  const pct = Math.min(data.progress_pct, 100);
  const palette = data.status === 'logrado'
    ? { bar: 'bg-emerald-500', text: 'text-emerald-700', bg: 'from-emerald-500/10 to-emerald-500/0', label: '🎯 ¡Meta lograda!' }
    : data.status === 'en_camino'
    ? { bar: 'bg-blue-500', text: 'text-blue-700', bg: 'from-blue-500/10 to-blue-500/0', label: '🟢 En camino' }
    : { bar: 'bg-amber-500', text: 'text-amber-700', bg: 'from-amber-500/10 to-amber-500/0', label: '🟡 Vamos atrasados' };
  return (
    <Card className={cn('overflow-hidden relative bg-gradient-to-br', palette.bg)}>
      <CardContent className="p-5">
        <div className="flex items-center justify-between flex-wrap gap-3 mb-3">
          <div>
            <div className="text-xs uppercase tracking-wide text-muted-foreground font-semibold">Meta de hoy</div>
            <div className="text-2xl font-display font-bold mt-0.5">
              {formatCurrency(data.achieved)} <span className="text-base text-muted-foreground font-normal">/ {formatCurrency(data.target)}</span>
            </div>
          </div>
          <div className="text-right">
            <div className={cn('text-sm font-bold', palette.text)}>{palette.label}</div>
            <div className="text-xs text-muted-foreground">
              {data.orders_today} ventas · proyección {formatCurrency(data.projection_eod)}
            </div>
          </div>
        </div>
        <div className="h-3 rounded-full bg-muted/60 overflow-hidden">
          <div className={cn('h-full rounded-full transition-all', palette.bar)} style={{ width: `${pct}%` }} />
        </div>
        <div className="flex items-center justify-between mt-2 text-xs text-muted-foreground">
          <span>{data.progress_pct.toFixed(0)}% de la meta</span>
          {data.remaining > 0
            ? <span>Faltan {formatCurrency(data.remaining)}</span>
            : <span className="text-emerald-600 font-medium">Meta superada 🎉</span>}
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => analytics.dashboard(),
    staleTime: 60_000,
  });

  const kpis = data?.kpis;
  const actionable = data?.actionable;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1 text-sm">Vista ejecutiva — {new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })}</p>
        </div>
      </div>

      {/* Error banner */}
      {isError && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 p-4 text-sm">
          No se pudo conectar con el API. Verifica que el servicio esté en línea.
        </div>
      )}

      {/* Meta diaria */}
      <DailyGoalBanner />

      {/* Banners de alerta */}
      {(!!kpis?.low_stock_count || !!actionable?.below_cost_lines) && (
        <div className="grid gap-3 sm:grid-cols-2">
          {!!kpis?.low_stock_count && (
            <div className="flex items-center gap-2 px-4 py-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-sm font-medium">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              {kpis.low_stock_count} productos con stock bajo
            </div>
          )}
          {!!actionable?.below_cost_lines && (
            <Link
              href="/below-cost"
              className="flex items-center justify-between gap-2 px-4 py-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-sm font-medium hover:bg-rose-100 transition-colors group"
            >
              <span className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 shrink-0" />
                {actionable.below_cost_lines} venta{actionable.below_cost_lines !== 1 ? 's' : ''} por debajo del costo este mes — {formatCurrency(Math.abs(actionable.below_cost_loss))} perdidos
              </span>
              <ArrowUpRight className="h-4 w-4 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
            </Link>
          )}
        </div>
      )}

      {/* KPIs principales — MTD vs mismo corte del mes anterior */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <Kpi label="Ingresos MTD" value={formatCurrency(kpis?.revenue_month ?? 0)} delta={kpis?.revenue_delta_pct} icon={DollarSign} accent="from-emerald-500/20 to-emerald-500/5" loading={isLoading} />
        <Kpi label="Margen bruto MTD" value={`${(actionable?.gross_margin_pct ?? 0).toFixed(1)}%`} delta={actionable?.gross_margin_delta_pts} deltaSuffix=" pts" icon={Percent} accent="from-teal-500/20 to-teal-500/5" loading={isLoading} />
        <Kpi label="Pedidos MTD" value={String(kpis?.orders_month ?? 0)} delta={kpis?.orders_delta_pct} icon={ShoppingBag} accent="from-blue-500/20 to-blue-500/5" loading={isLoading} />
        <Kpi label="Ticket promedio" value={formatCurrency(kpis?.avg_ticket ?? 0)} icon={Package} accent="from-violet-500/20 to-violet-500/5" loading={isLoading} />
      </div>

      {/* Fila de acción — oportunidades reales */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-5">
        <ActionCard
          label="Bold te debe"
          value={formatCurrency(actionable?.bold_pending_amount ?? 0)}
          sub={`Últimos ${actionable?.bold_pending_days ?? 2} días · ver detalle`}
          icon={CreditCard}
          accent="from-indigo-500/20 to-indigo-500/5"
          href="/analytics"
        />
        <ActionCard
          label="Oportunidad de recompra"
          value={String(actionable?.repurchase_due ?? 0)}
          sub={`${formatCurrency(actionable?.repurchase_revenue_opportunity ?? 0)} en juego`}
          icon={RotateCcw}
          accent="from-blue-500/20 to-blue-500/5"
        />
        <ActionCard
          label="Clientes en riesgo"
          value={String(actionable?.at_risk_count ?? 0)}
          sub={`${formatCurrency(actionable?.at_risk_value ?? 0)} en riesgo`}
          icon={UserMinus}
          accent="from-rose-500/20 to-rose-500/5"
        />
        <ActionCard
          label="Capital atrapado"
          value={formatCurrency(actionable?.trapped_capital ?? 0)}
          sub={`${actionable?.dead_stock_count ?? 0} SKUs sin rotar`}
          icon={Archive}
          accent="from-amber-500/20 to-amber-500/5"
        />
        <ActionCard
          label="Clientes nuevos"
          value={String(actionable?.new_customers_month ?? 0)}
          sub={actionable && actionable.new_customers_delta_pct !== 0
            ? `${actionable.new_customers_delta_pct > 0 ? '+' : ''}${actionable.new_customers_delta_pct.toFixed(1)}% vs mes anterior`
            : 'Ver detalle'}
          icon={UserPlus}
          accent="from-emerald-500/20 to-emerald-500/5"
        />
      </div>

      {/* Row 3: sparkline + top productos */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Tendencia 30 días */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Ventas — 30 días</CardTitle>
              <TrendingUp className="h-4 w-4 text-brand-500" />
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="h-16 bg-muted/30 animate-pulse rounded" />
            ) : (data?.daily_sales?.length ?? 0) > 0 ? (
              <>
                <Sparkline data={data!.daily_sales} />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>{data!.daily_sales[0]?.date}</span>
                  <span>{data!.daily_sales[data!.daily_sales.length - 1]?.date}</span>
                </div>
              </>
            ) : (
              <div className="h-16 flex items-center justify-center text-muted-foreground text-sm">Sin ventas registradas este período</div>
            )}
          </CardContent>
        </Card>

        {/* Top productos */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base">Top productos — este mes</CardTitle>
              <Boxes className="h-4 w-4 text-brand-500" />
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="space-y-2">
                {[...Array(5)].map((_, i) => <div key={i} className="h-8 bg-muted/30 animate-pulse rounded" />)}
              </div>
            ) : (data?.top_products?.length ?? 0) > 0 ? (
              <div className="space-y-2">
                {data!.top_products.map((p, i) => (
                  <div key={p.product_id} className="flex items-center justify-between py-1.5 border-b border-border/40 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="w-5 text-xs font-bold text-muted-foreground">{i + 1}</span>
                      <div>
                        <div className="text-sm font-medium leading-tight">{p.name}</div>
                        <div className="text-xs text-muted-foreground">{p.units_sold} uds</div>
                      </div>
                    </div>
                    <div className="text-sm font-semibold text-brand-700">{formatCurrency(p.revenue)}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="h-16 flex items-center justify-center text-muted-foreground text-sm">Sin datos de ventas este mes</div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Órdenes recientes */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base">Órdenes recientes</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => <div key={i} className="h-10 bg-muted/30 animate-pulse rounded" />)}
            </div>
          ) : (data?.recent_orders?.length ?? 0) > 0 ? (
            <div className="divide-y divide-border/40">
              {data!.recent_orders.map((o) => (
                <div key={o.id} className="flex items-center justify-between py-2.5">
                  <div className="flex items-center gap-3">
                    <span className="font-mono text-sm font-semibold text-brand-700">#{o.order_number}</span>
                    <span className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide', STATUS_COLORS[o.status] ?? 'bg-muted text-muted-foreground')}>
                      {o.status}
                    </span>
                    <span className="text-xs text-muted-foreground hidden sm:inline">{o.channel}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-semibold">{formatCurrency(o.grand_total)}</span>
                    <span className="text-xs text-muted-foreground">{new Date(o.occurred_at).toLocaleDateString('es-CO')}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-8 text-center text-muted-foreground text-sm">Aún no hay órdenes registradas</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
