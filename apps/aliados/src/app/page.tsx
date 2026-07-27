'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth-store';

export default function RootPage() {
  const router = useRouter();
  const token = useAuth((s) => s.token);

  useEffect(() => {
    router.replace(token ? '/dashboard' : '/login');
  }, [token, router]);

  return null;
}
