'use client';

/**
 * Datos que faltan en la ficha del cliente (1-nov-2026).
 *
 * Diego: "muchos de los clientes no les capturamos el correo... cuando selecciono
 * el cliente en el admin un pop que diga que falta el correo o el dato que falte
 * para completar esa base de datos... pronto tendré facturación electrónica".
 *
 * `faltantes()` dice qué falta; el modal pide SOLO eso y lo guarda en la ficha.
 */

import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { customers, type Customer } from '@/lib/api';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';

type Campo = 'document_id' | 'email' | 'phone' | 'address' | 'city';

const CAMPOS: { key: Campo; label: string; placeholder: string; type: string; porQue: string }[] = [
  { key: 'document_id', label: 'Cédula', placeholder: '1088266407', type: 'text', porQue: 'para la factura a su nombre' },
  { key: 'email', label: 'Correo', placeholder: 'nombre@correo.com', type: 'email', porQue: 'para enviarle la factura y el correo de gracias' },
  { key: 'phone', label: 'Celular', placeholder: '320 687 6633', type: 'tel', porQue: 'para confirmar pedidos por WhatsApp' },
  { key: 'address', label: 'Dirección', placeholder: 'Calle 12 # 34-56, apto 201', type: 'text', porQue: 'para el domicilio' },
  { key: 'city', label: 'Ciudad', placeholder: 'Dosquebradas', type: 'text', porQue: 'para el domicilio' },
];

export function faltantes(c: Customer | null | undefined): Campo[] {
  if (!c) return [];
  return CAMPOS.filter((f) => !(c[f.key] ?? '').toString().trim()).map((f) => f.key);
}

export function etiquetaFaltantes(c: Customer | null | undefined): string {
  const f = faltantes(c);
  return f.map((k) => CAMPOS.find((x) => x.key === k)!.label.toLowerCase()).join(', ');
}

export function DatosFaltantesModal({
  customer, open, onClose, onSaved,
}: {
  customer: Customer | null;
  open: boolean;
  onClose: () => void;
  onSaved: (c: Customer) => void;
}) {
  const faltan = faltantes(customer);
  const [valores, setValores] = useState<Partial<Record<Campo, string>>>({});
  const mut = useMutation({
    mutationFn: () => {
      const payload: Partial<Record<Campo, string>> = {};
      for (const k of faltan) {
        const v = (valores[k] ?? '').trim();
        if (v) payload[k] = k === 'document_id' || k === 'phone' ? v.replace(/\D/g, '') : v;
      }
      return customers.update(customer!.id, payload);
    },
    onSuccess: (c) => {
      toast.success('Ficha del cliente actualizada');
      setValores({});
      onSaved(c);
    },
    onError: (e: Error) => toast.error(e.message || 'No se pudo guardar'),
  });

  if (!customer || faltan.length === 0) return null;
  const algo = faltan.some((k) => (valores[k] ?? '').trim());

  return (
    <Dialog open={open} onClose={onClose} title={`A ${customer.full_name.split(' ')[0]} le faltan datos`} size="md">
      <DialogBody>
        <div className="flex items-start gap-2 rounded-lg bg-amber-50 border border-amber-200 px-3 py-2 text-sm text-amber-900 mb-4">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>Pídeselos ahora: con la ficha completa la factura sale a su nombre y le llega al correo.</span>
        </div>
        <div className="space-y-3">
          {CAMPOS.filter((f) => faltan.includes(f.key)).map((f) => (
            <div key={f.key}>
              <label className="text-xs font-medium text-muted-foreground block mb-1">
                {f.label} <span className="opacity-70">· {f.porQue}</span>
              </label>
              <Input
                type={f.type}
                inputMode={f.key === 'document_id' || f.key === 'phone' ? 'numeric' : undefined}
                placeholder={f.placeholder}
                value={valores[f.key] ?? ''}
                onChange={(e) => setValores((v) => ({ ...v, [f.key]: e.target.value }))}
                autoFocus={f.key === faltan[0]}
              />
            </div>
          ))}
        </div>
      </DialogBody>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Más tarde</Button>
        <Button onClick={() => mut.mutate()} disabled={!algo || mut.isPending}>
          {mut.isPending ? 'Guardando…' : 'Guardar en la ficha'}
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
