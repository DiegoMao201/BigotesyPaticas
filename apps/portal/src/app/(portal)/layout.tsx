'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { auth } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { BottomNav } from '@/components/ui/bottom-nav';
import { WhatsAppButton } from '@/components/ui/whatsapp-button';
import { PageLoader } from '@/components/ui/loading-spinner';
import { TermsModal } from '@/components/portal/TermsModal';
import { NotificationBell } from '@/components/portal/NotificationBell';

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { setCustomer } = useAuthStore();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['portal-me'],
    queryFn: auth.me,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (data) setCustomer(data);
    if (isError) router.replace('/login');
  }, [data, isError, setCustomer, router]);

  if (isLoading) return <PageLoader />;
  if (!data) return null;

  return (
    <div className="min-h-screen pb-24" style={{ background: 'transparent' }}>
      {/* Campana de notificaciones — esquina superior derecha */}
      <div className="fixed top-3 right-3 z-30">
        <NotificationBell />
      </div>

      {children}
      <BottomNav />
      <WhatsAppButton />

      {/* Modal de términos — solo primera vez */}
      <TermsModal />
    </div>
  );
}
