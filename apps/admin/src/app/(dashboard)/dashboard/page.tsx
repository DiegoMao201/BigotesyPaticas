'use client';

import { TrendingUp, TrendingDown, DollarSign, Package, ShoppingBag, Users } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { cn, formatCurrency } from '@/lib/utils';

interface KpiProps {
  label: string;
  value: string;
  delta?: number;
  icon: React.ComponentType<{ className?: string }>;
  accent?: string;
}

function Kpi({ label, value, delta, icon: Icon, accent = 'from-brand/20 to-brand/5' }: KpiProps) {
  const positive = (delta ?? 0) >= 0;
  return (
    <Card className="overflow-hidden relative">
      <div className={cn('absolute inset-0 bg-gradient-to-br opacity-50', accent)} />
      <CardHeader className="pb-2 relative">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
          <Icon className="h-4 w-4 text-muted-foreground" />
        </div>
      </CardHeader>
      <CardContent className="relative">
        <div className="text-3xl font-display font-bold tracking-tight">{value}</div>
        {delta !== undefined && (
          <div
            className={cn(
              'flex items-center gap-1 text-xs mt-2',
              positive ? 'text-emerald-500' : 'text-rose-500',
            )}
          >
            {positive ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
            {Math.abs(delta).toFixed(1)}% vs mes anterior
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl font-display font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">Vista ejecutiva en tiempo real</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Kpi
          label="Ingresos del mes"
          value={formatCurrency(0)}
          delta={0}
          icon={DollarSign}
          accent="from-emerald-500/20 to-emerald-500/5"
        />
        <Kpi
          label="Pedidos"
          value="0"
          delta={0}
          icon={ShoppingBag}
          accent="from-blue-500/20 to-blue-500/5"
        />
        <Kpi
          label="Productos activos"
          value="0"
          icon={Package}
          accent="from-brand/20 to-brand/5"
        />
        <Kpi
          label="Clientes"
          value="0"
          delta={0}
          icon={Users}
          accent="from-violet-500/20 to-violet-500/5"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Ventas últimos 30 días</CardTitle>
          </CardHeader>
          <CardContent className="h-72 flex items-center justify-center text-muted-foreground text-sm">
            Conecta el API y carga datos para visualizar la curva.
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Top productos</CardTitle>
          </CardHeader>
          <CardContent className="h-72 flex items-center justify-center text-muted-foreground text-sm">
            Próximamente.
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
