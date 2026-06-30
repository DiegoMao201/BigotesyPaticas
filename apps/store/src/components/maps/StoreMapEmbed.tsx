import { BUSINESS_INFO } from '@/lib/business-info';

const KEY = process.env.NEXT_PUBLIC_GOOGLE_MAPS_KEY ?? '';

interface Props {
  height?: number;
  zoom?: number;
  className?: string;
}

export function StoreMapEmbed({ height = 420, zoom = 17, className = '' }: Props) {
  const { address, name } = BUSINESS_INFO;
  const q = encodeURIComponent(
    `${name}, ${address.streetAddress}, ${address.addressLocality}, ${address.addressRegion}`,
  );
  const src = `https://www.google.com/maps/embed/v1/place?key=${KEY}&q=${q}&zoom=${zoom}&language=es`;

  return (
    <div className={`rounded-2xl overflow-hidden border border-border shadow-sm ${className}`}>
      <iframe
        src={src}
        width="100%"
        height={height}
        loading="lazy"
        referrerPolicy="no-referrer-when-downgrade"
        title={`${name} en ${address.addressLocality}, ${address.addressRegion} — Google Maps`}
        className="border-0 block"
        allowFullScreen
      />
    </div>
  );
}
