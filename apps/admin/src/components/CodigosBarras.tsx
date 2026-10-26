'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { ScanLine, X } from 'lucide-react';
import { toast } from 'sonner';
import { products } from '@/lib/api';
// Códigos de barras del producto: se pasa la pistola una vez y queda guardado.
// Va fuera del <form> del producto: la pistola termina con Enter y ahí guardaría
// la ficha entera.
const ORIGEN: Record<string, string> = { lector: 'lector', xml: 'factura', ficha: 'ficha' };

export function CodigosBarras({ productId, autoFocus, onSaved }: { productId: string; autoFocus?: boolean; onSaved?: () => void }) {
  const qc = useQueryClient();
  const [code, setCode] = useState('');
  const key = ['product-barcodes', productId];
  const { data: codigos } = useQuery({ queryKey: key, queryFn: () => products.barcodes(productId) });
  // las listas filtradas por "sin código" también cambian
  const refrescar = () => {
    qc.invalidateQueries({ queryKey: key });
    qc.invalidateQueries({ queryKey: ['products'] });
    qc.invalidateQueries({ queryKey: ['inventory-stock'] });
  };
  const addMut = useMutation({
    mutationFn: (c: string) => products.addBarcode(productId, c),
    onSuccess: (r) => {
      toast.success(`Código ${r.code} guardado`);
      setCode('');
      refrescar();
      onSaved?.();
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const delMut = useMutation({
    mutationFn: (c: string) => products.deleteBarcode(productId, c),
    onSuccess: refrescar,
    onError: (e: Error) => toast.error(e.message),
  });

  return (
    <div className="px-6 pt-6">
      <label className="text-xs font-medium mb-1 block">Código de barras</label>
      <div className="relative">
        <ScanLine className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-brand-500" />
        <input
          type="text"
          inputMode="numeric"
          autoComplete="off"
          autoFocus={autoFocus}
          placeholder="Pasa la pistola por el empaque y se guarda solo"
          value={code}
          disabled={addMut.isPending}
          onChange={(e) => setCode(e.target.value)}
          onKeyDown={(e) => {
            if (e.key !== 'Enter') return;
            e.preventDefault();
            if (code.trim()) addMut.mutate(code.trim());
          }}
          className="w-full pl-9 pr-3 h-9 rounded-lg border-2 border-brand-300 bg-brand-50/30 text-sm focus:outline-none focus:ring-2 focus:ring-brand-400 placeholder:text-brand-400"
        />
      </div>
      {!!codigos?.length && (
        <div className="flex flex-wrap gap-2 mt-2">
          {codigos.map((c) => (
            <span key={c.code} className="inline-flex items-center gap-1.5 rounded-md border border-border bg-muted/40 pl-2 pr-1 py-0.5 text-xs font-mono">
              {c.code}
              <span className="font-sans text-muted-foreground">· {ORIGEN[c.source] ?? c.source}</span>
              <button
                type="button"
                aria-label={`Quitar ${c.code}`}
                onClick={() => confirm(`¿Quitar el código ${c.code}?`) && delMut.mutate(c.code)}
                className="p-0.5 rounded hover:bg-muted text-muted-foreground hover:text-foreground"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
