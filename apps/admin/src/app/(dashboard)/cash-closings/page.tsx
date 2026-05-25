'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ReceiptText, Calendar, TrendingUp, TrendingDown, AlertCircle,
  CheckCircle2, Wallet, CreditCard, Smartphone, ArrowRightLeft,
  Lock, RefreshCw, ChevronDown, ChevronUp, DollarSign,
} from 'lucide-react';
import { toast } from 'sonner';
import { cashClosings, type CashClosing } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Pagination } from '@/components/ui/pagination';

// Iconos por método de pago
const METHOD_ICON: Record<string, React.ReactNode> = {
  Efectivo: <Wallet className="w-4 h-4" />,
  Tarjeta: <CreditCard className="w-4 h-4" />,
  Nequi: <Smartphone className="w-4 h-4" />,
  Daviplata: <Smartphone className="w-4 h-4" />,
  Transferencia: <ArrowRightLeft className="w-4 h-4" />,
};

const METHOD_COLOR: Record<string, string> = {
  Efectivo: 'text-emerald-600 bg-emerald-50 border-emerald-200',
  Tarjeta: 'text-blue-600 bg-blue-50 border-blue-200',
  Nequi: 'text-purple-600 bg-purple-50 border-purple-200',
  Daviplata: 'text-orange-600 bg-orange-50 border-orange-200',
  Transferencia: 'text-cyan-600 bg-cyan-50 border-cyan-200',
};

function getMethodStyle(method: string) {
  return METHOD_COLOR[method] ?? 'text-gray-600 bg-gray-50 border-gray-200';
}
function getMethodIcon(method: string) {
  return METHOD_ICON[method] ?? <DollarSign className="w-4 h-4" />;
}

// ─── Panel del Cierre de Hoy ──────────────────────────────────────────────────
function TodayPanel() {
  const qc = useQueryClient();
  const [showClose, setShowClose] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [saldoContado, setSaldoContado] = useState('');
  const [gastos, setGastos] = useState('');
  const [notasClose, setNotasClose] = useState('');
  const [editGastos, setEditGastos] = useState('');
  const [editSaldoInicial, setEditSaldoInicial] = useState('');
  const [editNotas, setEditNotas] = useState('');

  const { data: today, isLoading, refetch } = useQuery({
    queryKey: ['cash-closing-today'],
    queryFn: () => cashClosings.today(),
    refetchInterval: 30_000, // auto-refresh cada 30s
  });

  const patchMutation = useMutation({
    mutationFn: (p: { gastos_efectivo?: number; saldo_inicial?: number; notas?: string }) =>
      cashClosings.patch(today!.id, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-closing-today'] });
      qc.invalidateQueries({ queryKey: ['cash-closings'] });
      setShowEdit(false);
      toast.success('Cierre actualizado');
    },
    onError: () => toast.error('Error al actualizar'),
  });

  const closeMutation = useMutation({
    mutationFn: (p: { saldo_contado: number; gastos_efectivo?: number; notas?: string }) =>
      cashClosings.close(today!.id, p),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cash-closing-today'] });
      qc.invalidateQueries({ queryKey: ['cash-closings'] });
      setShowClose(false);
      toast.success('Cierre de caja cerrado exitosamente');
    },
    onError: () => toast.error('Error al cerrar el cierre'),
  });

  if (isLoading) {
    return (
      <Card className="p-6 animate-pulse">
        <div className="h-6 bg-muted rounded w-48 mb-4" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-20 bg-muted rounded" />)}
        </div>
      </Card>
    );
  }

  if (!today) return null;

  const isOpen = today.status === 'open';
  const diff = today.diferencia;
  const diffAbs = diff !== null ? Math.abs(diff) : null;
  const allMethods = Array.from(new Set([
    ...Object.keys(today.ventas_por_metodo),
    ...Object.keys(today.creditos_por_metodo),
  ]));

  return (
    <>
      <Card className="overflow-hidden border-2 border-brand-200">
        {/* Header */}
        <div className={`px-6 py-4 flex items-center justify-between ${isOpen ? 'bg-brand-50' : 'bg-emerald-50'}`}>
          <div className="flex items-center gap-3">
            <ReceiptText className={`w-5 h-5 ${isOpen ? 'text-brand-600' : 'text-emerald-600'}`} />
            <div>
              <h2 className="font-semibold text-base">
                Cierre del día — {new Date(today.fecha + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </h2>
              <p className="text-xs text-muted-foreground">{today.order_count} orden{today.order_count !== 1 ? 'es' : ''} registradas</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {isOpen ? (
              <Badge variant="warning" className="gap-1"><AlertCircle className="w-3 h-3" /> Abierto</Badge>
            ) : (
              <Badge variant="success" className="gap-1"><CheckCircle2 className="w-3 h-3" /> Cerrado</Badge>
            )}
            <button
              onClick={() => refetch()}
              className="p-1.5 rounded hover:bg-white/60 transition-colors text-muted-foreground"
              title="Actualizar"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        <div className="p-6 space-y-6">
          {/* KPI Efectivo row */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Saldo inicial</div>
              <div className="text-xl font-bold">{formatCurrency(today.saldo_inicial)}</div>
              <div className="text-xs text-muted-foreground mt-1">Carry-over efectivo</div>
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1"><TrendingUp className="w-3 h-3 text-emerald-500" /> Ventas efectivo</div>
              <div className="text-xl font-bold text-emerald-600">{formatCurrency(today.ventas_efectivo)}</div>
              {today.creditos_efectivo > 0 && (
                <div className="text-xs text-red-500 mt-1">−{formatCurrency(today.creditos_efectivo)} devol.</div>
              )}
            </div>
            <div className="rounded-lg border bg-white p-4">
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1 flex items-center gap-1"><TrendingDown className="w-3 h-3 text-red-500" /> Gastos efectivo</div>
              <div className="text-xl font-bold text-red-600">{formatCurrency(today.gastos_efectivo)}</div>
              {isOpen && (
                <button onClick={() => { setEditGastos(String(today.gastos_efectivo)); setShowEdit(true); }} className="text-xs text-brand-600 hover:underline mt-1">editar</button>
              )}
            </div>
            <div className={`rounded-lg border p-4 ${today.saldo_final_efectivo >= 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-red-50 border-red-200'}`}>
              <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Saldo final efectivo</div>
              <div className={`text-xl font-bold ${today.saldo_final_efectivo >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>{formatCurrency(today.saldo_final_efectivo)}</div>
              <div className="text-xs text-muted-foreground mt-1">= inicial + ventas − devol − gastos</div>
            </div>
          </div>

          {/* Desglose por método de pago */}
          <div>
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">Ventas por método de pago</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {allMethods.length === 0 ? (
                <p className="text-sm text-muted-foreground col-span-full">Sin ventas registradas hoy</p>
              ) : allMethods.map((method) => {
                const venta = today.ventas_por_metodo[method] || 0;
                const credito = today.creditos_por_metodo[method] || 0;
                const neto = venta - credito;
                return (
                  <div key={method} className={`rounded-lg border p-3 ${getMethodStyle(method)}`}>
                    <div className="flex items-center gap-1.5 mb-2 font-medium text-sm">
                      {getMethodIcon(method)} {method}
                    </div>
                    <div className="text-lg font-bold">{formatCurrency(venta)}</div>
                    {credito > 0 && (
                      <div className="text-xs opacity-80">−{formatCurrency(credito)} devol.</div>
                    )}
                    {credito > 0 && (
                      <div className="text-xs font-semibold mt-1">Neto: {formatCurrency(neto)}</div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* Total ventas (todos los métodos) */}
          <div className="flex items-center justify-between rounded-lg bg-muted/40 px-4 py-3">
            <span className="text-sm font-medium">Total ventas del día (todos los métodos)</span>
            <span className="text-lg font-bold">{formatCurrency(today.total_ventas)}</span>
          </div>

          {/* Resultado del cierre (solo si está cerrado) */}
          {!isOpen && diff !== null && (
            <div className={`rounded-lg border-2 p-4 flex items-center justify-between ${diffAbs! < 1000 ? 'border-emerald-300 bg-emerald-50' : 'border-red-300 bg-red-50'}`}>
              <div>
                <div className="font-semibold">{diffAbs! < 1000 ? '✓ Cuadre correcto' : '⚠ Revisar diferencia'}</div>
                <div className="text-sm text-muted-foreground">
                  Contado: {formatCurrency(today.saldo_contado!)} | Sistema: {formatCurrency(today.saldo_final_efectivo)}
                </div>
                {today.notas && <div className="text-sm mt-1 italic">{today.notas}</div>}
              </div>
              <div className={`text-2xl font-bold ${diff >= 0 ? 'text-emerald-700' : 'text-red-700'}`}>
                {diff >= 0 ? '+' : ''}{formatCurrency(diff)}
              </div>
            </div>
          )}

          {/* Actions */}
          {isOpen && (
            <div className="flex gap-3 pt-2">
              <Button variant="outline" size="sm" onClick={() => { setEditGastos(String(today.gastos_efectivo)); setEditSaldoInicial(String(today.saldo_inicial)); setEditNotas(today.notas ?? ''); setShowEdit(true); }}>
                Ajustar gastos / saldo inicial
              </Button>
              <Button size="sm" onClick={() => { setSaldoContado(''); setGastos(String(today.gastos_efectivo)); setNotasClose(''); setShowClose(true); }} className="bg-brand-600 hover:bg-brand-700 text-white">
                <Lock className="w-4 h-4 mr-1.5" /> Cerrar caja
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Dialog: Cerrar caja */}
      <Dialog open={showClose} onClose={() => setShowClose(false)} title="Cerrar caja del día" size="md">
        <DialogBody>
          <p className="text-sm text-muted-foreground mb-4">
            Ingresa el valor físicamente contado en caja. El sistema calculará la diferencia automáticamente.
          </p>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1">Saldo contado en caja <span className="text-red-500">*</span></label>
              <Input
                type="number"
                min="0"
                step="100"
                placeholder="0"
                value={saldoContado}
                onChange={(e) => setSaldoContado(e.target.value)}
              />
              <p className="text-xs text-muted-foreground mt-1">El sistema espera: {formatCurrency(today.saldo_final_efectivo)}</p>
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Gastos efectivo del día</label>
              <Input
                type="number"
                min="0"
                step="100"
                placeholder="0"
                value={gastos}
                onChange={(e) => setGastos(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Notas</label>
              <Input
                placeholder="Observaciones del cierre..."
                value={notasClose}
                onChange={(e) => setNotasClose(e.target.value)}
              />
            </div>
          </div>
          {saldoContado && (
            <div className="mt-4 rounded-lg bg-muted/60 p-3">
              <div className="text-sm font-medium">Vista previa diferencia:</div>
              <div className={`text-xl font-bold mt-1 ${(Number(saldoContado) - today.saldo_final_efectivo) >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                {formatCurrency(Number(saldoContado) - today.saldo_final_efectivo)}
              </div>
            </div>
          )}
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowClose(false)}>Cancelar</Button>
          <Button
            onClick={() => closeMutation.mutate({ saldo_contado: Number(saldoContado), gastos_efectivo: gastos ? Number(gastos) : undefined, notas: notasClose || undefined })}
            disabled={!saldoContado || closeMutation.isPending}
            className="bg-brand-600 hover:bg-brand-700 text-white"
          >
            {closeMutation.isPending ? 'Cerrando...' : 'Confirmar cierre'}
          </Button>
        </DialogFooter>
      </Dialog>

      {/* Dialog: Editar gastos */}
      <Dialog open={showEdit} onClose={() => setShowEdit(false)} title="Ajustar cierre" size="sm">
        <DialogBody>
          <div className="space-y-4">
            <div>
              <label className="text-sm font-medium block mb-1">Saldo inicial (carry-over)</label>
              <Input
                type="number"
                min="0"
                step="100"
                value={editSaldoInicial}
                onChange={(e) => setEditSaldoInicial(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Gastos en efectivo</label>
              <Input
                type="number"
                min="0"
                step="100"
                value={editGastos}
                onChange={(e) => setEditGastos(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-medium block mb-1">Notas</label>
              <Input
                placeholder="Observaciones..."
                value={editNotas}
                onChange={(e) => setEditNotas(e.target.value)}
              />
            </div>
          </div>
        </DialogBody>
        <DialogFooter>
          <Button variant="outline" onClick={() => setShowEdit(false)}>Cancelar</Button>
          <Button
            onClick={() => patchMutation.mutate({ gastos_efectivo: Number(editGastos), saldo_inicial: Number(editSaldoInicial), notas: editNotas || undefined })}
            disabled={patchMutation.isPending}
            className="bg-brand-600 hover:bg-brand-700 text-white"
          >
            {patchMutation.isPending ? 'Guardando...' : 'Guardar'}
          </Button>
        </DialogFooter>
      </Dialog>
    </>
  );
}

// ─── Fila histórico ───────────────────────────────────────────────────────────
function HistoryRow({ c }: { c: CashClosing }) {
  const [expanded, setExpanded] = useState(false);
  const isOpen = c.status === 'open';
  const diff = c.diferencia;
  const totalMethods = Object.entries(c.ventas_por_metodo);

  return (
    <>
      <tr className="border-t border-border hover:bg-muted/30 cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <td className="px-4 py-3 text-muted-foreground">
          <div className="flex items-center gap-1.5">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            <Calendar className="w-3.5 h-3.5" />
            {new Date(c.fecha + 'T12:00:00').toLocaleDateString('es-CO', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })}
          </div>
        </td>
        <td className="px-4 py-3 text-right">{formatCurrency(c.saldo_inicial)}</td>
        <td className="px-4 py-3 text-right text-emerald-600 font-medium">{formatCurrency(c.ventas_efectivo)}</td>
        <td className="px-4 py-3 text-right font-bold">{formatCurrency(c.total_ventas)}</td>
        <td className="px-4 py-3 text-right text-red-600">{formatCurrency(c.gastos_efectivo)}</td>
        <td className="px-4 py-3 text-right font-bold">{formatCurrency(c.saldo_final_efectivo)}</td>
        <td className={`px-4 py-3 text-right font-bold ${diff !== null ? (diff >= 0 ? 'text-emerald-600' : 'text-red-600') : 'text-muted-foreground'}`}>
          {diff !== null ? formatCurrency(diff) : '—'}
        </td>
        <td className="px-4 py-3">
          {isOpen ? (
            <Badge variant="warning" className="gap-1"><AlertCircle className="w-3 h-3" /> Abierto</Badge>
          ) : diff !== null && Math.abs(diff) < 1000 ? (
            <Badge variant="success" className="gap-1"><CheckCircle2 className="w-3 h-3" /> Cuadrado</Badge>
          ) : (
            <Badge variant="danger" className="gap-1"><AlertCircle className="w-3 h-3" /> Revisar</Badge>
          )}
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-border bg-muted/20">
          <td colSpan={8} className="px-6 py-4">
            <div className="flex flex-wrap gap-3">
              {totalMethods.map(([method, total]) => (
                <div key={method} className={`rounded-lg border px-3 py-2 text-sm flex items-center gap-2 ${getMethodStyle(method)}`}>
                  {getMethodIcon(method)}
                  <span className="font-medium">{method}:</span>
                  <span className="font-bold">{formatCurrency(total)}</span>
                  {c.creditos_por_metodo[method] && (
                    <span className="text-xs opacity-75">−{formatCurrency(c.creditos_por_metodo[method])}</span>
                  )}
                </div>
              ))}
              {c.notas && (
                <div className="text-sm text-muted-foreground italic w-full mt-1">
                  Nota: {c.notas}
                </div>
              )}
              {c.closed_by && (
                <div className="text-xs text-muted-foreground w-full">
                  Cerrado por {c.closed_by} — {c.closed_at ? new Date(c.closed_at).toLocaleString('es-CO') : ''}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

// ─── Página principal ─────────────────────────────────────────────────────────
export default function CashClosingsPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery({
    queryKey: ['cash-closings', page],
    queryFn: () => cashClosings.list({ page, page_size: 30 }),
  });

  const totalVentas = data?.items.reduce((s, c) => s + c.total_ventas, 0) || 0;
  const totalEfectivo = data?.items.reduce((s, c) => s + c.ventas_efectivo, 0) || 0;
  const totalGastos = data?.items.reduce((s, c) => s + c.gastos_efectivo, 0) || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <ReceiptText className="w-6 h-6 text-brand-600" /> Cierres de Caja
        </h1>
        <p className="text-sm text-muted-foreground">Cuadre diario por método de pago con carry-over automático de efectivo</p>
      </div>

      {/* Cierre de hoy */}
      <TodayPanel />

      {/* KPIs histórico */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Cierres totales</div>
          <div className="text-2xl font-bold mt-1">{data?.total || 0}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1"><TrendingUp className="w-3 h-3 text-emerald-500" /> Ventas totales</div>
          <div className="text-2xl font-bold mt-1 text-emerald-600">{formatCurrency(totalVentas)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1"><Wallet className="w-3 h-3 text-emerald-500" /> Efectivo total</div>
          <div className="text-2xl font-bold mt-1 text-emerald-700">{formatCurrency(totalEfectivo)}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider flex items-center gap-1"><TrendingDown className="w-3 h-3 text-red-500" /> Gastos efectivo</div>
          <div className="text-2xl font-bold mt-1 text-red-600">{formatCurrency(totalGastos)}</div>
        </Card>
      </div>

      {/* Histórico */}
      <Card className="overflow-hidden">
        <div className="px-4 py-3 border-b border-border">
          <h3 className="font-semibold text-sm">Histórico de cierres</h3>
          <p className="text-xs text-muted-foreground">Haz clic en una fila para ver el desglose por método de pago</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-right px-4 py-3">Saldo inicial</th>
                <th className="text-right px-4 py-3">Efectivo ventas</th>
                <th className="text-right px-4 py-3">Total ventas</th>
                <th className="text-right px-4 py-3">Gastos</th>
                <th className="text-right px-4 py-3">Saldo final</th>
                <th className="text-right px-4 py-3">Diferencia</th>
                <th className="text-left px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={8} className="text-center py-8 text-muted-foreground">Cargando…</td></tr>
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={8} className="text-center py-8 text-muted-foreground">Sin cierres registrados</td></tr>
              ) : (
                data?.items.map((c) => <HistoryRow key={c.id} c={c} />)
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
