'use client';

/**
 * Detalle y gestión de un pedido del portal.
 *
 * Rediseño 28-sep-2026 (Diego: "el flujo es demasiado tosco… no puedo modificar el
 * pedido ni escribirle al cliente sin darle un aprobado"):
 *  - Editar (cantidad, precio, quitar, sustituir, agregar, descuento, dirección) ya NO
 *    cambia el estado solo. Los cambios quedan "sin avisar" y el admin decide:
 *    pedir aprobación, o marcar que ya lo acordó con el cliente (llamada/WhatsApp/tienda).
 *  - "Escribir al cliente" con plantillas rápidas: abre WhatsApp y NO toca el estado.
 *  - Sin stock: "Dejar en lo disponible" en un clic, sustituir o quitar — sin cancelar.
 *  - Después de facturar el pedido queda bloqueado (la venta ya existe).
 *  - WhatsApp se abre en una sola pestaña o en la app (lib/whatsapp.ts): no tumba la sesión.
 */
import { useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  X, ChevronRight, MessageCircle, Package, MapPin,
  Percent, UserCheck, XCircle, Clock,
  CheckCircle2, AlertCircle, Copy, Send, SkipForward,
  AlertTriangle, Minus, Plus, Trash2, Repeat, PackagePlus, Pencil, Lock, Bell, Undo2,
  ShieldAlert, ShieldCheck,
} from 'lucide-react';
import { adminPortal, ApiError, type PortalOrderDetail, type PendingNotification, type Product, type DeliveryEvidence } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { openWhatsApp, getWhatsAppMode, setWhatsAppMode, copyText, type WhatsAppMode } from '@/lib/whatsapp';
import { ProductPickerModal } from '@/components/ProductPickerModal';

const PORTAL_URL = 'https://mi.bigotesypaticas.com';

function stockShortageMessage(err: unknown): string | null {
  if (!(err instanceof ApiError) || err.status !== 409) return null;
  const detail = (err.detail as { detail?: { shortages?: { name: string; requested: number; available: number }[] } })?.detail;
  const shortages = detail?.shortages;
  if (!shortages?.length) return null;
  return shortages.map((s) => `${s.name}: pediste ${s.requested}, solo hay ${s.available}`).join(' · ');
}

const WORKFLOW_LABELS: Record<string, { label: string; color: string }> = {
  received:            { label: 'Recibido',              color: 'bg-blue-100 text-blue-700' },
  under_review:        { label: 'En revisión',           color: 'bg-purple-100 text-purple-700' },
  awaiting_customer:   { label: 'Esperando cliente',     color: 'bg-amber-100 text-amber-700' },
  ready_to_invoice:    { label: 'Listo p/facturar',      color: 'bg-sky-100 text-sky-700' },
  invoiced:            { label: 'Facturado',             color: 'bg-indigo-100 text-indigo-700' },
  in_preparation:      { label: 'En preparación',        color: 'bg-orange-100 text-orange-700' },
  ready_for_delivery:  { label: 'Listo p/entregar',      color: 'bg-teal-100 text-teal-700' },
  in_transit:          { label: 'En camino',             color: 'bg-cyan-100 text-cyan-700' },
  delivered:           { label: 'Entregado ✅',          color: 'bg-green-100 text-green-700' },
  cancelled:           { label: 'Cancelado',             color: 'bg-red-100 text-red-700' },
  returned:            { label: 'Devuelto',              color: 'bg-gray-100 text-gray-600' },
};

// La aprobación del cliente va aparte (bloque "Cliente aprobó"), aquí solo el avance normal
const NEXT_STATUS: Record<string, { value: string; label: string }[]> = {
  received:           [{ value: 'under_review', label: 'Marcar en revisión' }],
  under_review:       [],
  awaiting_customer:  [{ value: 'under_review', label: 'Volver a revisión' }],
  ready_to_invoice:   [{ value: 'invoiced', label: 'Facturar (descuenta inventario)' }],
  invoiced:           [{ value: 'in_preparation', label: 'Iniciar preparación' }],
  in_preparation:     [{ value: 'ready_for_delivery', label: 'Listo para entrega' }],
  ready_for_delivery: [{ value: 'in_transit', label: 'Enviado a domicilio' }],
  in_transit:         [{ value: 'delivered', label: 'Marcar entregado' }],
};

const APPROVABLE = ['received', 'under_review', 'awaiting_customer'];

const CHANGE_LABELS: Record<string, string> = {
  item_quantity_changed: 'Cantidad',
  item_substituted: 'Sustitución',
  item_added: 'Producto agregado',
  item_removed: 'Producto quitado',
  item_price_changed: 'Precio',
  discount_applied: 'Descuento',
  address_changed: 'Dirección',
};

interface Props {
  orderId: string;
  onClose: () => void;
  onRefreshList: () => void;
}

// ── Mensajes rápidos para escribirle al cliente (no cambian el estado) ─────────

function money(n: number) {
  return `$${Math.round(n || 0).toLocaleString('es-CO')}`;
}

function summaryLines(o: PortalOrderDetail) {
  const items = o.items
    .map((i) => `• ${i.name}${i.is_substituted ? ` (cambio por ${i.substituted_from_name})` : ''} x${i.quantity} — ${money(i.subtotal)}`)
    .join('\n');
  const parts = [items, ''];
  if (o.discount_amount > 0) parts.push(`Descuento: -${money(o.discount_amount)}`);
  parts.push(`Envío: ${o.shipping === 0 ? 'Gratis 🎉' : money(o.shipping)}`);
  parts.push(`*Total: ${money(o.total)}*`);
  return parts.join('\n');
}

function quickMessages(o: PortalOrderDetail): { key: string; label: string; text: string }[] {
  const name = o.customer_name?.split(' ')[0] ?? '';
  const hi = `¡Hola${name ? ` ${name}` : ''}! 🐾 Te escribimos de Bigotes y Paticas por tu pedido del portal.`;
  const sinStock = o.items.filter((i) => !i.stock_ok);
  const msgs = [
    { key: 'hola', label: '👋 Saludo', text: `${hi}\n\n` },
    {
      key: 'stock',
      label: '📦 Sin stock',
      text: sinStock.length
        ? `${hi}\n\n${sinStock
            .map((i) => (i.available_stock && i.available_stock > 0
              ? `De *${i.name}* nos quedan ${i.available_stock} y pediste ${i.quantity}.`
              : `*${i.name}* no lo tenemos en este momento.`))
            .join('\n')}\n\n¿Te lo cambiamos por una opción parecida, lo ajustamos a lo disponible o lo quitamos? Como prefieras 🐶🐱`
        : `${hi}\n\nUno de los productos no lo tenemos en este momento. ¿Te lo cambiamos por una opción parecida o lo quitamos?`,
    },
    {
      key: 'direccion',
      label: '📍 Dirección',
      text: `${hi}\n\n¿Nos confirmas la dirección de entrega?\n📍 ${o.shipping_address || '(no la tenemos)'}\n\nSi puedes, compártenos tu ubicación por aquí 🙏`,
    },
    { key: 'resumen', label: '🧾 Resumen', text: `${hi}\n\nAsí va tu pedido:\n\n${summaryLines(o)}` },
    {
      key: 'aprobar',
      label: '✅ Pedir aprobación',
      text: `${hi}\n\nRevisamos tu pedido y así quedaría:\n\n${summaryLines(o)}\n\n¿Lo confirmas? Responde *SÍ* o apruébalo en tu portal 👉 ${PORTAL_URL}/orders/${o.id}`,
    },
    {
      key: 'camino',
      label: '🚚 En camino',
      text: `${hi}\n\nTu pedido ya va en camino 🚚\n📍 ${o.shipping_address || ''}\n\nTotal a pagar: *${money(o.total)}*`,
    },
  ];
  return msgs;
}

export function OrderDetailDrawer({ orderId, onClose, onRefreshList }: Props) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'items' | 'activity' | 'notes'>('items');
  const [cancelReason, setCancelReason] = useState('');
  const [showCancel, setShowCancel] = useState(false);
  const [customerNoteText, setCustomerNoteText] = useState('');
  const [internalNoteText, setInternalNoteText] = useState('');
  const [discountAmount, setDiscountAmount] = useState('');
  const [discountReason, setDiscountReason] = useState('');
  const [showDiscount, setShowDiscount] = useState(false);
  const [pendingNotif, setPendingNotif] = useState<PendingNotification | null>(null);
  const [substitutingItemId, setSubstitutingItemId] = useState<string | null>(null);
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [editingAddress, setEditingAddress] = useState(false);
  const [addressText, setAddressText] = useState('');
  const [priceEdit, setPriceEdit] = useState<{ itemId: string; value: string; reason: string } | null>(null);
  const [showWrite, setShowWrite] = useState(false);
  const [writeText, setWriteText] = useState('');
  const [approvalChannel, setApprovalChannel] = useState('phone_call');
  const [notaLiberar, setNotaLiberar] = useState('');
  const [pidiendoEvidencia, setPidiendoEvidencia] = useState(false);
  const [waMode, setWaModeState] = useState<WhatsAppMode>(() => (typeof window === 'undefined' ? 'web' : getWhatsAppMode()));

  const { data: order, isLoading } = useQuery({
    queryKey: ['portal-order-detail', orderId],
    queryFn: () => adminPortal.orderDetail(orderId),
  });

  const { data: activity = [] } = useQuery({
    queryKey: ['portal-order-activity', orderId],
    queryFn: () => adminPortal.orderActivity(orderId),
  });

  const templates = useMemo(() => (order ? quickMessages(order) : []), [order]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['portal-order-detail', orderId] });
    qc.invalidateQueries({ queryKey: ['portal-order-activity', orderId] });
    onRefreshList();
  };
  const onErr = (e: Error) => toast.error(e.message);

  const liberarMut = useMutation({
    mutationFn: (nota: string) => adminPortal.liberarRiesgo(orderId, nota),
    onSuccess: () => {
      toast.success('Pedido verificado: ya se puede entregar');
      setNotaLiberar('');
      invalidate();
    },
    onError: onErr,
  });

  const workflowMut = useMutation({
    mutationFn: ({ status, notes, evidencia }:
      { status: string; notes?: string; evidencia?: DeliveryEvidence }) =>
      adminPortal.changeWorkflow(orderId, status, notes, evidencia),
    onSuccess: (d) => {
      toast.success(`Estado → ${WORKFLOW_LABELS[d.workflow_status]?.label ?? d.workflow_status}`);
      invalidate();
      if (d.pending_notification) setPendingNotif(d.pending_notification);
    },
    onError: (e: Error) => {
      const shortage = stockShortageMessage(e);
      toast.error(shortage ? `Sin stock para facturar — ${shortage}` : e.message, {
        duration: shortage ? 10000 : undefined,
      });
    },
  });

  const editQtyMut = useMutation({
    mutationFn: ({ itemId, quantity, reason }: { itemId: string; quantity: number; reason?: string }) =>
      adminPortal.editItemQty(orderId, itemId, quantity, reason ?? 'Ajuste de cantidad por disponibilidad'),
    onSuccess: () => { toast.success('Cantidad actualizada'); invalidate(); },
    onError: onErr,
  });

  const priceMut = useMutation({
    mutationFn: ({ itemId, price, reason }: { itemId: string; price: number; reason: string }) =>
      adminPortal.editItemPrice(orderId, itemId, price, reason),
    onSuccess: () => { toast.success('Precio actualizado'); setPriceEdit(null); invalidate(); },
    onError: onErr,
  });

  const removeItemMut = useMutation({
    mutationFn: (itemId: string) =>
      adminPortal.removeItem(orderId, itemId, 'Producto agotado, no se pudo conseguir'),
    onSuccess: () => { toast.success('Producto quitado del pedido'); invalidate(); },
    onError: onErr,
  });

  const cancelMut = useMutation({
    mutationFn: () => adminPortal.cancelOrder(orderId, cancelReason),
    onSuccess: () => { toast.success('Pedido cancelado'); setShowCancel(false); invalidate(); },
    onError: onErr,
  });

  const discountMut = useMutation({
    mutationFn: () => adminPortal.applyDiscount(orderId, parseFloat(discountAmount), discountReason),
    onSuccess: () => { toast.success('Descuento aplicado'); setShowDiscount(false); setDiscountAmount(''); setDiscountReason(''); invalidate(); },
    onError: onErr,
  });

  const notesMut = useMutation({
    mutationFn: () => adminPortal.updateNotes(orderId, { customer_facing_notes: customerNoteText }),
    onSuccess: () => { toast.success('Nota guardada'); setCustomerNoteText(''); invalidate(); },
    onError: onErr,
  });

  const internalNotesMut = useMutation({
    mutationFn: () => adminPortal.updateNotes(orderId, { internal_notes: internalNoteText }),
    onSuccess: () => { toast.success('Nota interna guardada'); setInternalNoteText(''); invalidate(); },
    onError: onErr,
  });

  const substituteMut = useMutation({
    mutationFn: ({ itemId, product }: { itemId: string; product: Product }) =>
      adminPortal.substituteItem(orderId, itemId, {
        new_product_id: product.id,
        reason: 'Producto no disponible, sustituido por el administrador',
      }),
    onSuccess: () => { toast.success('Producto sustituido'); invalidate(); },
    onError: onErr,
  });

  const addItemMut = useMutation({
    mutationFn: (product: Product) => adminPortal.addItem(orderId, { product_id: product.id, quantity: 1 }),
    onSuccess: () => { toast.success('Producto agregado al pedido'); invalidate(); },
    onError: onErr,
  });

  const addressMut = useMutation({
    mutationFn: () => adminPortal.updateShippingAddress(orderId, addressText),
    onSuccess: () => { toast.success('Dirección actualizada'); setEditingAddress(false); invalidate(); },
    onError: onErr,
  });

  const markSentMut = useMutation({
    mutationFn: () => adminPortal.markNotifSent(orderId),
    onSuccess: () => { toast.success('Cambios marcados como avisados'); invalidate(); },
    onError: onErr,
  });

  const approvalMut = useMutation({
    mutationFn: (channel: string) => adminPortal.confirmApproval(orderId, channel),
    onSuccess: () => { toast.success('Aprobado — listo para facturar'); invalidate(); },
    onError: onErr,
  });

  if (isLoading || !order) {
    return (
      <div className="fixed inset-0 bg-black/50 z-40 flex items-center justify-center" onClick={onClose}>
        <div className="bg-white rounded-2xl p-8 shadow-2xl">
          <div className="h-8 w-8 rounded-full border-2 border-teal-200 border-t-teal-600 animate-spin mx-auto" />
        </div>
      </div>
    );
  }

  const ws = order.workflow_status ?? 'received';
  const wsInfo = WORKFLOW_LABELS[ws] ?? { label: ws, color: 'bg-gray-100 text-gray-600' };
  const nextOptions = NEXT_STATUS[ws] ?? [];
  const canCancel = !['delivered', 'cancelled', 'returned'].includes(ws);
  const isAwaiting = ws === 'awaiting_customer';
  const canEditItems = order.is_editable ?? !['invoiced', 'in_preparation', 'ready_for_delivery', 'in_transit', 'delivered', 'cancelled', 'returned'].includes(ws);
  const canEditAddress = !['delivered', 'cancelled', 'returned'].includes(ws);
  const unsent = canEditItems ? order.unsent_changes ?? [] : [];
  const canApprove = APPROVABLE.includes(ws);
  const busy = workflowMut.isPending || approvalMut.isPending || markSentMut.isPending;

  const changeWaMode = (m: WhatsAppMode) => { setWhatsAppMode(m); setWaModeState(m); };
  const sendWhatsApp = (text: string) => {
    openWhatsApp(order.customer_phone, text, waMode);
    copyText(text);
  };
  const openWrite = (key?: string) => {
    const t = templates.find((x) => x.key === key) ?? templates[0];
    setWriteText(t?.text ?? '');
    setShowWrite(true);
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white z-50 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50 shrink-0">
          <div className="min-w-0">
            <p className="text-xs text-gray-500 mb-0.5">Pedido portal #{order.id.slice(0, 8).toUpperCase()}</p>
            <h2 className="font-bold text-gray-900 truncate">{order.customer_name ?? 'Cliente'}</h2>
            {order.customer_phone && (
              <p className="text-xs text-gray-500">{order.customer_phone}</p>
            )}
          </div>
          <div className="flex items-center gap-2">
            <span className={`text-xs font-semibold px-3 py-1 rounded-full ${wsInfo.color}`}>
              {wsInfo.label}
            </span>
            <button onClick={onClose} className="p-2 rounded-lg hover:bg-gray-200 transition-colors">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Totals bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-teal-50 border-b shrink-0 text-sm">
          <span className="text-gray-600">Subtotal: <strong>{formatCurrency(order.subtotal)}</strong></span>
          {order.discount_amount > 0 && (
            <span className="text-red-600">Desc: -{formatCurrency(order.discount_amount)}</span>
          )}
          <span className="text-gray-600">Envío: <strong>{order.shipping === 0 ? 'Gratis' : formatCurrency(order.shipping)}</strong></span>
          <span className="font-bold text-teal-800">Total: {formatCurrency(order.total)}</span>
        </div>

        {/* ── Semáforo antifraude ────────────────────────────────────────────
            Va aquí, pegado al total y antes de cualquier botón, porque la
            decisión que informa es "¿esto sale de la tienda o no?". Más abajo
            nadie la leería a tiempo. */}
        {order.risk_level && order.risk_level !== 'bajo' && (
          <BanderaRiesgo
            order={order}
            nota={notaLiberar}
            setNota={setNotaLiberar}
            onLiberar={() => liberarMut.mutate(notaLiberar)}
            liberando={liberarMut.isPending}
          />
        )}

        {!canEditItems && ws !== 'cancelled' && (
          <div className="flex items-center gap-2 px-4 py-2 bg-indigo-50 border-b border-indigo-100 text-indigo-700 text-xs font-semibold shrink-0">
            <Lock size={13} className="shrink-0" />
            {order.invoice_number ? `Facturado (${order.invoice_number}). ` : ''}Los productos y precios ya no se cambian: si hay que corregir, cancela (devuelve el inventario) y vuelve a crearlo.
          </div>
        )}

        {canEditItems && order.has_stock_issues && (
          <div className="flex items-center gap-2 px-4 py-2 bg-red-50 border-b border-red-100 text-red-700 text-xs font-semibold shrink-0">
            <AlertTriangle size={14} className="shrink-0" />
            Falta stock: ajusta a lo disponible, sustituye o quita — no hace falta cancelar. Escríbele al cliente con “📦 Sin stock”.
          </div>
        )}

        {/* Tabs */}
        <div className="flex border-b shrink-0">
          {(['items', 'activity', 'notes'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
                tab === t ? 'border-b-2 border-teal-600 text-teal-700' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              {t === 'items' ? '📦 Pedido' : t === 'activity' ? '🕐 Actividad' : '📝 Notas'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {tab === 'items' && (
            <>
              {/* Cambios que el cliente no conoce */}
              {unsent.length > 0 && (
                <div className="rounded-xl border-2 border-amber-300 bg-amber-50 p-3 flex flex-col gap-2">
                  <p className="text-sm font-bold text-amber-900 flex items-center gap-1.5">
                    <Bell size={15} /> {unsent.length} cambio{unsent.length === 1 ? '' : 's'} que el cliente aún no conoce
                  </p>
                  <p className="text-xs text-amber-800">
                    {unsent.map((u) => CHANGE_LABELS[u.action] ?? u.action).join(' · ')}
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {ws !== 'awaiting_customer' ? (
                      <button
                        onClick={() => workflowMut.mutate({ status: 'awaiting_customer' })}
                        disabled={busy}
                        className="flex-1 min-w-[160px] rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                      >
                        Pedirle aprobación al cliente
                      </button>
                    ) : (
                      <button
                        onClick={() => { sendWhatsApp(templates.find((t) => t.key === 'aprobar')?.text ?? ''); markSentMut.mutate(); }}
                        disabled={busy}
                        className="flex-1 min-w-[160px] rounded-lg bg-amber-500 px-3 py-2 text-xs font-bold text-white disabled:opacity-50"
                      >
                        Enviar cambios por WhatsApp
                      </button>
                    )}
                    <button
                      onClick={() => approvalMut.mutate('phone_call')}
                      disabled={busy}
                      className="flex-1 min-w-[160px] rounded-lg border border-amber-400 bg-white px-3 py-2 text-xs font-bold text-amber-900 disabled:opacity-50"
                    >
                      Ya lo acordé con el cliente ✓
                    </button>
                  </div>
                </div>
              )}

              {/* Dirección */}
              {!editingAddress ? (
                <div className="flex items-start gap-2 bg-gray-50 rounded-xl p-3 text-sm">
                  <MapPin size={14} className="text-gray-400 mt-0.5 shrink-0" />
                  <span className="text-gray-700 flex-1 whitespace-pre-line">{order.shipping_address || 'Sin dirección registrada'}</span>
                  {canEditAddress && (
                    <button
                      onClick={() => { setAddressText(order.shipping_address ?? ''); setEditingAddress(true); }}
                      className="text-gray-400 hover:text-teal-600 shrink-0"
                      title="Editar dirección"
                    >
                      <Pencil size={13} />
                    </button>
                  )}
                </div>
              ) : (
                <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-2">
                  <textarea
                    value={addressText}
                    onChange={(e) => setAddressText(e.target.value)}
                    rows={2}
                    autoFocus
                    className="rounded-lg border border-gray-200 p-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                  <div className="flex gap-2">
                    <button onClick={() => addressMut.mutate()} disabled={!addressText.trim() || addressMut.isPending}
                      className="bg-teal-600 text-white rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50">
                      Guardar dirección
                    </button>
                    <button onClick={() => setEditingAddress(false)} className="text-xs text-gray-500 underline">Cancelar</button>
                  </div>
                </div>
              )}

              {/* Items */}
              {order.items.map((item) => (
                <div key={item.id} className={`flex flex-col gap-2 bg-white border rounded-xl p-3 ${
                  !item.stock_ok ? 'border-red-300 bg-red-50/40' : item.is_substituted ? 'border-amber-200 bg-amber-50' : 'border-gray-100'
                }`}>
                  <div className="flex items-center gap-3">
                    <div className="h-12 w-12 rounded-lg bg-gray-100 flex items-center justify-center overflow-hidden shrink-0">
                      {item.image_url
                        ? <img src={item.image_url} alt={item.name ?? ''} className="h-full w-full object-contain p-1" />
                        : <Package size={20} className="text-gray-400" />
                      }
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-gray-900 leading-snug">{item.name}</p>
                      {item.is_substituted && (
                        <p className="text-xs text-amber-600">↔ Sustituyó: {item.substituted_from_name}</p>
                      )}
                      {item.sku && <p className="text-xs text-gray-400">{item.sku}</p>}
                      {!item.stock_ok && (
                        <p className="text-xs font-semibold text-red-600 flex items-center gap-1 mt-0.5">
                          <AlertTriangle size={12} /> Hay {item.available_stock ?? 0} en inventario, pidió {item.quantity}
                        </p>
                      )}
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-xs text-gray-500">x{item.quantity} · {formatCurrency(item.unit_price)}</p>
                      <p className="text-sm font-bold text-gray-900">{formatCurrency(item.subtotal)}</p>
                    </div>
                  </div>

                  {canEditItems && (
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-2 pl-[60px]">
                      <div className="flex items-center gap-1 bg-gray-50 border border-gray-200 rounded-lg">
                        <button
                          type="button"
                          onClick={() => item.quantity > 1 && editQtyMut.mutate({ itemId: item.id, quantity: item.quantity - 1 })}
                          disabled={editQtyMut.isPending || item.quantity <= 1}
                          className="p-1.5 text-gray-500 hover:text-gray-800 disabled:opacity-30"
                        >
                          <Minus size={12} />
                        </button>
                        <span className="text-xs font-semibold w-6 text-center">{item.quantity}</span>
                        <button
                          type="button"
                          onClick={() => editQtyMut.mutate({ itemId: item.id, quantity: item.quantity + 1 })}
                          disabled={editQtyMut.isPending}
                          className="p-1.5 text-gray-500 hover:text-gray-800 disabled:opacity-30"
                        >
                          <Plus size={12} />
                        </button>
                      </div>
                      {!item.stock_ok && (item.available_stock ?? 0) > 0 && (
                        <button
                          type="button"
                          onClick={() => editQtyMut.mutate({ itemId: item.id, quantity: item.available_stock as number, reason: `Ajustado a lo disponible (${item.available_stock})` })}
                          disabled={editQtyMut.isPending}
                          className="text-xs font-bold text-white bg-red-500 hover:bg-red-600 rounded-lg px-2 py-1 disabled:opacity-40"
                        >
                          Dejar en {item.available_stock}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setPriceEdit({ itemId: item.id, value: String(Math.round(item.unit_price)), reason: '' })}
                        className="flex items-center gap-1 text-xs text-teal-700 hover:text-teal-900"
                      >
                        <Pencil size={12} /> Precio
                      </button>
                      <button
                        type="button"
                        onClick={() => setSubstitutingItemId(item.id)}
                        disabled={substituteMut.isPending}
                        className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-800 disabled:opacity-40"
                      >
                        <Repeat size={12} /> Sustituir
                      </button>
                      <button
                        type="button"
                        onClick={() => removeItemMut.mutate(item.id)}
                        disabled={removeItemMut.isPending || order.items.length <= 1}
                        title={order.items.length <= 1 ? 'Es el único producto: cancela el pedido o sustitúyelo' : undefined}
                        className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 disabled:opacity-40"
                      >
                        <Trash2 size={12} /> Quitar
                      </button>
                    </div>
                  )}

                  {priceEdit?.itemId === item.id && (
                    <div className="pl-[60px] flex flex-col gap-2">
                      <div className="flex gap-2">
                        <input
                          type="number"
                          min={0}
                          value={priceEdit.value}
                          onChange={(e) => setPriceEdit({ ...priceEdit, value: e.target.value })}
                          className="w-32 rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
                          placeholder="Precio unitario"
                          autoFocus
                        />
                        <input
                          value={priceEdit.reason}
                          onChange={(e) => setPriceEdit({ ...priceEdit, reason: e.target.value })}
                          className="flex-1 rounded-lg border border-gray-200 px-2 py-1.5 text-sm"
                          placeholder="Motivo (ej. precio actualizado)"
                        />
                      </div>
                      <div className="flex gap-2">
                        <button
                          onClick={() => priceMut.mutate({ itemId: item.id, price: parseFloat(priceEdit.value), reason: priceEdit.reason })}
                          disabled={!priceEdit.reason.trim() || priceEdit.value === '' || parseFloat(priceEdit.value) < 0 || priceMut.isPending}
                          className="bg-teal-600 text-white rounded-lg px-3 py-1.5 text-xs font-semibold disabled:opacity-50"
                        >
                          Guardar precio
                        </button>
                        <button onClick={() => setPriceEdit(null)} className="text-xs text-gray-500 underline">Cancelar</button>
                      </div>
                    </div>
                  )}
                </div>
              ))}

              {canEditItems && (
                <button
                  type="button"
                  onClick={() => setShowAddProduct(true)}
                  className="flex items-center justify-center gap-1.5 text-sm text-teal-700 border-2 border-dashed border-teal-200 rounded-xl py-2.5 hover:bg-teal-50 transition-colors"
                >
                  <PackagePlus size={15} /> Agregar producto al pedido
                </button>
              )}

              {/* Descuento */}
              {canEditItems && (!showDiscount ? (
                <button onClick={() => setShowDiscount(true)} className="text-sm text-teal-700 underline flex items-center gap-1 self-start">
                  <Percent size={13} /> {order.discount_amount > 0 ? 'Cambiar descuento' : 'Aplicar descuento'}
                </button>
              ) : (
                <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-2">
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min={0}
                      max={order.subtotal}
                      placeholder="Monto descuento $"
                      value={discountAmount}
                      onChange={(e) => setDiscountAmount(e.target.value)}
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
                    />
                    <input
                      type="text"
                      placeholder="Motivo"
                      value={discountReason}
                      onChange={(e) => setDiscountReason(e.target.value)}
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-sm"
                    />
                  </div>
                  {discountAmount !== '' && (parseFloat(discountAmount) < 0 || parseFloat(discountAmount) > order.subtotal) && (
                    <p className="text-xs text-red-600">El descuento debe estar entre $0 y el subtotal ({formatCurrency(order.subtotal)}).</p>
                  )}
                  <div className="flex gap-2">
                    <button
                      onClick={() => discountMut.mutate()}
                      disabled={!discountAmount || !discountReason || discountMut.isPending || parseFloat(discountAmount) < 0 || parseFloat(discountAmount) > order.subtotal}
                      className="bg-teal-600 text-white rounded-lg px-3 py-1.5 text-sm font-semibold disabled:opacity-50">
                      Aplicar
                    </button>
                    <button onClick={() => setShowDiscount(false)} className="text-sm text-gray-500 underline">Cancelar</button>
                  </div>
                </div>
              ))}
            </>
          )}

          {tab === 'activity' && (
            <div className="flex flex-col gap-2">
              {activity.length === 0 && (
                <p className="text-sm text-gray-400 text-center py-4">Sin actividad registrada</p>
              )}
              {activity.map((log) => (
                <div key={log.id} className={`flex gap-3 p-3 rounded-xl ${log.visible_to_customer ? 'bg-blue-50 border border-blue-100' : 'bg-gray-50'}`}>
                  <div className="shrink-0 mt-0.5">
                    {log.notification_sent_at
                      ? <CheckCircle2 size={14} className="text-green-500" />
                      : log.visible_to_customer
                      ? <AlertCircle size={14} className="text-amber-500" />
                      : <Clock size={14} className="text-gray-400" />
                    }
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{formatAction(log.action)}</p>
                    {log.notes && <p className="text-xs text-gray-500 mt-0.5">{log.notes}</p>}
                    {log.notification_sent_at && (
                      <p className="text-xs text-green-600">Avisado al cliente · {new Date(log.notification_sent_at).toLocaleString('es-CO')}</p>
                    )}
                    <p className="text-[10px] text-gray-400 mt-0.5">{new Date(log.created_at).toLocaleString('es-CO')} · {log.actor_name ?? 'Sistema'}</p>
                  </div>
                </div>
              ))}
            </div>
          )}

          {tab === 'notes' && (
            <div className="flex flex-col gap-3">
              {order.internal_notes && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-3">
                  <p className="text-xs font-semibold text-yellow-800 mb-1">🔒 Notas internas</p>
                  <p className="text-sm text-yellow-900 whitespace-pre-wrap">{order.internal_notes}</p>
                </div>
              )}
              {order.customer_facing_notes && (
                <div className="bg-blue-50 border border-blue-200 rounded-xl p-3">
                  <p className="text-xs font-semibold text-blue-800 mb-1">👤 Nota al cliente (la ve en su portal)</p>
                  <p className="text-sm text-blue-900">{order.customer_facing_notes}</p>
                </div>
              )}
              <div className="flex flex-col gap-2">
                <textarea
                  value={customerNoteText}
                  onChange={(e) => setCustomerNoteText(e.target.value)}
                  placeholder="Nota visible para el cliente en su portal..."
                  rows={3}
                  className="rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <button onClick={() => notesMut.mutate()} disabled={!customerNoteText || notesMut.isPending}
                  className="self-start bg-teal-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50">
                  Guardar nota
                </button>
              </div>

              <div className="flex flex-col gap-2 pt-2 border-t">
                <p className="text-xs font-semibold text-gray-500">🔒 Nota interna (no la ve el cliente)</p>
                <textarea
                  value={internalNoteText}
                  onChange={(e) => setInternalNoteText(e.target.value)}
                  placeholder="Agregar nota interna del equipo..."
                  rows={3}
                  className="rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-yellow-400"
                />
                <button onClick={() => internalNotesMut.mutate()} disabled={!internalNoteText || internalNotesMut.isPending}
                  className="self-start bg-yellow-500 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50">
                  Guardar nota interna
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions footer */}
        <div className="border-t bg-gray-50 p-4 flex flex-col gap-2 shrink-0">
          {/* Escribir al cliente: nunca cambia el estado */}
          {!showWrite ? (
            <div className="flex gap-2">
              <button
                onClick={() => openWrite()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-white text-sm"
                style={{ backgroundColor: '#25D366' }}
              >
                <MessageCircle size={16} /> Escribir al cliente
              </button>
              <select
                value={waMode}
                onChange={(e) => changeWaMode(e.target.value as WhatsAppMode)}
                className="rounded-xl border border-gray-200 bg-white px-2 text-xs text-gray-600"
                title="Dónde abrir WhatsApp"
              >
                <option value="web">WhatsApp Web (1 pestaña)</option>
                <option value="app">App de escritorio</option>
              </select>
            </div>
          ) : (
            <div className="rounded-xl border border-green-200 bg-white p-3 flex flex-col gap-2">
              <div className="flex flex-wrap gap-1.5">
                {templates.map((t) => (
                  <button
                    key={t.key}
                    onClick={() => setWriteText(t.text)}
                    className="rounded-full border border-gray-200 px-2.5 py-1 text-xs hover:bg-green-50"
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              <textarea
                value={writeText}
                onChange={(e) => setWriteText(e.target.value)}
                rows={5}
                className="rounded-lg border border-gray-200 p-2 text-sm resize-y focus:outline-none focus:ring-2 focus:ring-green-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={() => sendWhatsApp(writeText)}
                  disabled={!writeText.trim()}
                  className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-green-500 text-white text-sm font-bold disabled:opacity-50"
                >
                  <Send size={14} /> Abrir en WhatsApp
                </button>
                <button
                  onClick={async () => {
                    const ok = await copyText(writeText);
                    if (ok) toast.success('Mensaje copiado 📋'); else toast.error('No se pudo copiar');
                  }}
                  className="flex items-center gap-1 px-3 py-2 rounded-lg border border-gray-200 text-sm"
                >
                  <Copy size={14} /> Copiar
                </button>
                <button onClick={() => setShowWrite(false)} className="px-2 text-xs text-gray-500 underline">Cerrar</button>
              </div>
              <p className="text-[11px] text-gray-400">Escribirle no cambia el estado del pedido. El mensaje también queda copiado por si WhatsApp no abre.</p>
            </div>
          )}

          {/* Aprobación del cliente (ya se habló con él) */}
          {canApprove && (
            <div className="flex gap-2">
              <button
                onClick={() => approvalMut.mutate(approvalChannel)}
                disabled={busy}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-white text-sm bg-teal-600 disabled:opacity-50"
              >
                <UserCheck size={16} /> Cliente aprobó → listo p/facturar
              </button>
              <select
                value={approvalChannel}
                onChange={(e) => setApprovalChannel(e.target.value)}
                className="rounded-xl border border-gray-200 bg-white px-2 text-xs text-gray-600"
                title="¿Cómo aprobó?"
              >
                <option value="phone_call">por llamada</option>
                <option value="whatsapp_replied">por WhatsApp</option>
                <option value="in_store">en la tienda</option>
              </select>
            </div>
          )}

          {/* Avance normal */}
          {nextOptions.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {nextOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    // Solo un pedido PAGADO EN LÍNEA puede acabar en contracargo, y
                    // el único instante en que se puede recoger la evidencia es este.
                    // En los de contraentrega no se pregunta nada: no hay disputa
                    // posible y estorbar ahí sería frenar por frenar.
                    if (opt.value === 'delivered' && order.payment_status === 'paid') {
                      setPidiendoEvidencia(true);
                    } else {
                      workflowMut.mutate({ status: opt.value });
                    }
                  }}
                  disabled={busy}
                  className="flex-1 py-2 rounded-xl border-2 border-teal-600 text-teal-700 font-semibold text-sm hover:bg-teal-50 transition-colors disabled:opacity-50"
                >
                  {opt.value === 'under_review' && ws === 'awaiting_customer' ? <Undo2 size={13} className="inline mr-1" /> : null}
                  {opt.label} <ChevronRight size={13} className="inline" />
                </button>
              ))}
            </div>
          )}

          {/* Cancelar */}
          {canCancel && !showCancel && (
            <button onClick={() => setShowCancel(true)}
              className="text-xs text-red-500 underline self-center mt-1">
              Cancelar pedido
            </button>
          )}
          {showCancel && (
            <div className="flex flex-col gap-1">
              <div className="flex gap-2 items-center">
                <input
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder="Motivo de cancelación..."
                  className="flex-1 rounded-lg border border-red-200 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-red-400"
                />
                <button onClick={() => cancelMut.mutate()} disabled={!cancelReason || cancelMut.isPending}
                  className="bg-red-500 text-white rounded-lg px-3 py-1.5 text-sm font-semibold disabled:opacity-50 flex items-center gap-1">
                  <XCircle size={13} /> Cancelar
                </button>
              </div>
              {order.sales_order_id && (
                <p className="text-[11px] text-red-600">Ya está facturado: al cancelar se anula la venta y el inventario vuelve a la tienda.</p>
              )}
            </div>
          )}
        </div>
      </div>

      {pidiendoEvidencia && (
        <ModalEvidencia
          cliente={order.customer_name}
          onCancelar={() => setPidiendoEvidencia(false)}
          onConfirmar={(evidencia) => {
            setPidiendoEvidencia(false);
            workflowMut.mutate({ status: 'delivered', evidencia });
          }}
        />
      )}

      {/* Modal notificación WhatsApp */}
      {pendingNotif && (
        <WhatsAppNotifModal
          notif={pendingNotif}
          phone={order.customer_phone}
          onClose={() => setPendingNotif(null)}
        />
      )}

      <ProductPickerModal
        open={!!substitutingItemId}
        onClose={() => setSubstitutingItemId(null)}
        title="Sustituir por…"
        onSelect={(product) => substitutingItemId && substituteMut.mutate({ itemId: substitutingItemId, product })}
      />
      <ProductPickerModal
        open={showAddProduct}
        onClose={() => setShowAddProduct(false)}
        title="Agregar producto al pedido"
        onSelect={(product) => addItemMut.mutate(product)}
      />
    </>
  );
}


// ── Modal WhatsApp pre-armado ─────────────────────────────────────────────────

function WhatsAppNotifModal({
  notif,
  phone,
  onClose,
}: {
  notif: PendingNotification;
  phone: string | null;
  onClose: () => void;
}) {
  const qc = useQueryClient();

  const sentMut = useMutation({
    mutationFn: () => adminPortal.markNotificationSent(notif.id),
    onSuccess: () => {
      toast.success('Mensaje marcado como enviado ✅');
      qc.invalidateQueries({ queryKey: ['pending-notifs'] });
      onClose();
    },
  });

  const skipMut = useMutation({
    mutationFn: () => adminPortal.skipNotification(notif.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-notifs'] });
      onClose();
    },
  });

  function copyMessage() {
    copyText(notif.rendered_message).then((ok) =>
      ok ? toast.success('Mensaje copiado al portapapeles 📋') : toast.error('No se pudo copiar'),
    );
  }

  const TEMPLATE_LABELS: Record<string, string> = {
    order_received: '📥 Pedido recibido',
    changes_to_confirm: '⚠️ Cambios para confirmar',
    order_invoiced: '🧾 Facturado',
    ready_for_delivery: '🚚 En camino',
    delivered_with_review_cta: '⭐ Entregado + Calificar',
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-[60] flex items-end sm:items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-2xl flex flex-col gap-0 overflow-hidden">
        {/* Header */}
        <div className="bg-green-600 px-5 py-4 flex items-center justify-between">
          <div>
            <p className="text-white font-bold text-base flex items-center gap-2">
              <MessageCircle size={18} /> Envía este mensaje al cliente
            </p>
            <p className="text-green-100 text-xs mt-0.5">
              {TEMPLATE_LABELS[notif.template_code] ?? notif.template_code}
              {notif.customer_name && ` · ${notif.customer_name}`}
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-full hover:bg-green-700">
            <X size={18} className="text-white" />
          </button>
        </div>

        {/* Message preview */}
        <div className="p-4 bg-gray-50 border-b">
          <pre className="text-sm text-gray-800 whitespace-pre-wrap font-sans leading-relaxed max-h-56 overflow-y-auto">
            {notif.rendered_message}
          </pre>
        </div>

        {/* Action buttons */}
        <div className="p-4 flex gap-2">
          <button
            onClick={copyMessage}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl border border-gray-200 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
          >
            <Copy size={15} /> Copiar
          </button>
          <button
            onClick={() => { openWhatsApp(phone ?? notif.customer_phone ?? null, notif.rendered_message); copyText(notif.rendered_message); }}
            className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-xl bg-green-500 text-white text-sm font-semibold hover:bg-green-600 transition-colors"
          >
            <Send size={15} /> Abrir WhatsApp
          </button>
        </div>

        {/* Confirm or skip */}
        <div className="px-4 pb-4 flex gap-2 border-t pt-3">
          <p className="text-xs text-gray-500 self-center flex-1">Después de enviar:</p>
          <button
            onClick={() => sentMut.mutate()}
            disabled={sentMut.isPending}
            className="flex items-center gap-1 px-3 py-2 rounded-xl bg-teal-600 text-white text-xs font-bold hover:bg-teal-700 disabled:opacity-50 transition-colors"
          >
            <CheckCircle2 size={13} /> Ya lo envié
          </button>
          <button
            onClick={() => skipMut.mutate()}
            disabled={skipMut.isPending}
            className="flex items-center gap-1 px-3 py-2 rounded-xl bg-gray-100 text-gray-600 text-xs font-bold hover:bg-gray-200 disabled:opacity-50 transition-colors"
          >
            <SkipForward size={13} /> Saltar
          </button>
        </div>
      </div>
    </div>
  );
}


function formatAction(action: string): string {
  const map: Record<string, string> = {
    created: '🆕 Pedido creado',
    status_changed: '🔄 Estado cambiado',
    item_quantity_changed: '✏️ Cantidad modificada',
    item_price_changed: '💲 Precio ajustado',
    item_substituted: '↔️ Producto sustituido',
    item_added: '➕ Producto agregado',
    item_removed: '❌ Producto removido',
    discount_applied: '💰 Descuento aplicado',
    address_changed: '📍 Dirección cambiada',
    notes_updated: '📝 Nota actualizada',
    customer_confirmed_via_whatsapp_replied: '✅ Cliente aprobó (WhatsApp)',
    customer_confirmed_via_phone_call: '✅ Cliente aprobó (llamada)',
    customer_confirmed_via_in_store: '✅ Cliente aprobó (en tienda)',
    customer_confirmed_via_portal: '✅ Cliente aprobó (desde el portal)',
    cancelled: '🚫 Pedido cancelado',
  };
  return map[action] ?? action.replace(/_/g, ' ');
}


// ─────────────────────────────────────────────────────────────────────────────
// Antifraude (8-oct-2026)
// ─────────────────────────────────────────────────────────────────────────────

/** El semáforo del pedido, con el motivo escrito y el botón para liberarlo.
 *
 * Muestra POR QUÉ está marcado, no solo que lo está: un aviso sin razón se ignora
 * la segunda vez. Y el botón pide una nota obligatoria, porque el valor real de
 * haber llamado al cliente aparece después —en una disputa— y solo si quedó escrito.
 */
function BanderaRiesgo({
  order, nota, setNota, onLiberar, liberando,
}: {
  order: PortalOrderDetail;
  nota: string;
  setNota: (v: string) => void;
  onLiberar: () => void;
  liberando: boolean;
}) {
  const alto = order.risk_level === 'alto';
  const liberado = !!order.risk_cleared_at;
  const motivos = (order.risk_flags ?? []).filter((f) => f.puntos > 0);

  if (liberado) {
    return (
      <div className="flex items-start gap-2 px-4 py-2 bg-green-50 border-b border-green-100 text-green-800 text-xs shrink-0">
        <ShieldCheck size={15} className="mt-0.5 shrink-0" />
        <span>
          <strong>Verificado por {order.risk_cleared_by}</strong>
          {order.risk_cleared_note ? ` — ${order.risk_cleared_note}` : ''}. Se puede entregar.
        </span>
      </div>
    );
  }

  return (
    <div className={`px-4 py-3 border-b shrink-0 ${alto ? 'bg-red-50 border-red-200' : 'bg-amber-50 border-amber-200'}`}>
      <div className="flex items-start gap-2">
        <ShieldAlert size={16} className={`mt-0.5 shrink-0 ${alto ? 'text-red-600' : 'text-amber-600'}`} />
        <div className="min-w-0 flex-1">
          <p className={`text-sm font-bold ${alto ? 'text-red-800' : 'text-amber-800'}`}>
            {alto
              ? 'Pago de riesgo ALTO — llama al cliente antes de entregar'
              : 'Pago para mirar antes de despachar'}
          </p>
          <ul className={`mt-1 space-y-0.5 text-xs ${alto ? 'text-red-700' : 'text-amber-700'}`}>
            {motivos.map((m) => <li key={m.codigo}>• {m.texto}</li>)}
          </ul>
          {order.bold_masked_pan && (
            <p className="mt-1.5 font-mono text-[11px] text-gray-500">
              {order.bold_card_brand} {order.bold_masked_pan}
              {order.bold_payer_email ? ` · ${order.bold_payer_email}` : ''}
            </p>
          )}

          {/* El rojo pide la nota; el amarillo es solo informativo y no estorba. */}
          {alto && (
            <div className="mt-2 flex flex-wrap items-center gap-2">
              <input
                value={nota}
                onChange={(e) => setNota(e.target.value)}
                placeholder="¿Qué verificaste? Ej: llamé al 300… y confirmó"
                className="flex-1 min-w-[180px] rounded-lg border border-red-200 px-2.5 py-1.5 text-xs"
              />
              <button
                onClick={onLiberar}
                disabled={nota.trim().length < 3 || liberando}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-bold text-white disabled:opacity-50"
              >
                {liberando ? 'Guardando…' : 'Verifiqué, liberar'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

/** Pide el expediente de entrega de un pedido pagado en línea.
 *
 * Bold dice textualmente qué gana una disputa: "guías de envío, fotos del producto
 * recibido por el cliente, soportes de entrega". Y da **2 días hábiles** para
 * mandarlo. Recogerlo después es imposible: nadie recuerda quién abrió la puerta.
 *
 * Solo el nombre de quien recibe es obligatorio —tres segundos— porque un formulario
 * largo en el momento de entregar no se llena: se salta.
 */
function ModalEvidencia({
  cliente, onCancelar, onConfirmar,
}: {
  cliente: string | null;
  onCancelar: () => void;
  onConfirmar: (e: DeliveryEvidence) => void;
}) {
  const [nombre, setNombre] = useState(cliente ?? '');
  const [documento, setDocumento] = useState('');
  const [notas, setNotas] = useState('');

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 p-4"
      onClick={onCancelar}>
      <div className="w-full max-w-sm rounded-2xl bg-white p-5 shadow-2xl"
        onClick={(e) => e.stopPropagation()}>
        <h3 className="font-bold text-gray-900">¿Quién recibió el pedido?</h3>
        <p className="mt-1 text-xs text-gray-500">
          Este pedido se pagó en línea. Si el cliente desconoce el cobro, esto es lo
          único con lo que se puede pelear la disputa.
        </p>

        <label className="mt-4 block text-xs font-semibold text-gray-700">Nombre de quien recibe</label>
        <input
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          placeholder="Nombre completo"
          className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
          autoFocus
        />

        <label className="mt-3 block text-xs font-semibold text-gray-700">
          Cédula <span className="font-normal text-gray-400">(opcional, pero ayuda)</span>
        </label>
        <input
          value={documento}
          onChange={(e) => setDocumento(e.target.value)}
          inputMode="numeric"
          className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
        />

        <label className="mt-3 block text-xs font-semibold text-gray-700">
          Nota <span className="font-normal text-gray-400">(opcional)</span>
        </label>
        <input
          value={notas}
          onChange={(e) => setNotas(e.target.value)}
          placeholder="Ej: lo recibió la mamá en la portería"
          className="mt-1 w-full rounded-xl border border-gray-200 px-3 py-2 text-sm"
        />

        <div className="mt-5 flex gap-2">
          <button onClick={onCancelar}
            className="flex-1 rounded-xl border border-gray-200 py-2 text-sm font-semibold text-gray-600">
            Cancelar
          </button>
          <button
            onClick={() => onConfirmar({
              delivered_to_name: nombre.trim() || undefined,
              delivered_to_doc: documento.trim() || undefined,
              delivery_notes: notas.trim() || undefined,
            })}
            disabled={nombre.trim().length < 2}
            className="flex-1 rounded-xl bg-teal-600 py-2 text-sm font-bold text-white disabled:opacity-50"
          >
            Marcar entregado
          </button>
        </div>
      </div>
    </div>
  );
}
