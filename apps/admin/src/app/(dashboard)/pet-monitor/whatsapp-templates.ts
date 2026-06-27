import type { PortalOrderDetail } from '@/lib/api';

export type TemplateKey =
  | 'order_received'
  | 'changes_to_confirm'
  | 'order_invoiced'
  | 'ready_for_delivery'
  | 'delivered';

export interface Template {
  key: TemplateKey;
  label: string;
  build: (order: PortalOrderDetail) => string;
}

function firstName(order: PortalOrderDetail) {
  return order.customer_name?.split(' ')[0] ?? 'cliente';
}

function itemsList(order: PortalOrderDetail) {
  return order.items
    .filter((i) => !i.is_substituted || i.substituted_from_name)
    .map((i) => {
      const sub = i.is_substituted ? ` (antes: ${i.substituted_from_name})` : '';
      return `• ${i.name}${sub} x${i.quantity} — $${(i.subtotal || 0).toLocaleString('es-CO')}`;
    })
    .join('\n');
}

function totalsLine(order: PortalOrderDetail) {
  const lines = [];
  if (order.discount_amount > 0)
    lines.push(`Descuento: -$${order.discount_amount.toLocaleString('es-CO')}`);
  lines.push(`Envío: ${order.shipping === 0 ? 'Gratis 🎉' : '$' + order.shipping.toLocaleString('es-CO')}`);
  lines.push(`*TOTAL: $${order.total.toLocaleString('es-CO')}*`);
  return lines.join('\n');
}

export const TEMPLATES: Template[] = [
  {
    key: 'order_received',
    label: '📥 Pedido recibido',
    build: (o) =>
      `Hola ${firstName(o)}! 🐾 Recibimos tu pedido en Bigotes y Paticas.\n\n${itemsList(o)}\n\n${totalsLine(o)}\n\nEstamos revisando disponibilidad. Te avisamos pronto!`,
  },
  {
    key: 'changes_to_confirm',
    label: '⚠️ Cambios — confirmar',
    build: (o) => {
      const note = o.customer_facing_notes ? `\n\n📌 ${o.customer_facing_notes}` : '';
      return `Hola ${firstName(o)}! Revisamos tu pedido y hay cambios 🐾\n\n${itemsList(o)}\n\n${totalsLine(o)}${note}\n\nPor favor responde *SÍ* para confirmar o dinos si tienes alguna duda.`;
    },
  },
  {
    key: 'order_invoiced',
    label: '🧾 Facturado',
    build: (o) =>
      `Hola ${firstName(o)}! Tu pedido fue facturado ✅ y está siendo preparado con todo el amor 🐾\n\nPago: ${o.payment_method ?? 'pendiente'}\n\nTe avisamos cuando salga a domicilio!`,
  },
  {
    key: 'ready_for_delivery',
    label: '🚚 En camino',
    build: (o) =>
      `Hola ${firstName(o)}! Tu pedido ya está en camino 🚚🐾\n\nDirección: ${o.shipping_address ?? 'pendiente'}\n\nEstaremos pronto por allá!`,
  },
  {
    key: 'delivered',
    label: '✅ Entregado',
    build: (o) =>
      `Hola ${firstName(o)}! Tu pedido fue entregado ✅🐾 Esperamos que ${firstName(o)} y su mascota estén felices!\n\nSi tienes algún inconveniente avísanos. Gracias por preferirnos!`,
  },
];
