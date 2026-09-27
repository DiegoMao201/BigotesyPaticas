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

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { setCustomer } = useAuthStore();
  const pathname = usePathname();

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
    <div className="min-h-screen pb-24" style={{ background: 'transparent' }}>
      <LocationTracker />
      <PromoGroomer />

      {/* Campana de notificaciones — esquina superior derecha */}
      <div className="fixed top-3 right-3 z-30">
        <NotificationBell />
      </div>

      {children}
      <CartButton />
      <BottomNav />
      <SOSButton />
      <WhatsAppButton />

      {/* Modal de términos — solo primera vez */}
      <TermsModal />
      <GoogleReviewPrompt />
    </div>
  );
}
