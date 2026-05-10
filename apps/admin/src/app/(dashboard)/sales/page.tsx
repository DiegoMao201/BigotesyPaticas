'use client';

import { useQuery } from '@tanstack/react-query';
import { sales } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { formatCurrency, formatDate } from '@/lib/utils';

const STATUS_STYLES: Record<string, string> = {
  Pagado: 'bg-emerald-500/10 text-emerald-500',
  'Abono parcial': 'bg-amber-500/10 text-amber-500',
  Pendiente: 'bg-rose-500/10 text-rose-500',
};

export default function SalesPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['orders'],
    queryFn: () => sales.list({ page_size: 50 }),
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-display font-bold tracking-tight">Ventas</h1>
        <p className="text-muted-foreground mt-1">Pedidos de todos los canales</p>
      </div>

      {isLoading && <div className="text-center py-12 text-muted-foreground">Cargando…</div>}

      {data && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left p-4 font-medium">Pedido</th>
                <th className="text-left p-4 font-medium">Canal</th>
                <th className="text-left p-4 font-medium">Fecha</th>
                <th className="text-right p-4 font-medium">Total</th>
                <th className="text-right p-4 font-medium">Saldo</th>
                <th className="text-center p-4 font-medium">Pago</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((o) => (
                <tr key={o.id} className="border-t border-border hover:bg-accent/30">
                  <td className="p-4 font-mono text-xs font-semibold">{o.order_number}</td>
                  <td className="p-4 text-xs">{o.channel}</td>
                  <td className="p-4 text-xs">
                    {formatDate(o.occurred_at, { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td className="p-4 text-right font-semibold">
                    {formatCurrency(o.grand_total)}
                  </td>
                  <td className="p-4 text-right text-muted-foreground">
                    {formatCurrency(o.balance_due)}
                  </td>
                  <td className="p-4 text-center">
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        STATUS_STYLES[o.payment_status] ?? 'bg-muted text-muted-foreground'
                      }`}
                    >
                      {o.payment_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {data.items.length === 0 && (
            <div className="p-12 text-center text-muted-foreground text-sm">
              Aún no hay pedidos registrados.
            </div>
          )}
        </Card>
      )}
    </div>
  );
}
