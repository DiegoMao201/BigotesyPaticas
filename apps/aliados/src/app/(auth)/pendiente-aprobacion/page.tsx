'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { PartyPopper, ArrowRight, Store } from 'lucide-react';
import { useAuth } from '@/lib/auth-store';

export default function PendienteAprobacionPage() {
  const router = useRouter();
  const partnerUser = useAuth((s) => s.partnerUser);
  const token = useAuth((s) => s.token);
  const hasHydrated = useAuth((s) => s.hasHydrated);

  useEffect(() => {
    if (hasHydrated && !token) router.replace('/login');
  }, [hasHydrated, token, router]);

  if (!hasHydrated || !partnerUser) return null;

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-6">
      <div className="max-w-md w-full text-center">
        <div className="mx-auto h-16 w-16 rounded-2xl bg-primary-700 flex items-center justify-center mb-6">
          <PartyPopper className="h-8 w-8 text-white" />
        </div>
        <h1 className="font-display text-2xl font-bold text-foreground">
          ¡Bienvenido, {partnerUser.partner.business_name}!
        </h1>
        <p className="text-muted text-sm mt-3 leading-relaxed">
          Tu registro fue recibido. El equipo de Bigotes y Paticas va a revisar tu negocio antes de
          publicarlo en el directorio — normalmente toma poco tiempo. Mientras tanto, puedes ir
          configurando tu perfil, tus servicios y tu disponibilidad para que quede todo listo.
        </p>

        <div className="card text-left mt-8 flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-amber-50 flex items-center justify-center shrink-0">
            <Store className="h-5 w-5 text-amber-600" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">Estado: Pendiente de aprobación</p>
            <p className="text-xs text-muted">Te avisaremos por correo cuando quede publicado.</p>
          </div>
        </div>

        <button onClick={() => router.push('/dashboard')} className="btn-primary w-full mt-6">
          Ir a mi panel <ArrowRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
