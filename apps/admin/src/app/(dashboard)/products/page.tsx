'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search, Plus, Package } from 'lucide-react';
import { products } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { formatCurrency } from '@/lib/utils';

export default function ProductsPage() {
  const [q, setQ] = useState('');
  const { data, isLoading, error } = useQuery({
    queryKey: ['products', q],
    queryFn: () => products.list({ q: q || undefined, page_size: 50 }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-4xl font-display font-bold tracking-tight">Productos</h1>
          <p className="text-muted-foreground mt-1">Gestiona el catálogo de la tienda</p>
        </div>
        <Button>
          <Plus className="h-4 w-4" /> Nuevo producto
        </Button>
      </div>

      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder="Buscar por nombre o SKU…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          className="pl-10"
        />
      </div>

      {isLoading && (
        <div className="text-center py-12 text-muted-foreground">Cargando productos…</div>
      )}

      {error && (
        <Card className="p-6 border-destructive/50">
          <p className="text-sm text-destructive">
            {error instanceof Error ? error.message : 'Error al cargar productos.'}
          </p>
        </Card>
      )}

      {data && data.items.length === 0 && (
        <Card className="p-12 text-center">
          <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <h3 className="font-display font-semibold text-lg">No hay productos aún</h3>
          <p className="text-muted-foreground text-sm mt-1">
            Importa desde Sheets o crea el primero.
          </p>
        </Card>
      )}

      {data && data.items.length > 0 && (
        <Card className="overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-muted/50 text-muted-foreground text-xs uppercase tracking-wider">
              <tr>
                <th className="text-left p-4 font-medium">Producto</th>
                <th className="text-left p-4 font-medium">SKU</th>
                <th className="text-right p-4 font-medium">Costo</th>
                <th className="text-right p-4 font-medium">Precio</th>
                <th className="text-center p-4 font-medium">Estado</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((p) => (
                <tr key={p.id} className="border-t border-border hover:bg-accent/30 transition-colors">
                  <td className="p-4">
                    <div className="flex items-center gap-3">
                      {p.primary_image_url ? (
                        // eslint-disable-next-line @next/next/no-img-element
                        <img src={p.primary_image_url} alt="" className="h-10 w-10 rounded-lg object-cover" />
                      ) : (
                        <div className="h-10 w-10 rounded-lg bg-muted flex items-center justify-center">
                          <Package className="h-4 w-4 text-muted-foreground" />
                        </div>
                      )}
                      <div>
                        <div className="font-medium">{p.name}</div>
                        {p.short_description && (
                          <div className="text-xs text-muted-foreground line-clamp-1">
                            {p.short_description}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="p-4 font-mono text-xs">{p.sku}</td>
                  <td className="p-4 text-right">{formatCurrency(p.cost)}</td>
                  <td className="p-4 text-right font-semibold">{formatCurrency(p.price)}</td>
                  <td className="p-4 text-center">
                    <span
                      className={
                        p.is_published
                          ? 'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-500'
                          : 'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-muted text-muted-foreground'
                      }
                    >
                      {p.is_published ? 'Publicado' : 'Borrador'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}
