'use client';

import { useEffect } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { auth } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { BottomNav } from '@/components/ui/bottom-nav';
import { WhatsAppButton } from '@/components/ui/whatsapp-button';
import { SOSButton } from '@/components/ui/sos-button';
import { CartButton } from '@/components/cart/CartButton';
import { PageLoader } from '@/components/ui/loading-spinner';
import { TermsModal } from '@/components/portal/TermsModal';
import { GoogleReviewPrompt } from '@/components/reviews/GoogleReviewPrompt';
import { NotificationBell } from '@/components/portal/NotificationBell';
import { LocationTracker } from '@/components/portal/LocationTracker';
import { PromoGroomer } from '@/components/portal/PromoGroomer';
import { HuellaOferta } from '@/components/auth/Huella';
import { CorreoSeguro } from '@/components/auth/CorreoSeguro';
import { AvisosOferta } from '@/components/portal/Avisos';

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { setCustomer } = useAuthStore();
  const pathname = usePathname();
  const enTienda = pathname === '/orders/new';

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portal-me'],
    queryFn: auth.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (data) setCustomer(data);
    // recuerda a dónde iba (p. ej. el QR de citas) para volver ahí después de entrar
    if (isError) router.replace(`/login?next=${encodeURIComponent(pathname || '/dashboard')}`);
  }, [data, isError, setCustomer, router, pathname]);

  if (isLoading) return <PageLoader />;
  if (!data) return null;

  return (
    <div className="min-h-[100dvh] pb-24 short:pb-14" style={{ background: 'transparent' }}>
      <LocationTracker />
      <PromoGroomer />

      {/* Campana de notificaciones — esquina superior derecha */}
      <div className="fixed top-3 right-3 z-30">
        <NotificationBell />
      </div>

      {children}
      {/* En la tienda manda la barra del carrito: tres botones flotantes encima de la
          rejilla tapaban precios y el "+" (8-nov-2026). WhatsApp sigue en el detalle
          y en "no encontramos eso". */}
      {!enTienda && <CartButton />}
      <BottomNav />
      {!enTienda && <SOSButton />}
      {!enTienda && <WhatsAppButton />}

      {/* Modal de términos — solo primera vez */}
      <TermsModal />
      <CorreoSeguro />
      <AvisosOferta />
      <HuellaOferta />
      <GoogleReviewPrompt />
    </div>
  );
}
