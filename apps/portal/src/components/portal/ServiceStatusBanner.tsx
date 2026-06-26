'use client';

import { useQuery } from '@tanstack/react-query';
import { serviceStatus } from '@/lib/api';

export function ServiceStatusBanner() {
  const { data } = useQuery({
    queryKey: ['service-status'],
    queryFn: serviceStatus.get,
    staleTime: 5 * 60 * 1000, // re-check each 5 min
  });

  if (!data?.message) return null;

  return (
    <div className="mx-4 mt-3 rounded-2xl bg-amber-50 border border-amber-200 px-4 py-3 flex items-start gap-3">
      <span className="text-lg shrink-0 mt-0.5">⏰</span>
      <div className="flex-1 min-w-0">
        <p className="text-amber-800 text-sm font-medium leading-snug">{data.message}</p>
        {data.next_delivery_window && (
          <p className="text-amber-600 text-xs mt-0.5">
            Próxima entrega: <strong>{data.next_delivery_window}</strong>
          </p>
        )}
      </div>
    </div>
  );
}
