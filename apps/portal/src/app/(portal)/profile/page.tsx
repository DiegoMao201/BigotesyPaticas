'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { LogOut, Star, ChevronRight } from 'lucide-react';
import { auth } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

export default function ProfilePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { customer, clear } = useAuthStore();
  const [loggingOut, setLoggingOut] = useState(false);

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await auth.logout();
    } catch {}
    clear();
    qc.clear();
    router.replace('/login');
  }

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <h1 className="font-display text-2xl font-bold text-foreground">Mi perfil</h1>

      {/* Avatar */}
      <div className="card flex items-center gap-4 py-4">
        <div className="h-16 w-16 rounded-2xl bg-primary-700 flex items-center justify-center text-white font-bold text-2xl">
          {customer?.full_name?.[0]?.toUpperCase() ?? '?'}
        </div>
        <div>
          <p className="font-display font-bold text-foreground text-lg">
            {customer?.full_name || 'Sin nombre'}
          </p>
          <p className="text-sm text-muted">{customer?.phone ?? ''}</p>
          {customer?.rfm_segment && (
            <span className="inline-flex items-center gap-1 text-xs font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full mt-1">
              <Star className="h-3 w-3 fill-amber-500 text-amber-500" />
              {customer.rfm_segment}
            </span>
          )}
        </div>
      </div>

      {/* Info */}
      <div className="card flex flex-col divide-y divide-border">
        {[
          { label: 'Cédula', value: customer?.document_id },
          { label: 'Email', value: customer?.email },
          { label: 'Teléfono', value: customer?.phone },
          { label: 'Ciudad', value: customer?.city },
          { label: 'Dirección', value: customer?.address },
        ].map(({ label, value }) => (
          <div key={label} className="flex items-center justify-between py-3">
            <span className="text-sm text-muted">{label}</span>
            <span className="text-sm font-medium text-foreground">{value || '—'}</span>
          </div>
        ))}
      </div>

      {/* Links */}
      <div className="card flex flex-col divide-y divide-border">
        <a
          href={`https://wa.me/573206876633?text=${encodeURIComponent('Hola! Necesito ayuda con mi portal de Bigotes y Paticas.')}`}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-between py-3"
        >
          <span className="text-sm font-medium">Soporte por WhatsApp</span>
          <ChevronRight className="h-4 w-4 text-muted" />
        </a>
      </div>

      {/* Logout */}
      <button
        onClick={handleLogout}
        disabled={loggingOut}
        className="flex items-center justify-center gap-2 py-3 rounded-xl border-2 border-red-200 text-red-600 font-semibold text-sm hover:bg-red-50 transition-colors active:scale-95"
      >
        <LogOut className="h-4 w-4" />
        {loggingOut ? 'Cerrando sesión...' : 'Cerrar sesión'}
      </button>
    </div>
  );
}
