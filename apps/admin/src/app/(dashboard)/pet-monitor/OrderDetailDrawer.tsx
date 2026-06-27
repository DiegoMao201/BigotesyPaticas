'use client';

import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useMutation, useQuery } from '@tanstack/react-query';
import { toast } from 'sonner';
import {
  X, ChevronRight, MessageCircle, Package, MapPin,
  StickyNote, Percent, UserCheck, XCircle, Clock,
  CheckCircle2, AlertCircle,
} from 'lucide-react';
import { adminPortal, type PortalOrderDetail, type ActivityLogEntry } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

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

const NEXT_STATUS: Record<string, { value: string; label: string }[]> = {
  received:           [{ value: 'under_review', label: 'Marcar en revisión' }],
  under_review:       [{ value: 'awaiting_customer', label: 'Enviar a cliente (cambios)' }, { value: 'ready_to_invoice', label: 'Aprobar — listo p/facturar' }],
  awaiting_customer:  [{ value: 'ready_to_invoice', label: 'Cliente aprobó (listo p/facturar)' }],
  ready_to_invoice:   [{ value: 'invoiced', label: 'Marcar facturado' }],
  invoiced:           [{ value: 'in_preparation', label: 'Iniciar preparación' }],
  in_preparation:     [{ value: 'ready_for_delivery', label: 'Listo para entrega' }],
  ready_for_delivery: [{ value: 'in_transit', label: 'Enviado a domicilio' }],
  in_transit:         [{ value: 'delivered', label: 'Marcar entregado' }],
};

interface Props {
  orderId: string;
  onClose: () => void;
  onRefreshList: () => void;
}

export function OrderDetailDrawer({ orderId, onClose, onRefreshList }: Props) {
  const qc = useQueryClient();
  const [tab, setTab] = useState<'items' | 'activity' | 'notes'>('items');
  const [cancelReason, setCancelReason] = useState('');
  const [showCancel, setShowCancel] = useState(false);
  const [customerNoteText, setCustomerNoteText] = useState('');
  const [discountAmount, setDiscountAmount] = useState('');
  const [discountReason, setDiscountReason] = useState('');
  const [showDiscount, setShowDiscount] = useState(false);

  const { data: order, isLoading } = useQuery({
    queryKey: ['portal-order-detail', orderId],
    queryFn: () => adminPortal.orderDetail(orderId),
  });

  const { data: activity = [] } = useQuery({
    queryKey: ['portal-order-activity', orderId],
    queryFn: () => adminPortal.orderActivity(orderId),
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['portal-order-detail', orderId] });
    qc.invalidateQueries({ queryKey: ['portal-order-activity', orderId] });
    onRefreshList();
  };

  const workflowMut = useMutation({
    mutationFn: ({ status, notes }: { status: string; notes?: string }) =>
      adminPortal.changeWorkflow(orderId, status, notes),
    onSuccess: (d) => { toast.success(`Estado → ${WORKFLOW_LABELS[d.workflow_status]?.label ?? d.workflow_status}`); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const cancelMut = useMutation({
    mutationFn: () => adminPortal.cancelOrder(orderId, cancelReason),
    onSuccess: () => { toast.success('Pedido cancelado'); setShowCancel(false); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const discountMut = useMutation({
    mutationFn: () => adminPortal.applyDiscount(orderId, parseFloat(discountAmount), discountReason),
    onSuccess: () => { toast.success('Descuento aplicado'); setShowDiscount(false); invalidate(); },
    onError: (e: Error) => toast.error(e.message),
  });

  const notesMut = useMutation({
    mutationFn: () => adminPortal.updateNotes(orderId, { customer_facing_notes: customerNoteText }),
    onSuccess: () => { toast.success('Nota guardada'); setCustomerNoteText(''); invalidate(); },
  });

  const markSentMut = useMutation({
    mutationFn: () => adminPortal.markNotifSent(orderId),
    onSuccess: () => { toast.success('Notificación marcada como enviada'); invalidate(); },
  });

  const approvalMut = useMutation({
    mutationFn: () => adminPortal.confirmApproval(orderId, 'whatsapp_replied'),
    onSuccess: (d) => { toast.success('Aprobación confirmada — listo p/facturar'); invalidate(); },
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

  const whatsappMsg = () => {
    const phone = order.customer_phone?.replace(/\D/g, '') ?? '';
    const items = order.items.map((i) => `• ${i.name} x${i.quantity} — $${(i.subtotal || 0).toLocaleString('es-CO')}`).join('\n');
    const discount = order.discount_amount > 0 ? `\nDescuento: -$${order.discount_amount.toLocaleString('es-CO')}` : '';
    const msg = `Hola ${order.customer_name?.split(' ')[0] ?? ''}! Revisamos tu pedido 🐾\n\n${items}${discount}\n\nEnvío: $${order.shipping.toLocaleString('es-CO')}\n*Total: $${order.total.toLocaleString('es-CO')}*\n\n${order.customer_facing_notes ? order.customer_facing_notes + '\n\n' : ''}¿Confirmas el pedido?`;
    const url = phone
      ? `https://wa.me/${phone.startsWith('57') ? phone : `57${phone}`}?text=${encodeURIComponent(msg)}`
      : `https://wa.me/?text=${encodeURIComponent(msg)}`;
    return url;
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-white z-50 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b bg-gray-50 shrink-0">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Pedido portal</p>
            <h2 className="font-bold text-gray-900">{order.customer_name ?? 'Cliente'}</h2>
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
              {t === 'items' ? '📦 Items' : t === 'activity' ? '🕐 Actividad' : '📝 Notas'}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-3">
          {tab === 'items' && (
            <>
              {order.shipping_address && (
                <div className="flex items-start gap-2 bg-gray-50 rounded-xl p-3 text-sm">
                  <MapPin size={14} className="text-gray-400 mt-0.5 shrink-0" />
                  <span className="text-gray-700">{order.shipping_address}</span>
                </div>
              )}
              {order.items.map((item) => (
                <div key={item.id} className={`flex items-center gap-3 bg-white border rounded-xl p-3 ${item.is_substituted ? 'border-amber-200 bg-amber-50' : 'border-gray-100'}`}>
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
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-gray-500">x{item.quantity}</p>
                    <p className="text-sm font-bold text-gray-900">{formatCurrency(item.subtotal)}</p>
                  </div>
                </div>
              ))}

              {/* Discount section */}
              {!showDiscount ? (
                <button onClick={() => setShowDiscount(true)} className="text-sm text-teal-700 underline flex items-center gap-1 self-start">
                  <Percent size={13} /> Aplicar descuento
                </button>
              ) : (
                <div className="bg-gray-50 rounded-xl p-3 flex flex-col gap-2">
                  <div className="flex gap-2">
                    <input
                      type="number"
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
                  <div className="flex gap-2">
                    <button onClick={() => discountMut.mutate()} disabled={!discountAmount || !discountReason || discountMut.isPending}
                      className="bg-teal-600 text-white rounded-lg px-3 py-1.5 text-sm font-semibold disabled:opacity-50">
                      Aplicar
                    </button>
                    <button onClick={() => setShowDiscount(false)} className="text-sm text-gray-500 underline">Cancelar</button>
                  </div>
                </div>
              )}
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
                      <p className="text-xs text-green-600">Enviado por {log.notification_sent_at}</p>
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
                  <p className="text-xs font-semibold text-blue-800 mb-1">👤 Nota al cliente</p>
                  <p className="text-sm text-blue-900">{order.customer_facing_notes}</p>
                </div>
              )}
              <div className="flex flex-col gap-2">
                <textarea
                  value={customerNoteText}
                  onChange={(e) => setCustomerNoteText(e.target.value)}
                  placeholder="Agregar nota visible para el cliente..."
                  rows={3}
                  className="rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
                <button onClick={() => notesMut.mutate()} disabled={!customerNoteText || notesMut.isPending}
                  className="self-start bg-teal-600 text-white rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50">
                  Guardar nota
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions footer */}
        <div className="border-t bg-gray-50 p-4 flex flex-col gap-2 shrink-0">
          {/* WhatsApp — always visible */}
          <a
            href={whatsappMsg()}
            target="_blank"
            rel="noopener noreferrer"
            onClick={() => { if (isAwaiting) markSentMut.mutate(); }}
            className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-white text-sm"
            style={{ backgroundColor: '#25D366' }}
          >
            <MessageCircle size={16} />
            {isAwaiting ? 'Enviar resumen por WhatsApp (marcar enviado)' : 'WhatsApp al cliente'}
          </a>

          {/* Awaiting: confirm approval */}
          {isAwaiting && (
            <button
              onClick={() => approvalMut.mutate()}
              disabled={approvalMut.isPending}
              className="flex items-center justify-center gap-2 py-2.5 rounded-xl font-bold text-white text-sm bg-teal-600 disabled:opacity-50"
            >
              <UserCheck size={16} />
              Cliente aprobó los cambios → listo p/facturar
            </button>
          )}

          {/* Next workflow statuses */}
          <div className="flex flex-wrap gap-2">
            {nextOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => workflowMut.mutate({ status: opt.value })}
                disabled={workflowMut.isPending}
                className="flex-1 py-2 rounded-xl border-2 border-teal-600 text-teal-700 font-semibold text-sm hover:bg-teal-50 transition-colors disabled:opacity-50"
              >
                {opt.label} <ChevronRight size={13} className="inline" />
              </button>
            ))}
          </div>

          {/* Cancel */}
          {canCancel && !showCancel && (
            <button onClick={() => setShowCancel(true)}
              className="text-xs text-red-500 underline self-center mt-1">
              Cancelar pedido
            </button>
          )}
          {showCancel && (
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
          )}
        </div>
      </div>
    </>
  );
}

function formatAction(action: string): string {
  const map: Record<string, string> = {
    created: '🆕 Pedido creado',
    status_changed: '🔄 Estado cambiado',
    item_quantity_changed: '✏️ Cantidad modificada',
    item_substituted: '↔️ Producto sustituido',
    item_added: '➕ Producto agregado',
    item_removed: '❌ Producto removido',
    discount_applied: '💰 Descuento aplicado',
    address_changed: '📍 Dirección cambiada',
    notes_updated: '📝 Nota actualizada',
    customer_confirmed_via_whatsapp_replied: '✅ Cliente aprobó (WhatsApp)',
    customer_confirmed_via_phone_call: '✅ Cliente aprobó (llamada)',
    customer_confirmed_via_in_store: '✅ Cliente aprobó (en tienda)',
    cancelled: '🚫 Pedido cancelado',
  };
  return map[action] ?? action.replace(/_/g, ' ');
}
