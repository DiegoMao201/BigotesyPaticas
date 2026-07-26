'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { PawPrint } from 'lucide-react';
import { adminPortal } from '@/lib/api';
import { Dialog, DialogBody, DialogFooter } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

const POLL_MS = 10 * 60 * 1000; // 10 minutos

export function PendingPortalOrdersAlert() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const shownForFetch = useRef<number | null>(null);

  const { data, dataUpdatedAt } = useQuery({
    queryKey: ['portal-pending-orders-summary'],
    queryFn: adminPortal.pendingOrdersSummary,
    refetchInterval: POLL_MS,
    refetchIntervalInBackground: true,
    staleTime: 0,
  });

  useEffect(() => {
    if (!data) return;
    if (data.count > 0 && shownForFetch.current !== dataUpdatedAt) {
      setOpen(true);
      shownForFetch.current = dataUpdatedAt;
    }
    if (data.count === 0) {
      setOpen(false);
    }
  }, [data, dataUpdatedAt]);

  if (!data || data.count === 0) return null;

  return (
    <Dialog open={open} onClose={() => setOpen(false)} size="sm">
      <DialogBody className="text-center space-y-3 pt-2">
        <div className="mx-auto w-14 h-14 rounded-full bg-amber-100 flex items-center justify-center">
          <PawPrint className="w-7 h-7 text-amber-600" />
        </div>
        <h2 className="text-lg font-bold font-display">
          Tienes {data.count} pedido{data.count === 1 ? '' : 's'} pendiente{data.count === 1 ? '' : 's'} del portal
        </h2>
        <p className="text-sm text-muted-foreground">
          Hay pedidos hechos desde el portal que aún no se han gestionado. Revísalos para no perderlos de vista.
        </p>
      </DialogBody>
      <DialogFooter className="justify-center">
        <Button
          onClick={() => {
            setOpen(false);
            router.push('/pet-monitor');
          }}
        >
          Revisar ahora
        </Button>
      </DialogFooter>
    </Dialog>
  );
}
