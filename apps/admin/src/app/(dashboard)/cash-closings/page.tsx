'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ReceiptText, Calendar, TrendingUp, TrendingDown, AlertCircle, CheckCircle2 } from 'lucide-react';
import { cashClosings } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';

export default function CashClosingsPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ['cash-closings', page],
    queryFn: () => cashClosings.list({ page, page_size: 30 }),
  });

  const totalVentas = data?.items.reduce((s, c) => s + c.ventas_efectivo, 0) || 0;
  const totalGastos = data?.items.reduce((s, c) => s + c.gastos_efectivo, 0) || 0;
  const totalDif = data?.items.reduce((s, c) => s + c.diferencia, 0) || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <ReceiptText className="w-6 h-6 text-brand-600" /> Cierres de Caja
        </h1>
        <p className="text-sm text-muted-foreground">Histórico de arqueos y conciliaciones diarias</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Cierres</div>
          <div className="text-2xl font-bold mt-1">{data?.total || 0}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1"><TrendingUp className="w-3 h-3" /> Ventas efectivo</div>
          <div className="text-2xl font-bold mt-1 text-emerald-600">{formatCurrency(totalVentas)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1"><TrendingDown className="w-3 h-3" /> Gastos efectivo</div>
          <div className="text-2xl font-bold mt-1 text-red-600">{formatCurrency(totalGastos)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Diferencia neta</div>
          <div className={`text-2xl font-bold mt-1 ${totalDif >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>{formatCurrency(totalDif)}</div>
        </Card>
      </div>

      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-right px-4 py-3">Saldo inicial</th>
                <th className="text-right px-4 py-3">Ventas efectivo</th>
                <th className="text-right px-4 py-3">Gastos efectivo</th>
                <th className="text-right px-4 py-3">Saldo final</th>
                <th className="text-right px-4 py-3">Diferencia</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={7} className="text-center py-8 text-muted-foreground">Cargando…</td></tr>
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={7} className="text-center py-8 text-muted-foreground">Sin cierres</td></tr>
              ) : (
                data?.items.map((c) => (
                  <tr key={c.id} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-3 text-muted-foreground">
                      <div className="flex items-center gap-1.5"><Calendar className="w-3.5 h-3.5" /> {c.fecha || '—'}</div>
                    </td>
                    <td className="px-4 py-3 text-right">{formatCurrency(c.saldo_inicial)}</td>
                    <td className="px-4 py-3 text-right text-emerald-600 font-medium">{formatCurrency(c.ventas_efectivo)}</td>
                    <td className="px-4 py-3 text-right text-red-600 font-medium">{formatCurrency(c.gastos_efectivo)}</td>
                    <td className="px-4 py-3 text-right font-bold">{formatCurrency(c.saldo_final)}</td>
                    <td className={`px-4 py-3 text-right font-bold ${c.diferencia >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                      {formatCurrency(c.diferencia)}
                    </td>
                    <td className="px-4 py-3">
                      {Math.abs(c.diferencia) < 1000 ? (
                        <Badge variant="success"><CheckCircle2 className="w-3 h-3" /> Cuadrado</Badge>
                      ) : (
                        <Badge variant="warning"><AlertCircle className="w-3 h-3" /> Revisar</Badge>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="px-4">
          {data && <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />}
        </div>
      </Card>
    </div>
  );
}
