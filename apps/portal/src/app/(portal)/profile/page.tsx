'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { LogOut, Star, ChevronRight, LifeBuoy, ShoppingBag, CalendarClock } from 'lucide-react';
import { auth, portalLocation } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { PageHeader } from '@/components/ui/page-header';
import { cn } from '@/lib/utils';

const PREF_ITEMS = [
  { key: 'sos' as const, icon: LifeBuoy, label: 'Alertas de SOS', desc: 'Mascotas perdidas cerca de ti' },
  { key: 'promos' as const, icon: ShoppingBag, label: 'Promociones', desc: 'Ofertas y descuentos' },
  { key: 'appointments' as const, icon: CalendarClock, label: 'Recordatorios de citas', desc: 'Vacunas, baños, consultas' },
];

export default function ProfilePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { customer, clear, setCustomer } = useAuthStore();
  const [loggingOut, setLoggingOut] = useState(false);

  const { mutate: togglePref, isPending: savingPref } = useMutation({
    mutationFn: (data: { sos?: boolean; promos?: boolean; appointments?: boolean }) =>
      portalLocation.updatePreferences(data),
    onSuccess: (res) => {
      if (customer) setCustomer({ ...customer, notification_prefs: res.notification_prefs });
      qc.invalidateQueries({ queryKey: ['portal-me'] });
    },
    onError: () => toast.error('No se pudo guardar el cambio'),
  });

  async function handleLogout() {
    setLoggingOut(true);
    try {
      await auth.logout();
    } catch {}
    clear();
    qc.clear();
    router.replace('/login');
  }

  const prefs = customer?.notification_prefs ?? {};

  return (
    <div className="p-4 pt-6 flex flex-col gap-5">
      <PageHeader title="Mi perfil" />

      {/* Avatar */}
      <div className="card flex items-center gap-4 py-4">
        <div
          className="h-16 w-16 rounded-2xl flex items-center justify-center text-white font-bold text-2xl shadow-sm"
          style={{ background: 'linear-gradient(135deg, #187f77, #085041)' }}
        >
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

      {/* Preferencias de notificación */}
      <div>
        <p className="text-xs font-semibold text-muted uppercase tracking-wide mb-2 px-1">
          Notificaciones
        </p>
        <div className="card flex flex-col divide-y divide-border">
          {PREF_ITEMS.map(({ key, icon: Icon, label, desc }) => {
            const enabled = prefs[key] !== false; // default true si no está definido
            return (
              <div key={key} className="flex items-center gap-3 py-3">
                <div className="h-9 w-9 rounded-xl bg-primary-50 flex items-center justify-center shrink-0">
                  <Icon className="h-4 w-4 text-primary-700" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-foreground">{label}</p>
                  <p className="text-xs text-muted">{desc}</p>
                </div>
                <button
                  role="switch"
                  aria-checked={enabled}
                  disabled={savingPref}
                  onClick={() => togglePref({ [key]: !enabled })}
                  className={cn(
                    'relative h-6 w-11 rounded-full transition-colors shrink-0 disabled:opacity-60',
                    enabled ? 'bg-primary-700' : 'bg-gray-200'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-0.5 h-5 w-5 rounded-full bg-white shadow transition-transform',
                      enabled ? 'translate-x-[22px]' : 'translate-x-0.5'
                    )}
                  />
                </button>
              </div>
            );
          })}
        </div>
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
