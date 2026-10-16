'use client';

/**
 * Envío nacional por transportadora, dentro del cajón del pedido (16-oct-2026).
 *
 * Diego: "aprobamos la venta y le damos aprobada y así se genera la guía que le
 * llega al cliente, la guía al proveedor para la recogida o nosotros llevamos el
 * paquete al punto donde nos digan".
 *
 * Lo que se ve, en el orden en que se usa:
 *   1. A dónde va y con quién (lo que el cliente eligió y pagó).
 *   2. La guía: se genera sola al facturar; aquí está el botón por si no salió, el
 *      PDF de la etiqueta para imprimir y pegar, y el rastreo.
 *   3. Cómo sale el paquete: pedir recogida en el local, o llevarlo a un punto.
 *   4. Cancelar la guía (solo antes de que la transportadora la escanee).
 */
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Truck, FileText, RefreshCw, MapPin, CalendarClock, XCircle, ExternalLink, Copy, Package } from 'lucide-react';
import { adminPortal, type PortalOrderDetail, type PendingNotification } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { copyText } from '@/lib/whatsapp';

type Props = {
  orderId: string;
  order: PortalOrderDetail;
  onNotif: (n: PendingNotification) => void;
  onChanged: () => void;
};

const ESTADO_ES: Record<string, string> = {
  Created: 'Guía creada',
  Shipped: 'En camino',
  'In transit': 'En camino',
  'Picked Up': 'Recogida por la transportadora',
  'Out for Delivery': 'En reparto',
  Delivered: 'Entregado',
  Canceled: 'Cancelada',
  Cancelled: 'Cancelada',
  Pending: 'Pendiente',
  Returned: 'Devuelto',
  'Address error': 'Error de dirección',
  Delayed: 'Retrasado',
};

function hoyMas(dias: number): string {
  const d = new Date();
  d.setDate(d.getDate() + dias);
  return d.toISOString().slice(0, 10);
}

export function EnvioNacionalPanel({ orderId, order, onNotif, onChanged }: Props) {
  const qc = useQueryClient();
  const d = order.shipping_destination ?? {};
  const q = order.shipping_quote;
  const guia = order.shipment ?? null;
  const [verPuntos, setVerPuntos] = useState(false);
  const [verRecogida, setVerRecogida] = useState(false);
  const [fecha, setFecha] = useState(hoyMas(1));
  const [desde, setDesde] = useState(9);
  const [hasta, setHasta] = useState(13);
  const [confirmarCancelar, setConfirmarCancelar] = useState(false);

  const refrescar = () => {
    qc.invalidateQueries({ queryKey: ['portal-order-detail', orderId] });
    onChanged();
  };
  const onErr = (e: Error) => toast.error(e.message, { duration: 8000 });

  const generarMut = useMutation({
    mutationFn: (aunqueNoPagado: boolean) => adminPortal.generarGuia(orderId, aunqueNoPagado),
    onSuccess: (r) => {
      toast.success(`Guía ${r.guia.tracking_number} generada con ${r.guia.carrier_nombre}`);
      refrescar();
      if (r.pending_notification) onNotif(r.pending_notification);
    },
    onError: onErr,
  });
  const rastrearMut = useMutation({
    mutationFn: () => adminPortal.rastrearGuia(orderId),
    onSuccess: (r) => { toast.success(`Estado: ${ESTADO_ES[r.guia.status ?? ''] ?? r.guia.status ?? 'sin novedad'}`); refrescar(); },
    onError: onErr,
  });
  const cancelarMut = useMutation({
    mutationFn: () => adminPortal.cancelarGuia(orderId),
    onSuccess: (r) => {
      toast.success(r.guia.refunded_amount != null ? `Guía cancelada · Envia devolvió ${formatCurrency(r.guia.refunded_amount)}` : 'Guía cancelada');
      setConfirmarCancelar(false);
      refrescar();
    },
    onError: onErr,
  });
  const recogidaMut = useMutation({
    mutationFn: () => adminPortal.programarRecogida(orderId, { fecha, desde, hasta }),
    onSuccess: (r) => { toast.success(`Recogida pedida${r.guia.pickup_number ? ` · nº ${r.guia.pickup_number}` : ''}`); setVerRecogida(false); refrescar(); },
    onError: onErr,
  });
  const { data: puntos, isLoading: cargandoPuntos } = useQuery({
    queryKey: ['envio-puntos', orderId],
    queryFn: () => adminPortal.puntosEntrega(orderId),
    enabled: verPuntos,
    staleTime: 10 * 60 * 1000,
  });

  const pagado = order.payment_status === 'paid';
  const estadoGuia = guia?.status ? (ESTADO_ES[guia.status] ?? guia.status) : null;

  return (
    <div className="rounded-xl border-2 border-sky-200 bg-sky-50/60 p-3 flex flex-col gap-3 text-sm">
      <div className="flex items-center gap-2">
        <Truck size={16} className="text-sky-700 shrink-0" />
        <p className="font-bold text-sky-900">Envío nacional por transportadora</p>
        {!pagado && (
          <span className="ml-auto text-[11px] font-bold bg-amber-100 text-amber-800 px-2 py-0.5 rounded-full">Sin pago confirmado</span>
        )}
      </div>

      {/* A dónde va */}
      <div className="bg-white rounded-lg p-3 flex flex-col gap-1">
        <p className="font-semibold text-gray-900">
          Recibe: {d.nombre || order.customer_name}{d.cedula ? ` · CC ${d.cedula}` : ''}
          {d.recibe && d.comprador ? <span className="font-normal text-gray-500"> · compró {d.comprador}</span> : null}
        </p>
        <p className="text-gray-700">{d.calle}{d.barrio ? `, ${d.barrio}` : ''}</p>
        <p className="text-gray-700">{d.ciudad}, {d.departamento_nombre} {d.postal ? `· CP ${d.postal}` : ''}</p>
        {d.referencia && <p className="text-gray-500 text-xs">Ref: {d.referencia}</p>}
        <p className="text-gray-500 text-xs">{d.telefono || order.customer_phone}{d.email ? ` · ${d.email}` : ''}</p>
        {q && (
          <p className="mt-1 text-xs text-sky-900 bg-sky-100 rounded-md px-2 py-1 inline-block w-fit">
            {q.carrier_nombre} · {q.service_nombre} · {q.dias} · el cliente pagó <strong>{formatCurrency(q.precio)}</strong>
            {q.precio_envia !== q.precio ? ` (tarifa Envia ${formatCurrency(q.precio_envia)})` : ''}
          </p>
        )}
      </div>

      {/* La guía */}
      {!guia ? (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-sky-900">
            La guía se genera sola al <strong>facturar</strong>. Si no salió, o la cancelaste, sácala aquí.
            Cada guía descuenta saldo de la cuenta de Envia.
          </p>
          <button
            onClick={() => generarMut.mutate(false)}
            disabled={generarMut.isPending || !pagado}
            className="rounded-lg bg-sky-700 text-white px-3 py-2 text-xs font-bold disabled:opacity-50 flex items-center justify-center gap-1.5"
          >
            <FileText size={14} /> {generarMut.isPending ? 'Generando…' : 'Generar guía ahora'}
          </button>
          {!pagado && (
            <button
              onClick={() => { if (confirm('El pedido NO está pagado. ¿Generar la guía igual? Se descuenta saldo de Envia.')) generarMut.mutate(true); }}
              disabled={generarMut.isPending}
              className="text-[11px] text-amber-800 underline self-center"
            >
              Generar aunque no esté pagado
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white rounded-lg p-3 flex flex-col gap-2">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">Guía {guia.carrier_nombre}</p>
              <p className="font-mono font-bold text-gray-900 text-base leading-tight break-all">{guia.tracking_number}</p>
              <p className="text-xs text-gray-600 mt-0.5">
                {estadoGuia ?? 'Creada'}
                {guia.status_at ? ` · ${new Date(guia.status_at).toLocaleString('es-CO', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })}` : ''}
                {guia.label_cost != null ? ` · costó ${formatCurrency(guia.label_cost)}` : ''}
              </p>
            </div>
            <button
              onClick={async () => { if (await copyText(guia.tracking_number ?? '')) toast.success('Guía copiada'); }}
              className="text-gray-400 hover:text-sky-700 shrink-0"
              title="Copiar número de guía"
            >
              <Copy size={14} />
            </button>
          </div>
          <div className="flex flex-wrap gap-2">
            {guia.label_url && (
              <a
                href={guia.label_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 min-w-[140px] rounded-lg bg-sky-700 text-white px-3 py-2 text-xs font-bold flex items-center justify-center gap-1.5"
              >
                <FileText size={14} /> Etiqueta (PDF)
              </a>
            )}
            {guia.track_url && (
              <a
                href={guia.track_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 min-w-[140px] rounded-lg border border-sky-300 text-sky-800 px-3 py-2 text-xs font-bold flex items-center justify-center gap-1.5"
              >
                <ExternalLink size={14} /> Rastreo público
              </a>
            )}
            <button
              onClick={() => rastrearMut.mutate()}
              disabled={rastrearMut.isPending}
              className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
              title="Preguntarle a la transportadora por dónde va"
            >
              <RefreshCw size={13} className={rastrearMut.isPending ? 'animate-spin' : ''} /> Actualizar
            </button>
          </div>
          {guia.events && guia.events.length > 0 && (
            <ul className="text-[11px] text-gray-600 border-t pt-2 flex flex-col gap-0.5 max-h-28 overflow-y-auto">
              {guia.events.slice(0, 8).map((e, i) => (
                <li key={i}>{e.fecha ? `${e.fecha} · ` : ''}{e.estado}{e.lugar ? ` · ${e.lugar}` : ''}</li>
              ))}
            </ul>
          )}
          {guia.packages?.length > 0 && (
            <p className="text-[11px] text-gray-500 flex items-center gap-1">
              <Package size={11} /> {guia.packages.length} caja{guia.packages.length > 1 ? 's' : ''} ·{' '}
              {guia.packages.reduce((a, p) => a + (p.weight ?? 0), 0).toLocaleString('es-CO')} kg declarados
            </p>
          )}

          {/* Cómo sale el paquete */}
          <div className="border-t pt-2 flex flex-col gap-2">
            {guia.pickup_number || guia.pickup_date ? (
              <p className="text-xs text-emerald-800 bg-emerald-50 rounded-md px-2 py-1.5 flex items-center gap-1.5">
                <CalendarClock size={13} /> Recogida pedida{guia.pickup_number ? ` nº ${guia.pickup_number}` : ''} · {guia.pickup_date} · {guia.pickup_window}
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() => setVerRecogida((v) => !v)}
                  className="flex-1 min-w-[150px] rounded-lg border border-emerald-300 text-emerald-800 px-3 py-2 text-xs font-semibold flex items-center justify-center gap-1.5"
                >
                  <CalendarClock size={13} /> Pedir recogida en el local
                </button>
                <button
                  onClick={() => setVerPuntos((v) => !v)}
                  className="flex-1 min-w-[150px] rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-semibold flex items-center justify-center gap-1.5"
                >
                  <MapPin size={13} /> Llevarlo a un punto
                </button>
              </div>
            )}

            {verRecogida && (
              <div className="rounded-lg border border-emerald-200 bg-emerald-50/50 p-2 flex flex-col gap-2">
                <div className="grid grid-cols-3 gap-2">
                  <label className="text-[11px] text-gray-600 flex flex-col gap-0.5">
                    Fecha
                    <input type="date" value={fecha} min={hoyMas(0)} onChange={(e) => setFecha(e.target.value)} className="rounded border border-gray-200 px-2 py-1 text-xs" />
                  </label>
                  <label className="text-[11px] text-gray-600 flex flex-col gap-0.5">
                    Desde
                    <select value={desde} onChange={(e) => setDesde(Number(e.target.value))} className="rounded border border-gray-200 px-2 py-1 text-xs">
                      {[8, 9, 10, 11, 12, 13, 14, 15, 16].map((h) => <option key={h} value={h}>{h}:00</option>)}
                    </select>
                  </label>
                  <label className="text-[11px] text-gray-600 flex flex-col gap-0.5">
                    Hasta
                    <select value={hasta} onChange={(e) => setHasta(Number(e.target.value))} className="rounded border border-gray-200 px-2 py-1 text-xs">
                      {[11, 12, 13, 14, 15, 16, 17, 18].map((h) => <option key={h} value={h}>{h}:00</option>)}
                    </select>
                  </label>
                </div>
                <p className="text-[11px] text-gray-500">La transportadora pasa por Samara Plaza Mall, Local 2, en esa franja. Ten el paquete cerrado y con la etiqueta pegada.</p>
                <button
                  onClick={() => recogidaMut.mutate()}
                  disabled={recogidaMut.isPending || hasta <= desde}
                  className="rounded-lg bg-emerald-600 text-white px-3 py-2 text-xs font-bold disabled:opacity-50"
                >
                  {recogidaMut.isPending ? 'Pidiendo…' : 'Confirmar recogida'}
                </button>
              </div>
            )}

            {verPuntos && (
              <div className="rounded-lg border border-gray-200 bg-white p-2 flex flex-col gap-1.5">
                <p className="text-[11px] font-semibold text-gray-700">
                  Puntos de {puntos?.carrier_nombre ?? guia.carrier_nombre} en Dosquebradas y Pereira
                </p>
                {cargandoPuntos && <p className="text-[11px] text-gray-500">Buscando…</p>}
                {puntos && puntos.puntos.length === 0 && (
                  <p className="text-[11px] text-gray-500">La transportadora no publicó puntos por aquí. Pide la recogida.</p>
                )}
                {puntos?.puntos.map((p, i) => (
                  <a
                    key={i}
                    href={p.lat && p.lng ? `https://www.google.com/maps?q=${p.lat},${p.lng}` : undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-gray-700 hover:text-sky-700 flex items-start gap-1.5"
                  >
                    <MapPin size={11} className="mt-0.5 shrink-0 text-gray-400" />
                    <span>
                      <strong>{p.direccion}</strong>, {p.ciudad}
                      {p.distancia_km != null ? ` · ${p.distancia_km} km` : ''}
                    </span>
                  </a>
                ))}
              </div>
            )}
          </div>

          {/* Cancelar la guía */}
          {!confirmarCancelar ? (
            <button onClick={() => setConfirmarCancelar(true)} className="text-[11px] text-red-500 underline self-start">
              Cancelar esta guía
            </button>
          ) : (
            <div className="flex items-center gap-2 text-[11px] text-red-700">
              <span>Solo se puede antes de que la transportadora la escanee. Envia devuelve el saldo.</span>
              <button onClick={() => cancelarMut.mutate()} disabled={cancelarMut.isPending} className="rounded bg-red-500 text-white px-2 py-1 font-bold disabled:opacity-50 flex items-center gap-1">
                <XCircle size={11} /> Sí, cancelar
              </button>
              <button onClick={() => setConfirmarCancelar(false)} className="underline">No</button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
