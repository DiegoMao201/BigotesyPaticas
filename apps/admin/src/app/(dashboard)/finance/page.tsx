'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  TrendingUp, TrendingDown, DollarSign, Percent, Calendar,
} from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { finance } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';

const COLORS = ['#FF6B35', '#FF8C42', '#FFB347', '#FFC97A', '#FBD89D', '#A0AEC0'];

function defaultPeriod() {
  const t = new Date();
  const start = new Date(t.getFullYear(), t.getMonth(), 1);
  return {
    start: start.toISOString().slice(0, 10),
    end: t.toISOString().slice(0, 10),
  };
}

export default function FinancePage() {
  const [period, setPeriod] = useState(defaultPeriod());
  const { data, isLoading } = useQuery({
    queryKey: ['finance-summary', period],
    queryFn: () => finance.summary(period.start, period.end),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <TrendingUp className="w-6 h-6 text-brand-600" /> P&L y Cash Flow
          </h1>
          <p className="text-sm text-muted-foreground">Estado financiero ejecutivo del periodo</p>
        </div>
        <div className="flex items-center gap-2">
          <Calendar className="w-4 h-4 text-muted-foreground" />
          <Input type="date" value={period.start} onChange={(e) => setPeriod({ ...period, start: e.target.value })} />
          <span className="text-muted-foreground">→</span>
          <Input type="date" value={period.end} onChange={(e) => setPeriod({ ...period, end: e.target.value })} />
        </div>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-muted-foreground">Calculando…</div>
      ) : !data ? (
        <div className="text-center py-16 text-muted-foreground">Sin datos</div>
      ) : (
        <>
          {/* KPI Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <KpiCard
              label="Ingresos"
              value={formatCurrency(data.revenue)}
              icon={<TrendingUp className="w-5 h-5" />}
              tone="emerald"
            />
            <KpiCard
              label="COGS"
              value={formatCurrency(data.cogs)}
              icon={<TrendingDown className="w-5 h-5" />}
              tone="amber"
            />
            <KpiCard
              label="Margen Bruto"
              value={`${data.gross_margin_pct.toFixed(1)}%`}
              sub={formatCurrency(data.gross_profit)}
              icon={<Percent className="w-5 h-5" />}
              tone="brand"
            />
            <KpiCard
              label="Utilidad Neta"
              value={formatCurrency(data.net_profit)}
              sub={`${data.net_margin_pct.toFixed(1)}% margen`}
              icon={<DollarSign className="w-5 h-5" />}
              tone={data.net_profit >= 0 ? 'emerald' : 'red'}
            />
          </div>

          {/* P&L summary */}
          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Estado de Resultados</h2>
            <div className="space-y-2 max-w-xl">
              <PLRow label="Ingresos" value={data.revenue} positive />
              <PLRow label="− Costo de Ventas (COGS)" value={-data.cogs} />
              <PLRow label="Utilidad Bruta" value={data.gross_profit} bold positive={data.gross_profit >= 0} />
              <div className="border-t border-border my-2" />
              <PLRow label="− Gastos Operativos" value={-data.expenses_total} />
              <PLRow label="Utilidad Neta" value={data.net_profit} bold xl positive={data.net_profit >= 0} />
            </div>
          </Card>

          {/* Cashflow chart */}
          <Card className="p-6">
            <h2 className="text-lg font-bold mb-4">Flujo de Caja Diario</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={data.daily_cashflow}>
                  <defs>
                    <linearGradient id="rev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#FF6B35" stopOpacity={0.5} />
                      <stop offset="100%" stopColor="#FF6B35" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="exp" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#ef4444" stopOpacity={0.4} />
                      <stop offset="100%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                  <Tooltip
                    formatter={(v: number) => formatCurrency(v)}
                    labelClassName="text-sm font-semibold"
                  />
                  <Legend />
                  <Area type="monotone" dataKey="revenue" name="Ingresos" stroke="#FF6B35" fill="url(#rev)" strokeWidth={2} />
                  <Area type="monotone" dataKey="expenses" name="Gastos" stroke="#ef4444" fill="url(#exp)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            {/* Expenses by category */}
            <Card className="p-6">
              <h2 className="text-lg font-bold mb-4">Gastos por Categoría</h2>
              {data.expenses_by_category.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">Sin gastos en el periodo</div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={data.expenses_by_category.slice(0, 6)}
                        dataKey="total"
                        nameKey="category"
                        cx="50%"
                        cy="50%"
                        outerRadius={90}
                        label={(e: any) => e.category}
                        labelLine={false}
                      >
                        {data.expenses_by_category.slice(0, 6).map((_, i) => (
                          <Cell key={i} fill={COLORS[i % COLORS.length]} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(v: number) => formatCurrency(v)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            {/* Revenue by method */}
            <Card className="p-6">
              <h2 className="text-lg font-bold mb-4">Ingresos por Método de Pago</h2>
              {data.revenue_by_method.length === 0 ? (
                <div className="text-center py-12 text-muted-foreground">Sin ventas en el periodo</div>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data.revenue_by_method} layout="vertical">
                      <CartesianGrid stroke="#e5e7eb" strokeDasharray="3 3" />
                      <XAxis type="number" tick={{ fontSize: 11 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}k`} />
                      <YAxis type="category" dataKey="method" tick={{ fontSize: 11 }} width={100} />
                      <Tooltip formatter={(v: number) => formatCurrency(v)} />
                      <Bar dataKey="total" fill="#FF6B35" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

function KpiCard({ label, value, sub, icon, tone }: any) {
  const tones: any = {
    emerald: 'text-emerald-600 bg-emerald-500/10',
    amber: 'text-amber-600 bg-amber-500/10',
    brand: 'text-brand-600 bg-brand-500/10',
    red: 'text-red-600 bg-red-500/10',
  };
  return (
    <Card className="p-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-xs text-muted-foreground uppercase tracking-wider">{label}</div>
          <div className="text-2xl font-bold mt-1">{value}</div>
          {sub && <div className="text-xs text-muted-foreground mt-0.5">{sub}</div>}
        </div>
        <div className={`p-2 rounded-lg ${tones[tone] || tones.brand}`}>{icon}</div>
      </div>
    </Card>
  );
}

function PLRow({ label, value, bold, xl, positive }: any) {
  return (
    <div className={`flex items-center justify-between ${bold ? 'font-bold' : ''} ${xl ? 'text-lg' : 'text-sm'}`}>
      <span>{label}</span>
      <span className={positive ? 'text-emerald-600' : value < 0 ? 'text-red-600' : ''}>{formatCurrency(value)}</span>
    </div>
  );
}
