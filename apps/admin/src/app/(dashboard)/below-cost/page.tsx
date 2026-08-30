'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { startOfMonth, format } from 'date-fns';
import {
  AlertTriangle, ChevronDown, ChevronUp, Pencil, TrendingDown, Package,
} from 'lucide-react';
import { toast } from 'sonner';
import { analyticsBI, products, type BelowCostLine } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { DateRangePicker, type DateRange } from '@/components/analytics/DateRangePicker';

function fmt(d: Date): string {
  return format(d, 'yyyy-MM-dd');
}

// Default de la página: "este mes" (distinto al default de Analítica, que es
// últimos 30 días) — así lo pidió el negocio para este drill-down específico.
function defaultThisMonth(): DateRange {
  const hoy = new Date();
  return { start: fmt(startOfMonth(hoy)), end: fmt(hoy), label: 'Este mes' };
}

const CAUSA_META: Record<
  BelowCostLine['causa'],
  { label: string; variant: 'danger' | 'warning' | 'info'; hint: string }
> = {
  precio_lista_malo: {
    label: 'Precio de lista malo',
    variant: 'danger',
    hint: 'El precio de lista actual ya está en o por debajo del costo — se va a repetir hasta que se corrija.',
  },
  costo_sospechoso: {
    label: 'Costo sospechoso',
    variant: 'warning',
    hint: 'El costo de esta venta difiere más de 30% del costo actual del producto — puede haber un error al cargar la compra.',
  },
  descuento_puntual: {
    label: 'Descuento puntual',
    variant: 'info',
    hint: 'El precio de lista está bien; fue una rebaja puntual en el punto de venta.',
  },
};

interface ProductGroup {
  product_id: string | null;
  sku: string;
  nombre: string;
  costo_actual: number;
  precio_lista_actual: number;
  causa: BelowCostLine['causa'];
  total_perdida: number;
  lines: BelowCostLine[];
}

function groupByProduct(lines: BelowCostLine[]): ProductGroup[] {
  const map = new Map<string, ProductGroup>();
  for (const l of lines) {
    const key = l.product_id ?? `sku:${l.sku}`;
    let g = map.get(key);
    if (!g) {
      g = {
        product_id: l.product_id,
        sku: l.sku,
        nombre: l.nombre,
        costo_actual: l.costo_actual,
        precio_lista_actual: l.precio_lista_actual,
        causa: l.causa,
        total_perdida: 0,
        lines: [],
      };
      map.set(key, g);
    }
    g.total_perdida += l.perdida;
    g.lines.push(l);
  }
  // Causa del grupo: precio_lista_malo es todo-o-nada (mismo precio/costo
  // actual para todas las líneas del producto); costo_sospechoso se marca
  // si CUALQUIER línea lo detecta (vale la pena revisar esa compra).
  for (const g of map.values()) {
    if (g.lines.some((l) => l.causa === 'precio_lista_malo')) g.causa = 'precio_lista_malo';
    else if (g.lines.some((l) => l.causa === 'costo_sospechoso')) g.causa = 'costo_sospechoso';
    else g.causa = 'descuento_puntual';
  }
  return [...map.values()].sort((a, b) => b.total_perdida - a.total_perdida);
}

function EditPriceForm({
  productId, costoActual, precioActual, onDone,
}: {
  productId: string; costoActual: number; precioActual: number; onDone: () => void;
}) {
  const qc = useQueryClient();
  const [nuevoPrecio, setNuevoPrecio] = useState(String(precioActual));
  const [confirmBelowCost, setConfirmBelowCost] = useState(false);

  const nuevoPrecioNum = Number(nuevoPrecio) || 0;
  const margenNuevo = nuevoPrecioNum > 0 ? ((nuevoPrecioNum - costoActual) / nuevoPrecioNum) * 100 : 0;
  const quedaBajoCosto = nuevoPrecioNum > 0 && nuevoPrecioNum <= costoActual;

  const mutation = useMutation({
    mutationFn: () => products.update(productId, { price: nuevoPrecioNum as unknown as string }),
    onSuccess: () => {
      toast.success('Precio actualizado');
      qc.invalidateQueries({ queryKey: ['below-cost'] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      onDone();
    },
    onError: () => toast.error('No se pudo actualizar el precio'),
  });

  return (
    <div className="rounded-lg border border-brand-200 bg-brand-50/40 p-3 space-y-2 mt-2">
      <div className="flex items-center gap-2">
        <label className="text-xs font-medium text-muted-foreground">Nuevo precio</label>
        <Input
          type="number"
          min="0"
          step="100"
          value={nuevoPrecio}
          onChange={(e) => { setNuevoPrecio(e.target.value); setConfirmBelowCost(false); }}
          className="w-32 h-8 text-sm"
        />
        <span className="text-xs text-muted-foreground">
          Costo actual: {formatCurrency(costoActual)}
        </span>
      </div>

      {nuevoPrecioNum > 0 && (
        <p className={`text-xs font-medium ${quedaBajoCosto ? 'text-rose-600' : 'text-emerald-600'}`}>
          Con {formatCurrency(nuevoPrecioNum)} el margen queda en {margenNuevo.toFixed(1)}%
          {quedaBajoCosto && ' — sigue por debajo del costo'}
        </p>
      )}

      {quedaBajoCosto && !confirmBelowCost && (
        <div className="flex items-center gap-2 text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded px-2 py-1.5">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          Este precio sigue en o por debajo del costo actual.
          <button
            onClick={() => setConfirmBelowCost(true)}
            className="underline font-semibold shrink-0"
          >
            Guardar de todos modos
          </button>
        </div>
      )}

      <div className="flex gap-2">
        <Button
          size="sm"
          onClick={() => mutation.mutate()}
          disabled={!nuevoPrecio || mutation.isPending || (quedaBajoCosto && !confirmBelowCost)}
          className="bg-brand-600 hover:bg-brand-700 text-white"
        >
          {mutation.isPending ? 'Guardando…' : 'Guardar precio'}
        </Button>
        <Button size="sm" variant="outline" onClick={onDone}>Cancelar</Button>
      </div>
    </div>
  );
}

function ProductGroupCard({ group }: { group: ProductGroup }) {
  const [expanded, setExpanded] = useState(false);
  const [editing, setEditing] = useState(false);
  const meta = CAUSA_META[group.causa];

  return (
    <Card className="overflow-hidden">
      <div className="p-4">
        <div className="flex items-start justify-between gap-3 flex-wrap">
          <div className="flex items-start gap-3 min-w-0">
            <Package className="w-5 h-5 text-muted-foreground shrink-0 mt-0.5" />
            <div className="min-w-0">
              <p className="font-semibold text-sm truncate">{group.nombre}</p>
              <p className="text-xs text-muted-foreground font-mono">{group.sku}</p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span title={meta.hint}>
              <Badge variant={meta.variant}>{meta.label}</Badge>
            </span>
            <span className="text-sm font-bold text-rose-600">-{formatCurrency(group.total_perdida)}</span>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-3 mt-3">
          <div className="rounded-md bg-muted/40 px-3 py-2">
            <p className="text-[10px] uppercase text-muted-foreground font-semibold">Costo</p>
            <p className="text-sm font-bold">{formatCurrency(group.costo_actual)}</p>
          </div>
          <div className="rounded-md bg-muted/40 px-3 py-2">
            <p className="text-[10px] uppercase text-muted-foreground font-semibold">Precio de lista</p>
            <p className={`text-sm font-bold ${group.precio_lista_actual <= group.costo_actual ? 'text-rose-600' : ''}`}>
              {formatCurrency(group.precio_lista_actual)}
            </p>
          </div>
          <div className="rounded-md bg-muted/40 px-3 py-2">
            <p className="text-[10px] uppercase text-muted-foreground font-semibold">
              Cobrado ({group.lines.length} venta{group.lines.length !== 1 ? 's' : ''})
            </p>
            <p className="text-sm font-bold">
              {formatCurrency(group.lines.reduce((s, l) => s + l.unit_price, 0) / group.lines.length)} prom.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3 mt-3">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-brand-600 hover:underline flex items-center gap-1"
          >
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            {expanded ? 'Ocultar' : 'Ver'} ventas individuales
          </button>
          {group.product_id && !editing && (
            <button
              onClick={() => setEditing(true)}
              className="text-xs text-brand-600 hover:underline flex items-center gap-1"
            >
              <Pencil className="w-3.5 h-3.5" /> Editar precio
            </button>
          )}
        </div>

        {editing && group.product_id && (
          <EditPriceForm
            productId={group.product_id}
            costoActual={group.costo_actual}
            precioActual={group.precio_lista_actual}
            onDone={() => setEditing(false)}
          />
        )}

        {expanded && (
          <div className="mt-3 border-t border-border pt-3 space-y-2">
            {group.lines.map((l) => (
              <div key={l.order_item_id} className="flex items-center justify-between text-xs bg-muted/30 rounded px-3 py-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-muted-foreground">{l.order_number}</span>
                  <span className="text-muted-foreground">{l.fecha}</span>
                  <span>cant. {l.cantidad}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span>costo {formatCurrency(l.unit_cost)}</span>
                  <span>cobrado {formatCurrency(l.unit_price)}</span>
                  <span className="font-semibold text-rose-600">-{formatCurrency(l.perdida)}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function BelowCostPage() {
  const [range, setRange] = useState<DateRange>(defaultThisMonth);
  const { data, isLoading } = useQuery({
    queryKey: ['below-cost', range.start, range.end],
    queryFn: () => analyticsBI.belowCost(range),
    staleTime: 60_000,
  });

  const groups = useMemo(() => (data ? groupByProduct(data.lines) : []), [data]);

  const counts = useMemo(() => {
    const c = { precio_lista_malo: 0, costo_sospechoso: 0, descuento_puntual: 0 };
    for (const g of groups) c[g.causa]++;
    return c;
  }, [groups]);

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <TrendingDown className="w-6 h-6 text-rose-600" /> Ventas por debajo del costo
          </h1>
          <p className="text-sm text-muted-foreground">Agrupado por producto — la vista accionable</p>
        </div>
        <DateRangePicker value={range} onChange={setRange} />
      </div>

      {data && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Pérdida total</p>
            <p className="text-2xl font-bold text-rose-600">{formatCurrency(data.total_loss)}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Líneas afectadas</p>
            <p className="text-2xl font-bold">{data.total_lines}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Precio de lista malo</p>
            <p className="text-2xl font-bold text-rose-600">{counts.precio_lista_malo}</p>
          </Card>
          <Card className="p-4">
            <p className="text-xs font-semibold uppercase text-muted-foreground">Costo sospechoso</p>
            <p className="text-2xl font-bold text-amber-600">{counts.costo_sospechoso}</p>
          </Card>
        </div>
      )}

      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => <div key={i} className="h-32 bg-muted/30 animate-pulse rounded-lg" />)}
        </div>
      ) : groups.length === 0 ? (
        <Card className="p-10 text-center text-muted-foreground text-sm">
          Sin ventas por debajo del costo en este período 🎉
        </Card>
      ) : (
        <div className="space-y-3">
          {groups.map((g) => (
            <ProductGroupCard key={g.product_id ?? g.sku} group={g} />
          ))}
        </div>
      )}
    </div>
  );
}
