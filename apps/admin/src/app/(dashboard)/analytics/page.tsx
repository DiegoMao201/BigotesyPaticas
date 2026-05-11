'use client';

import { useQuery } from '@tanstack/react-query';
import {
  ResponsiveContainer, LineChart, Line, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, Legend,
} from 'recharts';
import { BarChart3, TrendingUp, ShoppingCart, Users, Package, Sparkles } from 'lucide-react';
import { analytics } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

export default function AnalyticsPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: () => analytics.dashboard(),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <BarChart3 className="w-6 h-6 text-brand-600" /> Analítica Ejecutiva
        </h1>
        <p className="text-sm text-muted-foreground">KPIs, ventas, productos top y tendencias</p>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Cargando…</div>
      ) : !data ? (
        <div className="text-center py-16 text-muted-foreground">Sin datos</div>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
            <Kpi label="Ventas mes" value={formatCurrency(data.kpis.revenue_month)} delta={data.kpis.revenue_delta_pct} icon={<TrendingUp className="w-5 h-5" />} />
            <Kpi label="Órdenes mes" value={data.kpis.orders_month.toLocaleString()} delta={data.kpis.orders_delta_pct} icon={<ShoppingCart className="w-5 h-5" />} />
            <Kpi label="Ticket promedio" value={formatCurrency(data.kpis.avg_ticket)} icon={<Sparkles className="w-5 h-5" />} />
            <Kpi label="Productos activos" value={data.kpis.products_active.toLocaleString()} icon={<Package className="w-5 h-5" />} />
            <Kpi label="Clientes" value={data.kpis.customers_total.toLocaleString()} icon={<Users className="w-5 h-5" />} />
          </div>

          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Ventas Diarias (últimos 30 días)</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.daily_sales}>
                  <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v: number) => formatCurrency(v)} />
                  <Legend />
                  <Line type="monotone" dataKey="revenue" name="Ingresos" stroke="#FF6B35" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="orders" name="Órdenes" stroke="#3b82f6" strokeWidth={2} dot={false} yAxisId="right" />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <Card className="p-6">
              <h2 className="text-lg font-bold mb-4">Top 5 Productos del Mes</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={data.top_products} layout="vertical">
                    <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                    <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                    <YAxis type="category" dataKey="name" tick={{ fontSize: 10 }} width={140} />
                    <Tooltip formatter={(v: number) => formatCurrency(v)} />
                    <Bar dataKey="revenue" fill="#FF6B35" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="p-6">
              <h2 className="text-lg font-bold mb-4">Órdenes Recientes</h2>
              <div className="space-y-2">
                {data.recent_orders.map((o: any) => (
                  <div key={o.id} className="flex items-center justify-between p-2 rounded-md hover:bg-muted/30">
                    <div>
                      <div className="font-mono text-xs">{o.order_number}</div>
                      <div className="text-xs text-muted-foreground">{o.channel} · {o.payment_status}</div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold">{formatCurrency(o.grand_total)}</div>
                      <Badge variant={o.status === 'cancelled' ? 'danger' : 'success'}>{o.status}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function Kpi({ label, value, delta, icon }: { label: string; value: string; delta?: number; icon: React.ReactNode }) {
  return (
    <Card className="p-4">
      <div className="flex items-center justify-between">
        <div className="text-xs text-muted-foreground uppercase tracking-wider">{label}</div>
        <div className="text-brand-600">{icon}</div>
      </div>
      <div className="text-2xl font-bold mt-1">{value}</div>
      {delta !== undefined && (
        <div className={`text-xs mt-0.5 ${delta >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
          {delta >= 0 ? '+' : ''}{delta}% vs mes anterior
        </div>
      )}
    </Card>
  );
}
