'use client';

import { MessageCircle } from 'lucide-react';
import { WHATSAPP_NUMBER } from '@/lib/utils';

interface WhatsAppButtonProps {
  message?: string;
  className?: string;
}

export function WhatsAppButton({
  message = '¡Hola! Te escribo desde el portal de Bigotes y Paticas.',
  className,
}: WhatsAppButtonProps) {
  const href = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;

  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Contactar por WhatsApp"
      className={`fixed bottom-20 right-4 z-50 flex h-14 w-14 items-center justify-center
                  rounded-full bg-[#25D366] shadow-lg shadow-green-500/30
                  transition-transform active:scale-90 hover:scale-105 ${className ?? ''}`}
    >
      <MessageCircle className="h-7 w-7 fill-white text-white" />
    </a>
  );
}
