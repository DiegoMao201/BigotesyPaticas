'use client';

/**
 * Registro de envíos nacionales (16-oct-2026).
 *
 * Diego: "al facturar solo facturo el producto, pero necesito ver el pago del envío
 * discriminado [...] eso lo llevamos no a ventas sino a un registro de envíos para
 * ver cuánto va costando y cruzarlos con Bold".
 *
 * Una fila por pedido nacional pagado: lo que Bold cobró en total, cuánto de eso
 * era producto (la venta) y cuánto envío, lo que de verdad costó la guía en Envia y
 * la diferencia. Con el CSV se cruza contra el extracto de Bold y la factura de Envia.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Download, Truck, ExternalLink } from 'lucide-react';
import { toast } from 'sonner';
import { adminPortal } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { Card } from '@/components/ui/card';

function hace(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() - dias);
  return d.toISOString().slice(0, 10);
}

const ESTADO_PAGO: Record<string, string> = { paid: 'Pagado', expired: 'Vencido', failed: 'Rechazado', voided: 'Anulado' };

export default function EnviosPage() {
  const [desde, setDesde] = useState(hace(90));
  const [hasta, setHasta] = useState(new Date().toISOString().slice(0, 10));
  const { data, isLoading } = useQuery({
    queryKey: ['registro-envios', desde, hasta],
    queryFn: () => adminPortal.registroEnvios(desde, hasta),
  });

  async function descargar() {
    try {
      const blob = await adminPortal.registroEnviosCsv(desde, hasta);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `registro_envios_${desde}_${hasta}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch (e) { toast.error((e as Error).message); }
  }

  const t = data?.totales;

  return (
    <div className="p-4 md:p-6 flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2"><Truck className="text-sky-700" /> Envíos nacionales</h1>
          <p className="text-sm text-gray-500 mt-1">
            Lo que el cliente pagó por el envío no es venta: aquí se ve aparte, frente a lo que costó la guía, para cruzarlo con Bold y con Envia.
          </p>
        </div>
        <div className="flex items-end gap-2">
          <label className="text-xs text-gray-600 flex flex-col gap-0.5">Desde
            <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm" />
          </label>
          <label className="text-xs text-gray-600 flex flex-col gap-0.5">Hasta
            <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} className="rounded-lg border border-gray-200 px-2 py-1.5 text-sm" />
          </label>
          <button onClick={descargar} className="rounded-lg bg-sky-700 text-white px-3 py-2 text-sm font-semibold flex items-center gap-1.5">
            <Download size={15} /> CSV
          </button>
        </div>
      </div>

      {t && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            { k: 'Pedidos pagados', v: String(t.pedidos_pagados) },
            { k: 'Cobrado por Bold', v: formatCurrency(t.total_bold), s: `${formatCurrency(t.productos)} productos` },
            { k: 'Envío cobrado al cliente', v: formatCurrency(t.envio_cobrado) },
            { k: 'Costo real de guías', v: formatCurrency(t.envio_costo), s: `${t.guias_generadas} guía${t.guias_generadas === 1 ? '' : 's'}` },
            { k: 'Diferencia', v: formatCurrency(t.diferencia), s: t.diferencia >= 0 ? 'a favor' : 'en contra', neg: t.diferencia < 0 },
          ].map((c) => (
            <Card key={c.k} className="p-3">
              <p className="text-[11px] uppercase tracking-wide text-gray-500">{c.k}</p>
              <p className={`text-lg font-bold ${c.neg ? 'text-red-600' : 'text-gray-900'}`}>{c.v}</p>
              {c.s && <p className="text-[11px] text-gray-500">{c.s}</p>}
            </Card>
          ))}
        </div>
      )}

      <Card className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-[11px] uppercase tracking-wide text-gray-500">
            <tr>
              {['Fecha', 'Referencia Bold', 'Cliente', 'Destino', 'Transportadora', 'Pago', 'Total Bold', 'Productos', 'Envío cobrado', 'Costo guía', 'Diferencia', 'Factura', 'Guía'].map((h) => (
                <th key={h} className="px-3 py-2 text-left font-semibold whitespace-nowrap">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading && <tr><td colSpan={13} className="px-3 py-6 text-center text-gray-500">Cargando…</td></tr>}
            {!isLoading && data?.filas.length === 0 && (
              <tr><td colSpan={13} className="px-3 py-8 text-center text-gray-500">Todavía no hay envíos nacionales en este periodo.</td></tr>
            )}
            {data?.filas.map((f) => (
              <tr key={f.order_id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-3 py-2 whitespace-nowrap">{new Date(f.fecha).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}</td>
                <td className="px-3 py-2 font-mono text-xs">{f.order_reference}</td>
                <td className="px-3 py-2">{f.cliente}</td>
                <td className="px-3 py-2 whitespace-nowrap">{f.ciudad}{f.departamento ? `, ${f.departamento}` : ''}</td>
                <td className="px-3 py-2 whitespace-nowrap">{f.carrier}<span className="text-gray-400 text-xs"> · {f.dias}</span></td>
                <td className="px-3 py-2">
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${f.payment_status === 'paid' ? 'bg-teal-600 text-white' : 'bg-gray-200 text-gray-700'}`}>
                    {ESTADO_PAGO[f.payment_status ?? ''] ?? f.payment_status}
                  </span>
                </td>
                <td className="px-3 py-2 tabular-nums text-right">{formatCurrency(f.total_bold)}</td>
                <td className="px-3 py-2 tabular-nums text-right">{formatCurrency(f.productos)}</td>
                <td className="px-3 py-2 tabular-nums text-right font-semibold">{formatCurrency(f.envio_cobrado)}</td>
                <td className="px-3 py-2 tabular-nums text-right">{f.envio_costo == null ? <span className="text-gray-400">sin guía</span> : formatCurrency(f.envio_costo)}</td>
                <td className={`px-3 py-2 tabular-nums text-right ${f.diferencia != null && f.diferencia < 0 ? 'text-red-600 font-semibold' : ''}`}>
                  {f.diferencia == null ? '—' : formatCurrency(f.diferencia)}
                </td>
                <td className="px-3 py-2 text-xs">{f.invoice_number ?? <span className="text-gray-400">sin facturar</span>}</td>
                <td className="px-3 py-2 text-xs whitespace-nowrap">
                  {f.guia ? (
                    <span className={f.guia_cancelada ? 'line-through text-gray-400' : ''}>
                      {f.guia}{f.track_url && !f.guia_cancelada && (
                        <a href={f.track_url} target="_blank" rel="noopener noreferrer" className="ml-1 inline-block text-sky-700 align-middle"><ExternalLink size={12} /></a>
                      )}
                      {f.guia_cancelada && f.refund != null ? ` (devuelto ${formatCurrency(f.refund)})` : ''}
                    </span>
                  ) : <span className="text-gray-400">—</span>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
      <p className="text-xs text-gray-500">
        Cómo cruzar: la columna "Total Bold" debe coincidir con el abono de Bold de esa referencia; "Productos" es lo que quedó en la venta
        y en la factura; "Envío cobrado" menos "Costo guía" es lo que el envío dejó o costó de más. El costo de la guía aparece cuando se genera.
      </p>
    </div>
  );
}
