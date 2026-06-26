import { cn } from '@/lib/utils';

const LOGO_URL = process.env.NEXT_PUBLIC_BRAND_LOGO
  ?? 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

export function LoadingSpinner({ className }: { className?: string }) {
  return (
    <div className={cn('flex items-center justify-center py-12', className)}>
      <div className="h-8 w-8 rounded-full border-3 border-primary-200 border-t-primary-700 animate-spin" />
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center bg-primary-700 gap-4 z-50">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={LOGO_URL} alt="Bigotes y Paticas" className="w-14 h-14 object-contain animate-bounce" />
      <p className="text-white/80 text-sm font-medium">Cargando...</p>
    </div>
  );
}
