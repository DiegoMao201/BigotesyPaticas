'use client';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export function Pagination({
  page,
  pageSize,
  total,
  onPageChange,
}: {
  page: number;
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  return (
    <div className="flex items-center justify-between text-sm py-3">
      <div className="text-muted-foreground">
        Mostrando <span className="font-semibold">{from}</span>-
        <span className="font-semibold">{to}</span> de{' '}
        <span className="font-semibold">{total.toLocaleString()}</span>
      </div>
      <div className="flex items-center gap-1">
        <button
          onClick={() => onPageChange(Math.max(1, page - 1))}
          disabled={page <= 1}
          className={cn(
            'p-1.5 rounded-md border border-border bg-card disabled:opacity-40 disabled:cursor-not-allowed hover:bg-muted',
          )}
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
        <span className="px-3 py-1 text-sm font-medium">
          Página {page} / {pages}
        </span>
        <button
          onClick={() => onPageChange(Math.min(pages, page + 1))}
          disabled={page >= pages}
          className="p-1.5 rounded-md border border-border bg-card disabled:opacity-40 disabled:cursor-not-allowed hover:bg-muted"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
