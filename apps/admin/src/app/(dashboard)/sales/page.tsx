'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { FileText, XCircle, ShoppingCart, Filter } from 'lucide-react';
import { toast } from 'sonner';
import { sales, API_BASE } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select } from '@/components/ui/select';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { formatCurrency, formatDate } from '@/lib/utils';

const STATUS_BADGE: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  Pagado: 'success',
  'Abono parcial': 'warning',
  Pendiente: 'danger',
};

const ORDER_STATUS_BADGE: Record<string, 'success' | 'warning' | 'danger' | 'neutral'> = {
  completed: 'success',
  pending: 'warning',
  cancelled: 'danger',
  processing: 'warning',
};

export default function SalesPage() {
  const qc = useQueryClient();
  const token = useAuth((s) => s.token);
  const [statusFilter, setStatusFilter] = useState('');
  const [cancelTarget, setCancelTarget] = useState<string | null>(null);
  const [cancelReason, setCancelReason] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['orders', statusFilter],
    queryFn: () => sales.list({ page_size: 100, status: statusFilter || undefined }),
  });

  const cancelMut = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) => sales.cancel(id, reason),
    onSuccess: (_, { id }) => {
      toast.success('Venta cancelada');
      qc.invalidateQueries({ queryKey: ['orders'] });
      setCancelTarget(null);
      setCancelReason('');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  function downloadInvoice(orderId: string) {
    const url = `${API_BASE}/v1/sales/orders/${orderId}/invoice`;
    const link = document.createElement('a');
    link.href = url;
    link.target = '_blank';
    // Pass auth header via direct fetch
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error('Error al obtener factura');
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `factura-${orderId}.html`;
        a.click();
      })
      .catch((e) => toast.error(e.message));
  }

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-4xl font-display font-bold tracking-tight flex items-center gap-2">
            <ShoppingCart className="h-8 w-8 text-brand-600" /> Ventas
          </h1>
          <p className="text-muted-foreground mt-1">{data?.items?.length ?? '…'} pedidos · todos los canales</p>
        </div>
        <div className="flex items-center gap-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="w-40">
            <option value="">Todos los estados</option>
            <option value="completed">Completado</option>
            <option value="pending">Pendiente</option>
            <option value="cancelled">Cancelado</option>
          </Select>
        </div>
      </div>

      {isLoading && <div className="text-center py-12 text-muted-foreground">Cargando…</div>}

      {data && (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
                <tr>
                  <th className="text-left p-4 font-medium">Pedido</th>
                  <th className="text-left p-4 font-medium">Canal</th>
                  <th className="text-left p-4 font-medium">Fecha</th>
                  <th className="text-right p-4 font-medium">Total</th>
                  <th className="text-right p-4 font-medium">Saldo</th>
                  <th className="text-center p-4 font-medium">Pago</th>
                  <th className="text-center p-4 font-medium">Estado</th>
                  <th className="text-center p-4 font-medium">Acciones</th>
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
                    <td className="p-4 text-right font-semibold">{formatCurrency(o.grand_total)}</td>
                    <td className="p-4 text-right text-muted-foreground">{formatCurrency(o.balance_due)}</td>
                    <td className="p-4 text-center">
                      <Badge variant={STATUS_BADGE[o.payment_status] ?? 'neutral'}>{o.payment_status}</Badge>
                    </td>
                    <td className="p-4 text-center">
                      <Badge variant={ORDER_STATUS_BADGE[o.status] ?? 'neutral'}>{o.status}</Badge>
                    </td>
                    <td className="p-4">
                      <div className="flex items-center justify-center gap-1">
                        <button
                          title="Descargar comprobante"
                          onClick={() => downloadInvoice(o.id)}
                          className="p-1.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
                        >
                          <FileText className="w-4 h-4" />
                        </button>
                        {o.status !== 'cancelled' && (
                          <button
                            title="Cancelar venta"
                            onClick={() => setCancelTarget(o.id)}
                            className="p-1.5 rounded hover:bg-rose-50 text-muted-foreground hover:text-rose-600"
                          >
                            <XCircle className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.items.length === 0 && (
            <div className="p-12 text-center text-muted-foreground text-sm">
              No hay pedidos {statusFilter ? `con estado "${statusFilter}"` : 'registrados'}.
            </div>
          )}
        </Card>
      )}

      {/* Cancel dialog */}
      <Dialog
        open={!!cancelTarget}
        onClose={() => { setCancelTarget(null); setCancelReason(''); }}
        title="Cancelar venta"
        size="sm"
      >
        <DialogBody className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Esta acción cancelará la orden y revertirá el stock. No se puede deshacer.
          </p>
          <div>
            <label className="text-xs font-medium mb-1 block">Motivo (opcional)</label>
            <Input
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              placeholder="Ej: solicitud del cliente"
            />
          </div>
        </DialogBody>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => { setCancelTarget(null); setCancelReason(''); }}
          >
            Volver
          </Button>
          <Button
            variant="destructive"
            disabled={cancelMut.isPending}
            onClick={() => cancelTarget && cancelMut.mutate({ id: cancelTarget, reason: cancelReason })}
          >
            {cancelMut.isPending ? 'Cancelando…' : 'Confirmar cancelación'}
          </Button>
        </DialogFooter>
      </Dialog>
    </div>
  );
}
