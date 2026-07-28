'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-store';

export default function RootPage() {
  const router = useRouter();
  const token = useAuth((s) => s.token);
  const hasHydrated = useAuth((s) => s.hasHydrated);

  useEffect(() => {
    if (!hasHydrated) return;
    router.replace(token ? '/dashboard' : '/login');
  }, [hasHydrated, token, router]);

  return null;
}
