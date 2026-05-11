'use client';

import { useQuery } from '@tanstack/react-query';
import { Boxes, AlertTriangle, TrendingDown, CheckCircle2 } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn } from '@/lib/utils';
import { analytics } from '@/lib/api';

export default function InventoryPage() {
  const { data: alerts, isLoading } = useQuery({
    queryKey: ['stock-alerts', 15],
    queryFn: () => analytics.stockAlerts(15),
    staleTime: 60_000,
  });

  const critical = alerts?.filter((a) => a.level === 'critical') ?? [];
  const low = alerts?.filter((a) => a.level === 'low') ?? [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-display font-bold tracking-tight">Inventario</h1>
        <p className="text-muted-foreground mt-1 text-sm">Stock, alertas y movimientos</p>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-3 gap-4">
        <Card className="border-rose-200 bg-rose-50">
          <CardContent className="p-4 flex items-center gap-3">
            <AlertTriangle className="h-7 w-7 text-rose-500 shrink-0" />
            <div>
              <div className="text-2xl font-display font-bold text-rose-700">{isLoading ? '…' : critical.length}</div>
              <div className="text-xs text-rose-600 font-medium">Sin stock (agotado)</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-amber-200 bg-amber-50">
          <CardContent className="p-4 flex items-center gap-3">
            <TrendingDown className="h-7 w-7 text-amber-500 shrink-0" />
            <div>
              <div className="text-2xl font-display font-bold text-amber-700">{isLoading ? '…' : low.length}</div>
              <div className="text-xs text-amber-600 font-medium">Stock bajo (&lt; 15 uds)</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-emerald-200 bg-emerald-50">
          <CardContent className="p-4 flex items-center gap-3">
            <CheckCircle2 className="h-7 w-7 text-emerald-500 shrink-0" />
            <div>
              <div className="text-2xl font-display font-bold text-emerald-700">—</div>
              <div className="text-xs text-emerald-600 font-medium">OK</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Alertas */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500" />
            Alertas de stock
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="divide-y divide-border/40">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-4 w-24 bg-muted/40 animate-pulse rounded" />
                  <div className="h-4 w-48 bg-muted/30 animate-pulse rounded" />
                </div>
              ))}
            </div>
          ) : (alerts?.length ?? 0) === 0 ? (
            <div className="py-16 text-center text-muted-foreground">
              <CheckCircle2 className="h-10 w-10 mx-auto mb-3 text-emerald-400" />
              <p className="text-sm font-medium text-emerald-600">Todo el stock está en niveles saludables</p>
            </div>
          ) : (
            <div className="divide-y divide-border/40">
              {alerts!.map((item) => (
                <div key={item.product_id} className="flex items-center justify-between px-4 py-3 hover:bg-accent/30 transition-colors">
                  <div>
                    <span className="font-mono text-xs text-muted-foreground mr-3">{item.sku}</span>
                    <span className="text-sm font-medium">{item.name}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className={cn(
                      'font-bold tabular-nums text-sm',
                      item.level === 'critical' ? 'text-rose-600' : 'text-amber-600',
                    )}>
                      {item.available} uds
                    </span>
                    <span className={cn(
                      'px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide',
                      item.level === 'critical'
                        ? 'bg-rose-100 text-rose-700'
                        : 'bg-amber-100 text-amber-700',
                    )}>
                      {item.level === 'critical' ? 'Agotado' : 'Bajo'}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

