'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Truck, RefreshCw, PackageX, MessageCircle,
  TrendingDown, ShoppingCart, CalendarClock, Boxes,
} from 'lucide-react';
import { intelligence, type StockoutForecastData, type ReplenishmentData } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const LEVEL_BADGE: Record<string, { label: string; cls: string }> = {
  agotado: { label: 'Agotado', cls: 'bg-rose-100 text-rose-800' },
  critico: { label: 'Crítico', cls: 'bg-orange-100 text-orange-800' },
  bajo: { label: 'Bajo', cls: 'bg-amber-100 text-amber-800' },
  ok: { label: 'OK', cls: 'bg-emerald-100 text-emerald-800' },
};

function KpiCard({ label, value, icon, sub, accent }: {
  label: string; value: string; icon: React.ReactNode; sub?: string; accent?: 'rose' | 'amber' | 'brand' | 'emerald';
}) {
  const cls =
    accent === 'rose' ? 'border-rose-200 bg-rose-50/50'
    : accent === 'amber' ? 'border-amber-200 bg-amber-50/50'
    : accent === 'emerald' ? 'border-emerald-200 bg-emerald-50/50'
    : 'border-brand/20 bg-brand/5';
  return (
    <Card className={`p-4 border ${cls}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
        <span className="text-muted-foreground">{icon}</span>
      </div>
      <div className="text-2xl font-bold font-display">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </Card>
  );
}

type Tab = 'forecast' | 'ordenes';

export default function ReplenishmentPage() {
  const [tab, setTab] = useState<Tab>('forecast');
  const [targetDays, setTargetDays] = useState(15);

  const forecast = useQuery({
    queryKey: ['stockout-forecast', targetDays],
    queryFn: () => intelligence.stockoutForecast({ target_days: targetDays, horizon_days: 21 }),
    staleTime: 5 * 60_000,
  });
  const replenish = useQuery({
    queryKey: ['replenishment', targetDays],
    queryFn: () => intelligence.replenishment({ target_days: targetDays, coverage_threshold_days: targetDays }),
    staleTime: 5 * 60_000,
  });

  const fData: StockoutForecastData | undefined = forecast.data;
  const rData: ReplenishmentData | undefined = replenish.data;
  const isFetching = forecast.isFetching || replenish.isFetching;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Truck className="w-6 h-6 text-brand-600" /> Reabastecimiento Inteligente
          </h1>
          <p className="text-sm text-muted-foreground">
            Predice qué se va a agotar y genera el pedido por proveedor, listo para enviar por WhatsApp.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={targetDays}
            onChange={(e) => setTargetDays(Number(e.target.value))}
            className="border rounded px-3 py-1.5 text-sm bg-background"
          >
            <option value={8}>Cubrir 8 días</option>
            <option value={15}>Cubrir 15 días</option>
            <option value={30}>Cubrir 30 días</option>
          </select>
          <Button variant="outline" size="sm" onClick={() => { forecast.refetch(); replenish.refetch(); }} disabled={isFetching}>
            <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="En riesgo de quiebre"
          value={fData ? String(fData.summary.at_risk) : '—'}
          icon={<TrendingDown className="w-4 h-4" />}
          sub={fData ? `Próximos 21 días` : undefined}
          accent="amber"
        />
        <KpiCard
          label="Agotados"
          value={fData ? String(fData.summary.agotado) : '—'}
          icon={<PackageX className="w-4 h-4" />}
          sub={fData ? `${fData.summary.critico} críticos` : undefined}
          accent="rose"
        />
        <KpiCard
          label="Proveedores a pedir"
          value={rData ? String(rData.suppliers.length) : '—'}
          icon={<Truck className="w-4 h-4" />}
          accent="brand"
        />
        <KpiCard
          label="Inversión sugerida"
          value={rData ? formatCurrency(rData.total_cost) : '—'}
          icon={<ShoppingCart className="w-4 h-4" />}
          sub={`Para cubrir ${targetDays} días`}
          accent="emerald"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {([
          { id: 'forecast', label: 'Predicción de quiebre', icon: CalendarClock },
          { id: 'ordenes', label: 'Órdenes por proveedor', icon: Truck },
        ] as { id: Tab; label: string; icon: React.FC<{ className?: string }> }[]).map((t) => {
          const Icon = t.icon;
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                active ? 'border-brand-600 text-brand-700' : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" /> {t.label}
            </button>
          );
        })}
      </div>

      {(forecast.isLoading || replenish.isLoading) && (
        <div className="text-center py-16 text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" /> Calculando rotación y cobertura…
        </div>
      )}

      {tab === 'forecast' && fData && <ForecastTab data={fData} />}
      {tab === 'ordenes' && rData && <OrdersTab data={rData} />}
    </div>
  );
}

function ForecastTab({ data }: { data: StockoutForecastData }) {
  if (data.items.length === 0) {
    return (
      <Card className="p-10 text-center text-muted-foreground">
        <Boxes className="w-8 h-8 mx-auto mb-2 opacity-50" />
        Ningún producto en riesgo de quiebre en los próximos días. ¡Inventario sano!
      </Card>
    );
  }
  return (
    <Card className="overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
            <tr>
              <th className="text-left font-semibold px-3 py-2">Producto</th>
              <th className="text-left font-semibold px-3 py-2">Proveedor</th>
              <th className="text-center font-semibold px-3 py-2">Stock</th>
              <th className="text-center font-semibold px-3 py-2">Venta/día</th>
              <th className="text-center font-semibold px-3 py-2">Cobertura</th>
              <th className="text-center font-semibold px-3 py-2">Se agota</th>
              <th className="text-center font-semibold px-3 py-2">Estado</th>
              <th className="text-right font-semibold px-3 py-2">Pedir</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {data.items.map((r) => {
              const badge = LEVEL_BADGE[r.level] ?? LEVEL_BADGE.ok;
              return (
                <tr key={r.product_id} className="hover:bg-muted/30">
                  <td className="px-3 py-2">
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">{r.sku}</div>
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{r.supplier_name ?? '—'}</td>
                  <td className="px-3 py-2 text-center">{r.available}</td>
                  <td className="px-3 py-2 text-center text-muted-foreground">{r.velocity.toFixed(1)}</td>
                  <td className="px-3 py-2 text-center">
                    {r.days_cover !== null ? <span className="font-medium">{r.days_cover.toFixed(0)}d</span> : '—'}
                  </td>
                  <td className="px-3 py-2 text-center text-muted-foreground">{r.stockout_date ?? '—'}</td>
                  <td className="px-3 py-2 text-center"><Badge className={badge.cls}>{badge.label}</Badge></td>
                  <td className="px-3 py-2 text-right font-bold text-brand-700">{r.suggested_reorder}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function OrdersTab({ data }: { data: ReplenishmentData }) {
  if (data.suppliers.length === 0) {
    return (
      <Card className="p-10 text-center text-muted-foreground">
        <Truck className="w-8 h-8 mx-auto mb-2 opacity-50" />
        No hay pedidos sugeridos por ahora. El stock cubre la demanda proyectada.
      </Card>
    );
  }
  return (
    <div className="space-y-4">
      {data.suppliers.map((s) => (
        <Card key={s.supplier_id ?? s.supplier_name} className="overflow-hidden">
          <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30 flex-wrap gap-2">
            <div>
              <div className="font-semibold flex items-center gap-2">
                <Truck className="w-4 h-4 text-brand-600" /> {s.supplier_name}
              </div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {s.lines.length} productos · {s.total_units} unidades · {formatCurrency(s.total_cost)}
              </div>
            </div>
            {s.whatsapp_url ? (
              <a href={s.whatsapp_url} target="_blank" rel="noopener noreferrer">
                <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5">
                  <MessageCircle className="w-4 h-4" /> Enviar pedido
                </Button>
              </a>
            ) : (
              <span className="text-xs text-muted-foreground">Sin teléfono de proveedor</span>
            )}
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/20 text-xs uppercase text-muted-foreground">
                <tr>
                  <th className="text-left font-semibold px-3 py-2">Producto</th>
                  <th className="text-center font-semibold px-3 py-2">Stock</th>
                  <th className="text-center font-semibold px-3 py-2">Cobertura</th>
                  <th className="text-right font-semibold px-3 py-2">Cantidad</th>
                  <th className="text-right font-semibold px-3 py-2">Costo est.</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {s.lines.map((l) => (
                  <tr key={l.product_id} className="hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <div className="font-medium">{l.name}</div>
                      <div className="text-xs text-muted-foreground">{l.sku}</div>
                    </td>
                    <td className="px-3 py-2 text-center text-muted-foreground">{l.available}</td>
                    <td className="px-3 py-2 text-center text-muted-foreground">
                      {l.days_cover !== null ? `${l.days_cover.toFixed(0)}d` : '—'}
                    </td>
                    <td className="px-3 py-2 text-right font-bold text-brand-700">{l.suggested_qty}</td>
                    <td className="px-3 py-2 text-right text-muted-foreground">{formatCurrency(l.line_cost)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      ))}
    </div>
  );
}
