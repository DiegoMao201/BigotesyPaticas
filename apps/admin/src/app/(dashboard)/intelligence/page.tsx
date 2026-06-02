'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Brain, RefreshCw, MessageCircle, Phone, AlertTriangle, Clock,
  TrendingDown, PackageX, Users, Target, DollarSign, Repeat,
} from 'lucide-react';
import { intelligence, type IntelligenceData } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

const URGENCY_BADGE: Record<string, { label: string; cls: string }> = {
  vencido: { label: 'Vencido', cls: 'bg-rose-100 text-rose-800' },
  hoy: { label: 'Hoy', cls: 'bg-amber-100 text-amber-800' },
  proximo: { label: 'Próximo', cls: 'bg-blue-100 text-blue-800' },
};

function KpiCard({ label, value, icon, sub, accent }: {
  label: string; value: string; icon: React.ReactNode; sub?: string; accent?: 'brand' | 'rose' | 'amber' | 'emerald';
}) {
  const accentCls =
    accent === 'rose' ? 'border-rose-200 bg-rose-50/50'
    : accent === 'amber' ? 'border-amber-200 bg-amber-50/50'
    : accent === 'emerald' ? 'border-emerald-200 bg-emerald-50/50'
    : 'border-brand/20 bg-brand/5';
  return (
    <Card className={`p-4 border ${accentCls}`}>
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</span>
        <span className="text-muted-foreground">{icon}</span>
      </div>
      <div className="text-2xl font-bold font-display">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </Card>
  );
}

function WhatsAppButton({ url, phone }: { url: string | null; phone: string | null }) {
  if (!url) {
    return (
      <span className="text-xs text-muted-foreground flex items-center gap-1">
        <Phone className="w-3 h-3" /> Sin teléfono
      </span>
    );
  }
  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      <Button size="sm" className="bg-emerald-600 hover:bg-emerald-700 text-white gap-1.5 h-8">
        <MessageCircle className="w-3.5 h-3.5" /> WhatsApp
      </Button>
    </a>
  );
}

type Tab = 'recompra' | 'riesgo' | 'capital';

export default function IntelligencePage() {
  const [tab, setTab] = useState<Tab>('recompra');
  const qc = useQuery({
    queryKey: ['intelligence-overview'],
    queryFn: () => intelligence.overview(),
    staleTime: 5 * 60_000,
  });

  const data: IntelligenceData | undefined = qc.data;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Brain className="w-6 h-6 text-brand-600" /> Centro de Inteligencia
          </h1>
          <p className="text-sm text-muted-foreground">
            A quién contactar hoy para vender más, quién se está enfriando y qué capital está atrapado.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={() => qc.refetch()} disabled={qc.isFetching}>
          <RefreshCw className={`w-4 h-4 ${qc.isFetching ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KpiCard
          label="Por recomprar"
          value={data ? String(data.summary.repurchase_due) : '—'}
          icon={<Repeat className="w-4 h-4" />}
          sub={data ? `Oportunidad ${formatCurrency(data.summary.repurchase_revenue_opportunity)}` : undefined}
          accent="emerald"
        />
        <KpiCard
          label="En riesgo de fuga"
          value={data ? String(data.summary.at_risk_count) : '—'}
          icon={<TrendingDown className="w-4 h-4" />}
          sub={data ? `Valor histórico ${formatCurrency(data.summary.at_risk_value)}` : undefined}
          accent="amber"
        />
        <KpiCard
          label="Clientes activos 90d"
          value={data ? `${data.summary.customers_active_90d}` : '—'}
          icon={<Users className="w-4 h-4" />}
          sub={data ? `de ${data.summary.customers_total} totales` : undefined}
          accent="brand"
        />
        <KpiCard
          label="Capital atrapado"
          value={data ? formatCurrency(data.summary.trapped_capital) : '—'}
          icon={<PackageX className="w-4 h-4" />}
          sub={data ? `${data.summary.dead_stock_count} productos sin rotar` : undefined}
          accent="rose"
        />
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border overflow-x-auto">
        {([
          { id: 'recompra', label: 'Recompra', icon: Repeat, count: data?.summary.repurchase_due },
          { id: 'riesgo', label: 'En riesgo', icon: AlertTriangle, count: data?.summary.at_risk_count },
          { id: 'capital', label: 'Capital atrapado', icon: PackageX, count: data?.summary.dead_stock_count },
        ] as { id: Tab; label: string; icon: React.FC<{ className?: string }>; count?: number }[]).map((t) => {
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
              {t.count !== undefined && t.count > 0 && (
                <span className="ml-1 text-[10px] font-bold bg-brand/15 text-brand-700 rounded-full px-1.5 py-0.5">
                  {t.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {qc.isLoading && (
        <div className="text-center py-16 text-muted-foreground">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2" /> Analizando datos del negocio…
        </div>
      )}
      {qc.isError && (
        <Card className="p-8 text-center text-rose-600">
          <AlertTriangle className="w-6 h-6 mx-auto mb-2" /> No se pudo cargar la inteligencia. Reintenta.
        </Card>
      )}

      {data && tab === 'recompra' && <RepurchaseTab data={data} />}
      {data && tab === 'riesgo' && <AtRiskTab data={data} />}
      {data && tab === 'capital' && <DeadStockTab data={data} />}
    </div>
  );
}

function RepurchaseTab({ data }: { data: IntelligenceData }) {
  if (data.repurchase.length === 0) {
    return (
      <Card className="p-10 text-center text-muted-foreground">
        <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
        Sin clientes por recomprar en este momento. ¡Vas al día!
      </Card>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        <Clock className="w-3.5 h-3.5" />
        Clientes que, según su ritmo de compra, ya deberían volver. Contáctalos con un mensaje listo.
      </p>
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left font-semibold px-3 py-2">Cliente</th>
                <th className="text-left font-semibold px-3 py-2">Producto habitual</th>
                <th className="text-center font-semibold px-3 py-2">Estado</th>
                <th className="text-center font-semibold px-3 py-2">Última</th>
                <th className="text-center font-semibold px-3 py-2">Ciclo</th>
                <th className="text-right font-semibold px-3 py-2">Histórico</th>
                <th className="text-right font-semibold px-3 py-2">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.repurchase.map((r) => {
                const badge = URGENCY_BADGE[r.urgency] ?? URGENCY_BADGE.proximo;
                return (
                  <tr key={r.customer_id} className="hover:bg-muted/30">
                    <td className="px-3 py-2">
                      <div className="font-medium">{r.name}</div>
                      <div className="text-xs text-muted-foreground">{r.orders} compras</div>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground max-w-[200px] truncate">
                      {r.favorite_product ?? '—'}
                    </td>
                    <td className="px-3 py-2 text-center">
                      <Badge className={badge.cls}>{badge.label}</Badge>
                      <div className="text-[11px] text-muted-foreground mt-0.5">
                        {r.days_overdue > 0 ? `+${r.days_overdue}d tarde` : `en ${Math.abs(r.days_overdue)}d`}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-center text-muted-foreground">hace {r.days_since}d</td>
                    <td className="px-3 py-2 text-center text-muted-foreground">~{r.avg_interval_days}d</td>
                    <td className="px-3 py-2 text-right font-medium">{formatCurrency(r.monetary)}</td>
                    <td className="px-3 py-2 text-right">
                      <WhatsAppButton url={r.whatsapp_url} phone={r.phone} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

function AtRiskTab({ data }: { data: IntelligenceData }) {
  if (data.at_risk.length === 0) {
    return (
      <Card className="p-10 text-center text-muted-foreground">
        <Users className="w-8 h-8 mx-auto mb-2 opacity-50" />
        Ningún cliente valioso en riesgo de fuga. ¡Excelente retención!
      </Card>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        <AlertTriangle className="w-3.5 h-3.5" />
        Clientes recurrentes que llevan tiempo sin comprar. Recupéralos con un mensaje y un detalle.
      </p>
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left font-semibold px-3 py-2">Cliente</th>
                <th className="text-center font-semibold px-3 py-2">Segmento</th>
                <th className="text-center font-semibold px-3 py-2">Sin comprar</th>
                <th className="text-center font-semibold px-3 py-2">Compras</th>
                <th className="text-right font-semibold px-3 py-2">Histórico</th>
                <th className="text-right font-semibold px-3 py-2">Acción</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.at_risk.map((r) => (
                <tr key={r.customer_id} className="hover:bg-muted/30">
                  <td className="px-3 py-2 font-medium">{r.name}</td>
                  <td className="px-3 py-2 text-center text-muted-foreground">{r.segment ?? '—'}</td>
                  <td className="px-3 py-2 text-center">
                    <span className="text-amber-700 font-medium">{r.days_since}d</span>
                  </td>
                  <td className="px-3 py-2 text-center text-muted-foreground">{r.orders}</td>
                  <td className="px-3 py-2 text-right font-medium">{formatCurrency(r.monetary)}</td>
                  <td className="px-3 py-2 text-right">
                    <WhatsAppButton url={r.whatsapp_url} phone={r.phone} />
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

function DeadStockTab({ data }: { data: IntelligenceData }) {
  if (data.dead_stock.length === 0) {
    return (
      <Card className="p-10 text-center text-muted-foreground">
        <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-50" />
        Sin capital atrapado relevante. Tu inventario está rotando bien.
      </Card>
    );
  }
  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground flex items-center gap-1.5">
        <PackageX className="w-3.5 h-3.5" />
        Productos con stock y costo que no se venden hace mucho. Considera promociones o combos para liberar caja.
      </p>
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left font-semibold px-3 py-2">Producto</th>
                <th className="text-center font-semibold px-3 py-2">Stock</th>
                <th className="text-right font-semibold px-3 py-2">Costo unit.</th>
                <th className="text-center font-semibold px-3 py-2">Sin vender</th>
                <th className="text-right font-semibold px-3 py-2">Capital atrapado</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {data.dead_stock.map((r) => (
                <tr key={r.product_id} className="hover:bg-muted/30">
                  <td className="px-3 py-2">
                    <div className="font-medium">{r.name}</div>
                    <div className="text-xs text-muted-foreground">{r.sku}</div>
                  </td>
                  <td className="px-3 py-2 text-center">{r.available}</td>
                  <td className="px-3 py-2 text-right text-muted-foreground">{formatCurrency(r.unit_cost)}</td>
                  <td className="px-3 py-2 text-center text-muted-foreground">
                    {r.days_no_sale === null ? 'nunca' : `${r.days_no_sale}d`}
                  </td>
                  <td className="px-3 py-2 text-right font-bold text-rose-600">{formatCurrency(r.trapped_capital)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
