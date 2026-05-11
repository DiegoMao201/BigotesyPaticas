'use client';

import {
  TrendingUp, TrendingDown, DollarSign, Package, ShoppingBag,
  Users, AlertTriangle, ArrowUpRight, Clock, Boxes,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, formatCurrency } from '@/lib/utils';
import { analytics, type DashboardData } from '@/lib/api';

// ── KPI card ──────────────────────────────────────────────────────
interface KpiProps {
  label: string;
  value: string;
  delta?: number;
  icon: React.ComponentType<{ className?: string }>;
  accent?: string;
  loading?: boolean;
}
function Kpi({ label, value, delta, icon: Icon, accent = 'from-brand/20 to-brand/5', loading }: KpiProps) {
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
            {Math.abs(delta).toFixed(1)}% vs mes anterior
          </div>
        )}
      </CardContent>
    </Card>
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

export default function DashboardPage() {
  const { data, isLoading, isError } = useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: () => analytics.dashboard(),
    staleTime: 60_000,
  });

  const kpis = data?.kpis;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-display font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground mt-1 text-sm">Vista ejecutiva — {new Date().toLocaleDateString('es-CO', { month: 'long', year: 'numeric' })}</p>
        </div>
        {kpis?.low_stock_count ? (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-sm font-medium">
            <AlertTriangle className="h-4 w-4" />
            {kpis.low_stock_count} productos con stock bajo
          </div>
        ) : null}
      </div>

      {/* Error banner */}
      {isError && (
        <div className="rounded-lg bg-rose-50 border border-rose-200 text-rose-700 p-4 text-sm">
          No se pudo conectar con el API. Verifica que el servicio esté en línea.
        </div>
      )}

      {/* KPIs */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-4">
        <Kpi label="Ingresos del mes" value={formatCurrency(kpis?.revenue_month ?? 0)} delta={kpis?.revenue_delta_pct} icon={DollarSign} accent="from-emerald-500/20 to-emerald-500/5" loading={isLoading} />
        <Kpi label="Pedidos" value={String(kpis?.orders_month ?? 0)} delta={kpis?.orders_delta_pct} icon={ShoppingBag} accent="from-blue-500/20 to-blue-500/5" loading={isLoading} />
        <Kpi label="Productos activos" value={String(kpis?.products_active ?? 0)} icon={Package} accent="from-brand/20 to-brand/5" loading={isLoading} />
        <Kpi label="Clientes" value={String(kpis?.customers_total ?? 0)} icon={Users} accent="from-violet-500/20 to-violet-500/5" loading={isLoading} />
      </div>

      {/* Row 2: stats secundarias */}
      <div className="grid gap-4 grid-cols-2 lg:grid-cols-3">
        <Card className="glass-brand">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-2">Ticket promedio</div>
            {isLoading ? <div className="h-7 w-24 bg-muted/50 animate-pulse rounded" /> : <div className="text-2xl font-display font-bold">{formatCurrency(kpis?.avg_ticket ?? 0)}</div>}
          </CardContent>
        </Card>
        <Card className="glass-brand">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-2">Rev. mes anterior</div>
            {isLoading ? <div className="h-7 w-24 bg-muted/50 animate-pulse rounded" /> : <div className="text-2xl font-display font-bold">{formatCurrency(kpis?.revenue_prev_month ?? 0)}</div>}
          </CardContent>
        </Card>
        <Card className="glass-brand">
          <CardContent className="p-5">
            <div className="text-xs text-muted-foreground font-medium uppercase tracking-wide mb-2">Stock bajo</div>
            <div className={cn('text-2xl font-display font-bold', (kpis?.low_stock_count ?? 0) > 0 ? 'text-amber-600' : 'text-emerald-600')}>
              {isLoading ? <div className="h-7 w-12 bg-muted/50 animate-pulse rounded" /> : `${kpis?.low_stock_count ?? 0} SKUs`}
            </div>
          </CardContent>
        </Card>
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
