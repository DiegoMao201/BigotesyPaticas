'use client';

import { useState } from 'react';
import { X, MessageCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { type Customer } from '@/lib/api';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';

function buildTemplate(customer: Customer): string {
  const firstName = customer.full_name?.split(' ')[0] ?? 'amigo';
  const petName = customer.pet_name ?? 'tu mascota';
  const referralCode = customer.referral_code ?? '';
  const referralUrl = referralCode
    ? `https://mi.bigotesypaticas.com/?ref=${referralCode}`
    : 'https://mi.bigotesypaticas.com/registro';

  return `¡Hola ${firstName}! 🐾

Soy de Bigotes y Paticas. ¡Tenemos novedades para ti!

Creamos una App exclusiva para nuestros clientes donde puedes:

✨ Llevar el carnet digital de ${petName}
✨ Pedir a domicilio en 1 clic
✨ Ganar puntos en cada compra (1 punto = $1.000)
✨ Recibir recordatorios de vacunas y desparasitación
✨ Ver tu historial completo de compras

Te regalamos 100 Puntos Bigotes solo por registrarte (= $100 de descuento).

👉 ${referralUrl}

Si nos quieres calificar en Google mientras tanto: ${GOOGLE_REVIEW_URL}

¡Cuidamos a quien te cuida! 🐶🐱`;
}

interface Props {
  customer: Customer;
  open: boolean;
  onClose: () => void;
}

export function InviteToPortalModal({ customer, open, onClose }: Props) {
  const [message, setMessage] = useState(() => buildTemplate(customer));

  if (!open) return null;

  function openWhatsApp() {
    const phone = customer.phone?.replace(/\D/g, '') ?? '';
    const encoded = encodeURIComponent(message);
    const url = phone
      ? `https://wa.me/${phone.startsWith('57') ? phone : `57${phone}`}?text=${encoded}`
      : `https://wa.me/?text=${encoded}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/50 z-40" onClick={onClose} />
      <div className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 bg-white rounded-2xl shadow-2xl p-6 max-w-lg w-[95%] z-50">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-bold text-lg">📨 Invitar al portal</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
            <X size={20} />
          </button>
        </div>

        <p className="text-sm text-gray-500 mb-3">
          Cliente: <strong>{customer.full_name}</strong>
          {customer.phone && <span> · {customer.phone}</span>}
        </p>

        <label className="text-xs font-medium text-gray-600 mb-1 block">
          Mensaje (editable):
        </label>
        <textarea
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={14}
          className="w-full rounded-xl border border-gray-200 p-3 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-teal-500 font-mono leading-relaxed mb-4"
        />

        <div className="flex gap-3">
          <Button
            onClick={openWhatsApp}
            className="flex-1 bg-[#25D366] hover:bg-[#20b358] text-white font-bold gap-2"
          >
            <MessageCircle className="h-4 w-4" />
            Abrir WhatsApp con mensaje
          </Button>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
        </div>
      </div>
    </>
  );
}
