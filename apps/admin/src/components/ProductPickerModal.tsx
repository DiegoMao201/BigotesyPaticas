'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Search } from 'lucide-react';
import { Dialog, DialogBody } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { products, type Product } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface ProductPickerModalProps {
  open: boolean;
  onClose: () => void;
  onSelect: (product: Product) => void;
  title?: string;
}

// Selector de producto reutilizable, adaptado de ProductSearch en pos/page.tsx
// -- reusa `products.list({ q })`, que es el único parámetro que el backend
// realmente aplica hoy (category/page_size se ignoran en el backend actual).
export function ProductPickerModal({ open, onClose, onSelect, title = 'Elegir producto' }: ProductPickerModalProps) {
  const [q, setQ] = useState('');

  const { data, isFetching } = useQuery({
    queryKey: ['product-picker', q],
    queryFn: () => products.list({ q: q || undefined }),
    enabled: open,
    staleTime: 30_000,
  });

  return (
    <Dialog open={open} onClose={onClose} title={title} size="lg">
      <DialogBody className="space-y-3">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            autoFocus
            placeholder="Buscar producto por nombre o SKU…"
            className="pl-9"
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 max-h-[420px] overflow-y-auto pr-1">
          {isFetching && !data && (
            [...Array(6)].map((_, i) => <div key={i} className="h-24 bg-muted/30 animate-pulse rounded-lg" />)
          )}
          {data?.items.map((p) => (
            <button
              key={p.id}
              onClick={() => {
                onSelect(p);
                onClose();
              }}
              className="group flex flex-col gap-1 p-3 rounded-lg border border-border hover:border-brand/40 hover:bg-brand/5 transition-all text-left"
            >
              {p.primary_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={p.primary_image_url} alt="" className="h-10 w-10 rounded object-cover mb-1" />
              ) : (
                <div className="h-10 w-10 rounded bg-muted flex items-center justify-center text-xl mb-1">📦</div>
              )}
              <div className="font-medium text-sm leading-tight line-clamp-2">{p.name}</div>
              <div className="text-xs text-muted-foreground font-mono">{p.sku}</div>
              <div className="text-sm font-bold text-brand-700">{formatCurrency(Number(p.price))}</div>
            </button>
          ))}
          {data?.items.length === 0 && (
            <div className="col-span-full py-8 text-center text-muted-foreground text-sm">
              Sin resultados para &ldquo;{q}&rdquo;
            </div>
          )}
        </div>
      </DialogBody>
    </Dialog>
  );
}
