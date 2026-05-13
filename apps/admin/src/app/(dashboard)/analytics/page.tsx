'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend, PieChart, Pie, Cell, AreaChart, Area,
  ComposedChart,
} from 'recharts';
import {
  BarChart3, TrendingUp, ShoppingCart, Users, Package,
  Sparkles, DollarSign, Target, ArrowUp, ArrowDown, RefreshCw,
  Calendar, Award, Zap, Activity,
} from 'lucide-react';
import { analyticsBI, type BiFull, type SalesPeriodComparison } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const BRAND_COLORS = ['#FF6B35', '#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16'];

const CHANNEL_LABELS: Record<string, string> = {
  POS_STREAMLIT: '🏪 POS antiguo',
  POS_NEW: '🏪 POS nuevo',
  POS_LEGACY: '🏪 POS legado',
  STORE_WEB: '🌐 E-commerce',
  STORE_LEGACY: '📦 Tienda legado',
  ADMIN_MANUAL: '⚙️ Manual',
  WHATSAPP: '💬 WhatsApp',
};

function Delta({ value, suffix = '%' }: { value: number; suffix?: string }) {
  const pos = value >= 0;
  return (
    <span className={`flex items-center gap-0.5 text-xs font-semibold ${pos ? 'text-emerald-600' : 'text-rose-600'}`}>
      {pos ? <ArrowUp className="w-3 h-3" /> : <ArrowDown className="w-3 h-3" />}
      {Math.abs(value).toFixed(1)}{suffix}
    </span>
  );
}

function KpiCard({ label, value, delta, icon, sub, accent = false }: {
  label: string; value: string; delta?: number; icon: React.ReactNode; sub?: string; accent?: boolean;
}) {
  return (
    <Card className={`p-4 ${accent ? 'bg-brand-500 text-white' : ''}`}>
      <div className="flex items-center justify-between mb-2">
        <span className={`text-xs font-semibold uppercase tracking-wide ${accent ? 'text-white/80' : 'text-muted-foreground'}`}>{label}</span>
        <span className={accent ? 'text-white/80' : 'text-muted-foreground'}>{icon}</span>
      </div>
      <div className={`text-2xl font-bold font-display ${accent ? 'text-white' : ''}`}>{value}</div>
      <div className="flex items-center gap-2 mt-1">
        {delta !== undefined && <Delta value={delta} />}
        {sub && <span className={`text-xs ${accent ? 'text-white/70' : 'text-muted-foreground'}`}>{sub}</span>}
      </div>
    </Card>
  );
}

type Tab = 'resumen' | 'ventas' | 'clientes' | 'productos' | 'pnl';

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>('resumen');
  const [days, setDays] = useState(90);
  const qc = useQuery({ queryKey: ['bi-full', days], queryFn: () => analyticsBI.full(days), staleTime: 2 * 60_000 });
  const comparison = useQuery({ queryKey: ['bi-comparison', 30], queryFn: () => analyticsBI.comparison(30), staleTime: 2 * 60_000 });

  const data = qc.data;
  const isLoading = qc.isLoading;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-brand-600" /> Analítica Ejecutiva BI
          </h1>
          <p className="text-sm text-muted-foreground">Panel completo — ventas, margen, clientes, P&amp;L</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={days}
            onChange={(e) => setDays(Number(e.target.value))}
            className="border rounded px-3 py-1.5 text-sm bg-background"
          >
            <option value={30}>Últimos 30 días</option>
            <option value={60}>Últimos 60 días</option>
            <option value={90}>Últimos 90 días</option>
            <option value={180}>Últimos 6 meses</option>
            <option value={365}>Último año</option>
          </select>
          <Button variant="outline" size="sm" onClick={() => qc.refetch()}>
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {([
          { id: 'resumen', label: 'Resumen', icon: Activity },
          { id: 'ventas', label: 'Ventas', icon: TrendingUp },
          { id: 'clientes', label: 'Clientes', icon: Users },
          { id: 'productos', label: 'Productos', icon: Package },
          { id: 'pnl', label: 'P&L', icon: DollarSign },
        ] as { id: Tab; label: string; icon: React.FC<{ className?: string }> }[]).map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors flex items-center gap-2 whitespace-nowrap
              ${tab === t.id ? 'border-brand-500 text-brand-600' : 'border-transparent text-muted-foreground hover:text-foreground'}`}
          >
            <t.icon className="w-4 h-4" /> {t.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="flex items-center justify-center py-24">
          <div className="text-center space-y-2">
            <Sparkles className="w-8 h-8 animate-spin text-brand-500 mx-auto" />
            <p className="text-muted-foreground">Calculando métricas BI…</p>
          </div>
        </div>
      )}

      {qc.isError && (
        <Card className="p-8 text-center text-rose-600">
          Error cargando datos: {String(qc.error)}
        </Card>
      )}

      {data && tab === 'resumen' && <ResumenTab data={data} comparison={comparison.data} />}
      {data && tab === 'ventas' && <VentasTab data={data} />}
      {data && tab === 'clientes' && <ClientesTab data={data} />}
      {data && tab === 'productos' && <ProductosTab data={data} />}
      {data && tab === 'pnl' && <PnlTab data={data} />}
    </div>
  );
}

// ─── RESUMEN ────────────────────────────────────────────────────────────────

function ResumenTab({ data, comparison }: { data: BiFull; comparison?: SalesPeriodComparison }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          label="Ingresos"
          value={formatCurrency(data.revenue_total)}
          delta={comparison?.delta_pct}
          icon={<DollarSign className="w-5 h-5" />}
          sub="vs período anterior"
          accent
        />
        <KpiCard
          label="Órdenes"
          value={data.orders_total.toLocaleString('es-CO')}
          delta={comparison ? ((comparison.current_orders - comparison.prev_orders) / Math.max(comparison.prev_orders, 1)) * 100 : undefined}
          icon={<ShoppingCart className="w-5 h-5" />}
        />
        <KpiCard
          label="Ticket promedio"
          value={formatCurrency(data.avg_ticket)}
          icon={<Target className="w-5 h-5" />}
        />
        <KpiCard
          label="Margen bruto"
          value={`${data.gross_margin_pct.toFixed(1)}%`}
          icon={<TrendingUp className="w-5 h-5" />}
          sub={`COGS: ${formatCurrency(data.cogs)}`}
        />
      </div>

      {data.monthly_trend.length > 0 && (
        <Card className="p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Calendar className="w-5 h-5 text-brand-500" /> Tendencia Mensual — Ingresos
          </h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={data.monthly_trend}>
                <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                <XAxis dataKey="year_month" tick={{ fontSize: 11 }} />
                <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                <Tooltip
                  formatter={(v: number, name: string) => [
                    name === 'Ingresos' ? formatCurrency(v) : v.toLocaleString('es-CO'),
                    name,
                  ]}
                />
                <Legend />
                <Area yAxisId="left" type="monotone" dataKey="revenue" name="Ingresos" fill="#FF6B35" fillOpacity={0.15} stroke="#FF6B35" strokeWidth={2} />
                <Bar yAxisId="right" dataKey="orders" name="Órdenes" fill="#3b82f6" opacity={0.7} radius={[4, 4, 0, 0]} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card className="p-6">
          <h2 className="text-base font-bold mb-4 flex items-center gap-2">
            <Zap className="w-4 h-4 text-brand-500" /> Por Canal de Venta
          </h2>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.by_channel} layout="vertical">
                <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
                <YAxis type="category" dataKey="channel" tick={{ fontSize: 9 }} width={100}
                  tickFormatter={(v: string) => CHANNEL_LABELS[v] ?? v} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="revenue" name="Ingresos" fill="#FF6B35" radius={[0, 6, 6, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-base font-bold mb-4 flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-brand-500" /> Por Método de Pago
          </h2>
          <div className="h-56 flex items-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data.by_method}
                  dataKey="revenue"
                  nameKey="method"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ method, pct }: { method: string; pct: number }) => `${method}: ${pct}%`}
                  labelLine={false}
                >
                  {data.by_method.map((_, i) => (
                    <Cell key={i} fill={BRAND_COLORS[i % BRAND_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      {data.heatmap.length > 0 && (
        <Card className="p-6">
          <h2 className="text-base font-bold mb-4 flex items-center gap-2">
            <Activity className="w-4 h-4 text-brand-500" /> Mapa de Calor — Órdenes por Día y Hora
          </h2>
          <HeatmapChart cells={data.heatmap} />
        </Card>
      )}
    </div>
  );
}

function HeatmapChart({ cells }: { cells: BiFull['heatmap'] }) {
  const DAY_LABELS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
  const hours = Array.from({ length: 24 }, (_, i) => i);
  const lookup = new Map<string, number>();
  let maxVal = 0;
  for (const c of cells) {
    lookup.set(`${c.weekday}-${c.hour}`, c.orders);
    if (c.orders > maxVal) maxVal = c.orders;
  }
  return (
    <div className="overflow-x-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="w-10 text-right pr-2 text-muted-foreground font-normal">Hora</th>
            {DAY_LABELS.map((d) => (
              <th key={d} className="w-8 text-center py-1 text-muted-foreground font-normal">{d}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {hours.map((h) => (
            <tr key={h}>
              <td className="text-right pr-2 text-muted-foreground py-0.5">{h}h</td>
              {Array.from({ length: 7 }, (_, wd) => {
                const v = lookup.get(`${wd}-${h}`) ?? 0;
                const intensity = maxVal > 0 ? v / maxVal : 0;
                const bg = intensity === 0 ? 'bg-gray-50' : intensity < 0.25 ? 'bg-orange-100' : intensity < 0.5 ? 'bg-orange-300' : intensity < 0.75 ? 'bg-orange-500' : 'bg-orange-700';
                const text = intensity > 0.6 ? 'text-white' : 'text-gray-700';
                return (
                  <td key={wd} className={`w-8 h-6 text-center rounded-sm m-px ${bg} ${text}`} title={`${DAY_LABELS[wd]} ${h}h: ${v} órdenes`}>
                    {v > 0 ? v : ''}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ─── VENTAS ──────────────────────────────────────────────────────────────────

function VentasTab({ data }: { data: BiFull }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="p-4 bg-emerald-50 border-emerald-200">
          <p className="text-xs text-emerald-700 font-semibold uppercase">Ingresos totales</p>
          <p className="text-2xl font-bold text-emerald-800">{formatCurrency(data.revenue_total)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground uppercase">Órdenes</p>
          <p className="text-2xl font-bold">{data.orders_total.toLocaleString('es-CO')}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground uppercase">Ticket prom.</p>
          <p className="text-2xl font-bold">{formatCurrency(data.avg_ticket)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground uppercase">Margen bruto</p>
          <p className={`text-2xl font-bold ${data.gross_margin_pct >= 30 ? 'text-emerald-600' : data.gross_margin_pct >= 15 ? 'text-amber-600' : 'text-rose-600'}`}>
            {data.gross_margin_pct.toFixed(1)}%
          </p>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Desglose por Canal</h2>
        <div className="space-y-3">
          {data.by_channel.map((c, i) => (
            <div key={c.channel} className="flex items-center gap-3">
              <span className="w-28 text-sm truncate">{CHANNEL_LABELS[c.channel] ?? c.channel}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                <div className="h-full rounded-full flex items-center justify-end pr-2" style={{ width: `${c.pct}%`, backgroundColor: BRAND_COLORS[i % BRAND_COLORS.length] }}>
                  <span className="text-white text-xs font-semibold">{c.pct}%</span>
                </div>
              </div>
              <span className="w-28 text-right text-sm font-semibold">{formatCurrency(c.revenue)}</span>
              <span className="w-12 text-right text-xs text-muted-foreground">{c.orders}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Desglose por Método de Pago</h2>
        <div className="space-y-3">
          {data.by_method.map((m, i) => (
            <div key={m.method} className="flex items-center gap-3">
              <span className="w-28 text-sm truncate">{m.method}</span>
              <div className="flex-1 bg-gray-100 rounded-full h-5 overflow-hidden">
                <div className="h-full rounded-full flex items-center justify-end pr-2" style={{ width: `${m.pct}%`, backgroundColor: BRAND_COLORS[i % BRAND_COLORS.length] }}>
                  <span className="text-white text-xs font-semibold">{m.pct}%</span>
                </div>
              </div>
              <span className="w-28 text-right text-sm font-semibold">{formatCurrency(m.revenue)}</span>
              <span className="w-12 text-right text-xs text-muted-foreground">{m.orders}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Evolución Mensual (12 meses)</h2>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data.monthly_trend}>
              <defs>
                <linearGradient id="grad-rev" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#FF6B35" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#FF6B35" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
              <XAxis dataKey="year_month" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1_000_000).toFixed(1)}M`} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Area type="monotone" dataKey="revenue" name="Ingresos" stroke="#FF6B35" fill="url(#grad-rev)" strokeWidth={2.5} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

// ─── CLIENTES ───────────────────────────────────────────────────────────────

function ClientesTab({ data }: { data: BiFull }) {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card className="p-4">
          <p className="text-xs text-muted-foreground uppercase">Clientes únicos (período)</p>
          <p className="text-2xl font-bold">{data.top_customers.length >= 15 ? '15+' : data.top_customers.length}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs text-muted-foreground uppercase">Top cliente</p>
          <p className="text-xl font-bold truncate">{data.top_customers[0]?.name ?? '—'}</p>
          <p className="text-sm text-muted-foreground">{data.top_customers[0] ? formatCurrency(data.top_customers[0].revenue) : ''}</p>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4 flex items-center gap-2">
          <Award className="w-4 h-4 text-brand-500" /> Top 15 Clientes por Revenue
        </h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground uppercase border-b">
              <tr>
                <th className="text-left pb-2">#</th>
                <th className="text-left pb-2">Cliente</th>
                <th className="text-right pb-2">Órdenes</th>
                <th className="text-right pb-2">Revenue</th>
                <th className="text-right pb-2">Ticket prom.</th>
                <th className="text-right pb-2">Última compra</th>
              </tr>
            </thead>
            <tbody>
              {data.top_customers.map((c, i) => (
                <tr key={i} className="border-b border-muted/30 hover:bg-muted/10">
                  <td className="py-2 pr-3">
                    <span className={`w-6 h-6 rounded-full inline-flex items-center justify-center text-xs font-bold
                      ${i === 0 ? 'bg-yellow-400 text-yellow-900' : i === 1 ? 'bg-gray-300 text-gray-700' : i === 2 ? 'bg-orange-400 text-orange-900' : 'bg-muted text-muted-foreground'}`}>
                      {i + 1}
                    </span>
                  </td>
                  <td className="py-2 font-medium">{c.name}</td>
                  <td className="py-2 text-right">{c.orders}</td>
                  <td className="py-2 text-right font-semibold text-emerald-700">{formatCurrency(c.revenue)}</td>
                  <td className="py-2 text-right text-muted-foreground">{formatCurrency(c.revenue / c.orders)}</td>
                  <td className="py-2 text-right text-muted-foreground text-xs">
                    {c.last_purchase ? new Date(c.last_purchase).toLocaleDateString('es-CO') : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Revenue Top 10 Clientes</h2>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.top_customers.slice(0, 10)} layout="vertical">
              <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
              <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
              <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={120} />
              <Tooltip formatter={(v: number) => formatCurrency(v)} />
              <Bar dataKey="revenue" name="Revenue" fill="#FF6B35" radius={[0, 6, 6, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
    </div>
  );
}

// ─── PRODUCTOS ───────────────────────────────────────────────────────────────

function ProductosTab({ data }: { data: BiFull }) {
  return (
    <div className="space-y-5">
      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Ventas por Categoría</h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data.by_category} dataKey="revenue" nameKey="category" cx="50%" cy="50%" outerRadius={100}
                  label={({ pct }: { pct: number }) => `${pct}%`}>
                  {data.by_category.map((_, i) => <Cell key={i} fill={BRAND_COLORS[i % BRAND_COLORS.length]} />)}
                </Pie>
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Legend />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2">
            {data.by_category.map((c, i) => (
              <div key={c.category} className="flex items-center gap-3">
                <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ backgroundColor: BRAND_COLORS[i % BRAND_COLORS.length] }} />
                <span className="flex-1 text-sm truncate">{c.category}</span>
                <span className="text-sm font-semibold">{formatCurrency(c.revenue)}</span>
                <span className="text-xs text-muted-foreground w-12 text-right">{c.pct}%</span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-4">Detalle por Categoría</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-xs text-muted-foreground uppercase border-b">
              <tr>
                <th className="text-left pb-2">Categoría</th>
                <th className="text-right pb-2">Revenue</th>
                <th className="text-right pb-2">Unidades</th>
                <th className="text-right pb-2">% Total</th>
              </tr>
            </thead>
            <tbody>
              {data.by_category.map((c) => (
                <tr key={c.category} className="border-b border-muted/30 hover:bg-muted/10">
                  <td className="py-2 font-medium">{c.category}</td>
                  <td className="py-2 text-right text-emerald-700 font-semibold">{formatCurrency(c.revenue)}</td>
                  <td className="py-2 text-right">{c.units.toLocaleString('es-CO')}</td>
                  <td className="py-2 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <div className="w-16 bg-gray-100 rounded-full h-2 overflow-hidden">
                        <div className="h-full bg-brand-500 rounded-full" style={{ width: `${c.pct}%` }} />
                      </div>
                      <span>{c.pct}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

// ─── P&L ────────────────────────────────────────────────────────────────────

function PnlTab({ data }: { data: BiFull }) {
  const margin_gross = data.revenue > 0 ? ((data.gross_profit / data.revenue) * 100).toFixed(1) : '0';
  const margin_net = data.revenue > 0 ? ((data.net_profit / data.revenue) * 100).toFixed(1) : '0';

  const pnl_rows = [
    { label: '+ Ingresos brutos', value: data.revenue, className: 'text-emerald-700 font-bold text-base' },
    { label: '— COGS (costo mercancía)', value: data.cogs, neg: true, className: 'text-rose-600' },
    { label: '= Utilidad bruta', value: data.gross_profit, className: `font-bold ${data.gross_profit >= 0 ? 'text-emerald-700' : 'text-rose-600'}`, sub: `Margen: ${margin_gross}%`, divider: true },
    { label: '— Gastos operativos', value: data.expenses_total, neg: true, className: 'text-rose-600' },
    { label: '= Utilidad neta', value: data.net_profit, className: `font-bold text-base ${data.net_profit >= 0 ? 'text-emerald-700' : 'text-rose-600'}`, sub: `Margen neto: ${margin_net}%`, divider: true },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className={`p-4 ${data.net_profit >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-rose-50 border-rose-200'}`}>
          <p className="text-xs font-semibold uppercase text-muted-foreground">Utilidad neta</p>
          <p className={`text-2xl font-bold ${data.net_profit >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}>{formatCurrency(data.net_profit)}</p>
          <p className="text-xs text-muted-foreground mt-1">Margen: {margin_net}%</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Utilidad bruta</p>
          <p className="text-2xl font-bold text-emerald-700">{formatCurrency(data.gross_profit)}</p>
          <p className="text-xs text-muted-foreground mt-1">Margen: {margin_gross}%</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase text-muted-foreground">Gastos totales</p>
          <p className="text-2xl font-bold text-rose-600">{formatCurrency(data.expenses_total)}</p>
        </Card>
        <Card className="p-4">
          <p className="text-xs font-semibold uppercase text-muted-foreground">COGS</p>
          <p className="text-2xl font-bold text-rose-600">{formatCurrency(data.cogs)}</p>
        </Card>
      </div>

      <Card className="p-6">
        <h2 className="text-base font-bold mb-6 flex items-center gap-2">
          <DollarSign className="w-5 h-5 text-brand-500" /> Estado de Resultados
        </h2>
        <div className="space-y-3 max-w-lg">
          {pnl_rows.map((row, i) => (
            <div key={i} className={`flex items-center justify-between py-2 ${row.divider ? 'border-t-2 border-b border-gray-300' : 'border-b border-dashed border-gray-200'}`}>
              <span className={`text-sm ${row.className}`}>
                {row.label}
                {row.sub && <span className="ml-2 text-xs text-muted-foreground font-normal">({row.sub})</span>}
              </span>
              <span className={`font-mono text-sm ${row.className}`}>
                {row.neg && row.value > 0 ? '- ' : ''}{formatCurrency(row.value)}
              </span>
            </div>
          ))}
        </div>
      </Card>

      {data.expenses_by_category.length > 0 && (
        <Card className="p-6">
          <h2 className="text-base font-bold mb-4">Gastos por Categoría</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={data.expenses_by_category} layout="vertical">
                  <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <YAxis type="category" dataKey="category" tick={{ fontSize: 10 }} width={120} />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Bar dataKey="total" name="Gasto" fill="#ef4444" radius={[0, 6, 6, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="space-y-2">
              {data.expenses_by_category.slice(0, 10).map((e) => (
                <div key={e.category} className="flex items-center justify-between text-sm">
                  <span className="truncate max-w-[160px]">{e.category}</span>
                  <span className="font-semibold text-rose-600">{formatCurrency(e.total)}</span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      )}
    </div>
  );
}

