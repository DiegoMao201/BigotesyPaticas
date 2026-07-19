'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, TrendingDown, Wallet, Calendar, Filter, FileSpreadsheet, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { expenses, finance, type ExpensesPage } from '@/lib/api';
import { formatCurrency, formatDate } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { Pagination } from '@/components/ui/pagination';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';

const TIPOS = ['Operativo', 'Administrativo', 'Marketing', 'Personal', 'Inversión', 'Otro'];
const CATEGORIAS = ['Alimentos', 'Servicios', 'Arriendo', 'Nómina', 'Transporte', 'Insumos', 'Publicidad', 'Mantenimiento', 'Impuestos', 'Otros'];
const METODOS = ['Efectivo', 'Bancolombia', 'Nequi', 'Daviplata', 'Tarjeta', 'Transferencia'];

export default function ExpensesPage() {
  const qc = useQueryClient();
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<{ start?: string; end?: string; categoria?: string; metodo_pago?: string }>({});
  const [openCreate, setOpenCreate] = useState(false);
  const [exportingExcel, setExportingExcel] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['expenses', page, filters],
    queryFn: () => expenses.list({ ...filters, page, page_size: 50 }),
  });

  const createMut = useMutation({
    mutationFn: expenses.create,
    onSuccess: () => {
      toast.success('Gasto registrado');
      qc.invalidateQueries({ queryKey: ['expenses'] });
      qc.invalidateQueries({ queryKey: ['finance-summary'] });
      setOpenCreate(false);
    },
    onError: (e: Error) => toast.error(e.message || 'Error al crear gasto'),
  });

  async function handleExportExcel() {
    setExportingExcel(true);
    const toastId = toast.loading('Generando informe ejecutivo con análisis IA… (30–60 seg)');
    try {
      const blob = await finance.exportExcel(12);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BigotesyPaticas_Informe_Financiero_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('Informe descargado correctamente', { id: toastId });
    } catch (e) {
      toast.error('Error al generar el informe', { id: toastId });
    } finally {
      setExportingExcel(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Wallet className="w-6 h-6 text-brand-600" /> Gastos
          </h1>
          <p className="text-sm text-muted-foreground">Control financiero de egresos operativos</p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            onClick={handleExportExcel}
            disabled={exportingExcel}
            className="gap-2 border-emerald-600 text-emerald-700 hover:bg-emerald-50"
          >
            {exportingExcel
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <FileSpreadsheet className="w-4 h-4" />}
            {exportingExcel ? 'Generando…' : 'Informe Ejecutivo'}
          </Button>
          <Button onClick={() => setOpenCreate(true)}>
            <Plus className="w-4 h-4 mr-1" /> Nuevo gasto
          </Button>
        </div>
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Total filtrado</div>
          <div className="text-2xl font-bold mt-1">{formatCurrency(data?.total_monto || 0)}</div>
          <div className="text-xs text-muted-foreground mt-1">{data?.total || 0} registros</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Promedio</div>
          <div className="text-2xl font-bold mt-1">
            {formatCurrency(data?.total ? (data.total_monto / data.total) : 0)}
          </div>
          <div className="text-xs text-muted-foreground mt-1">por gasto</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Mostrados</div>
          <div className="text-2xl font-bold mt-1">{data?.items.length || 0}</div>
          <div className="text-xs text-muted-foreground mt-1">en esta página</div>
        </Card>
      </div>

      {/* Filtros */}
      <Card className="p-4">
        <div className="flex items-center gap-2 text-sm font-medium mb-3 text-muted-foreground">
          <Filter className="w-4 h-4" /> Filtros
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <Input type="date" value={filters.start || ''} onChange={(e) => { setFilters({ ...filters, start: e.target.value }); setPage(1); }} placeholder="Desde" />
          <Input type="date" value={filters.end || ''} onChange={(e) => { setFilters({ ...filters, end: e.target.value }); setPage(1); }} placeholder="Hasta" />
          <Select value={filters.categoria || ''} onChange={(e) => { setFilters({ ...filters, categoria: e.target.value || undefined }); setPage(1); }}>
            <option value="">Todas las categorías</option>
            {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
          </Select>
          <Select value={filters.metodo_pago || ''} onChange={(e) => { setFilters({ ...filters, metodo_pago: e.target.value || undefined }); setPage(1); }}>
            <option value="">Todos los métodos</option>
            {METODOS.map((m) => <option key={m} value={m}>{m}</option>)}
          </Select>
          <Button variant="outline" onClick={() => { setFilters({}); setPage(1); }}>Limpiar</Button>
        </div>
      </Card>

      {/* Tabla */}
      <Card className="overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-xs uppercase text-muted-foreground">
              <tr>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">Categoría</th>
                <th className="text-left px-4 py-3">Descripción</th>
                <th className="text-left px-4 py-3">Método</th>
                <th className="text-right px-4 py-3">Monto</th>
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">Cargando…</td></tr>
              ) : data?.items.length === 0 ? (
                <tr><td colSpan={6} className="text-center py-8 text-muted-foreground">Sin gastos</td></tr>
              ) : (
                data?.items.map((g) => (
                  <tr key={g.id} className="border-t border-border hover:bg-muted/30">
                    <td className="px-4 py-3 text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Calendar className="w-3.5 h-3.5" /> {g.fecha || '—'}
                      </div>
                    </td>
                    <td className="px-4 py-3"><Badge variant="info">{g.tipo || '—'}</Badge></td>
                    <td className="px-4 py-3 font-medium">{g.categoria || '—'}</td>
                    <td className="px-4 py-3 max-w-xs truncate">{g.descripcion}</td>
                    <td className="px-4 py-3"><Badge variant="neutral">{g.metodo_pago || '—'}</Badge></td>
                    <td className="px-4 py-3 text-right font-bold text-red-600">
                      <div className="flex items-center justify-end gap-1">
                        <TrendingDown className="w-3.5 h-3.5" /> {formatCurrency(g.monto)}
                      </div>
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

      <Dialog open={openCreate} onClose={() => setOpenCreate(false)} title="Registrar gasto" size="md">
        <CreateExpenseForm onSubmit={(p) => createMut.mutate(p)} loading={createMut.isPending} />
      </Dialog>
    </div>
  );
}

function CreateExpenseForm({ onSubmit, loading }: { onSubmit: (p: any) => void; loading: boolean }) {
  const [form, setForm] = useState({
    fecha: new Date().toISOString().slice(0, 10),
    tipo: 'Operativo',
    categoria: 'Otros',
    descripcion: '',
    monto: 0,
    metodo_pago: 'Efectivo',
    banco_origen: '',
  });

  return (
    <form onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}>
      <DialogBody className="space-y-4">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Fecha</label>
            <Input type="date" value={form.fecha} onChange={(e) => setForm({ ...form, fecha: e.target.value })} required />
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Monto</label>
            <Input type="number" min="0" step="0.01" value={form.monto || ''} onChange={(e) => setForm({ ...form, monto: parseFloat(e.target.value) || 0 })} required />
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Tipo</label>
            <Select value={form.tipo} onChange={(e) => setForm({ ...form, tipo: e.target.value })}>
              {TIPOS.map((t) => <option key={t} value={t}>{t}</option>)}
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Categoría</label>
            <Select value={form.categoria} onChange={(e) => setForm({ ...form, categoria: e.target.value })}>
              {CATEGORIAS.map((c) => <option key={c} value={c}>{c}</option>)}
            </Select>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-medium mb-1 block">Método de pago</label>
            <Select value={form.metodo_pago} onChange={(e) => setForm({ ...form, metodo_pago: e.target.value })}>
              {METODOS.map((m) => <option key={m} value={m}>{m}</option>)}
            </Select>
          </div>
          <div>
            <label className="text-xs font-medium mb-1 block">Banco origen (opcional)</label>
            <Input value={form.banco_origen} onChange={(e) => setForm({ ...form, banco_origen: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="text-xs font-medium mb-1 block">Descripción</label>
          <Input value={form.descripcion} onChange={(e) => setForm({ ...form, descripcion: e.target.value })} placeholder="Describe el gasto…" />
        </div>
      </DialogBody>
      <DialogFooter>
        <Button type="submit" disabled={loading || !form.monto}>
          {loading ? 'Guardando…' : 'Guardar gasto'}
        </Button>
      </DialogFooter>
    </form>
  );
}
