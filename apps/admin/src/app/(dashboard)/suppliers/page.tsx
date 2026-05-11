'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Truck, Search, Package, ChevronDown, ChevronRight } from 'lucide-react';
import { suppliers } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';

export default function SuppliersPage() {
  const [search, setSearch] = useState('');
  const [expanded, setExpanded] = useState<Set<string>>(new Set());

  const { data, isLoading } = useQuery({
    queryKey: ['suppliers-grouped'],
    queryFn: () => suppliers.grouped(),
  });

  const filtered = data?.filter((s) =>
    !search || s.nombre_proveedor.toLowerCase().includes(search.toLowerCase()),
  ) || [];

  const totalSkus = data?.reduce((s, p) => s + p.sku_count, 0) || 0;

  function toggle(id: string) {
    const next = new Set(expanded);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setExpanded(next);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold font-display flex items-center gap-2">
          <Truck className="w-6 h-6 text-brand-600" /> Proveedores
        </h1>
        <p className="text-sm text-muted-foreground">Catálogo de proveedores y SKUs asociados</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Proveedores</div>
          <div className="text-2xl font-bold mt-1">{data?.length || 0}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">SKUs registrados</div>
          <div className="text-2xl font-bold mt-1">{totalSkus.toLocaleString()}</div>
        </Card>
        <Card className="p-4">
          <div className="text-xs text-muted-foreground uppercase tracking-wider">Promedio SKUs/prov</div>
          <div className="text-2xl font-bold mt-1">
            {data?.length ? Math.round(totalSkus / data.length) : 0}
          </div>
        </Card>
      </div>

      <Card className="p-4">
        <div className="relative">
          <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Buscar proveedor…"
            className="pl-9"
          />
        </div>
      </Card>

      <Card className="overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-muted-foreground">Cargando…</div>
        ) : filtered.length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">Sin proveedores</div>
        ) : (
          <div className="divide-y divide-border">
            {filtered.map((p) => {
              const isOpen = expanded.has(p.nombre_proveedor);
              const totalCosto = p.skus.reduce((s, sku) => s + sku.costo, 0);
              return (
                <div key={p.nombre_proveedor}>
                  <button
                    onClick={() => toggle(p.nombre_proveedor)}
                    className="w-full px-4 py-3 flex items-center justify-between hover:bg-muted/30 transition-colors text-left"
                  >
                    <div className="flex items-center gap-3">
                      {isOpen ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
                      <Truck className="w-4 h-4 text-brand-600" />
                      <div>
                        <div className="font-semibold">{p.nombre_proveedor}</div>
                        <div className="text-xs text-muted-foreground">ID: {p.id_proveedor || '—'}</div>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <Badge variant="brand"><Package className="w-3 h-3" /> {p.sku_count} SKUs</Badge>
                      <span className="text-sm text-muted-foreground hidden md:inline">
                        Costo total: <span className="font-semibold">{formatCurrency(totalCosto)}</span>
                      </span>
                    </div>
                  </button>
                  {isOpen && (
                    <div className="bg-muted/20 px-4 pb-4">
                      <table className="w-full text-sm">
                        <thead className="text-xs uppercase text-muted-foreground">
                          <tr>
                            <th className="text-left py-2">SKU Proveedor</th>
                            <th className="text-left py-2">SKU Interno</th>
                            <th className="text-right py-2">Costo unidad</th>
                          </tr>
                        </thead>
                        <tbody>
                          {p.skus.slice(0, 50).map((s, i) => (
                            <tr key={i} className="border-t border-border/50">
                              <td className="py-2 font-mono text-xs">{s.sku_proveedor || '—'}</td>
                              <td className="py-2 font-mono text-xs">{s.sku_interno || '—'}</td>
                              <td className="py-2 text-right">{formatCurrency(s.costo)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {p.skus.length > 50 && (
                        <div className="text-xs text-muted-foreground mt-2 text-center">
                          Mostrando 50 de {p.skus.length} SKUs
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </Card>
    </div>
  );
}
