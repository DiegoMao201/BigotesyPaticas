import { Instagram, Facebook } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';

/** Icono de TikTok (lucide no lo trae). */
export function TikTokIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
      <path d="M16.5 3c.4 2.4 1.9 4 4.5 4.2v3.1c-1.7 0-3.2-.5-4.5-1.4v6.3c0 3.6-2.9 6.4-6.5 6.4S3.5 18.8 3.5 15.2c0-3.6 2.9-6.4 6.5-6.4.4 0 .7 0 1 .1v3.3c-.3-.1-.7-.2-1-.2-1.8 0-3.2 1.4-3.2 3.2s1.4 3.2 3.2 3.2 3.2-1.4 3.2-3.2V3h3.3Z" />
    </svg>
  );
}

/** Icono de WhatsApp. */
export function WhatsAppIcon({ className = 'h-5 w-5' }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
      <path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.3-.4.7-1.3.1-.2 0-.3 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2c0 1.3 1 2.6 1.1 2.8.1.2 1.9 3 4.7 4.2 1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.1-1.2l-.4-.3Z" />
    </svg>
  );
}

const S = BUSINESS_INFO.social;

export const SOCIAL_LINKS = [
  { key: 'instagram', label: 'Instagram', handle: S.instagram.handle, url: S.instagram.url, Icon: Instagram, color: 'hover:text-pink-600' },
  { key: 'tiktok', label: 'TikTok', handle: S.tiktok.handle, url: S.tiktok.url, Icon: TikTokIcon, color: 'hover:text-black' },
  { key: 'facebook', label: 'Facebook', handle: S.facebook.handle, url: S.facebook.url, Icon: Facebook, color: 'hover:text-blue-600' },
  { key: 'whatsapp', label: 'WhatsApp', handle: S.whatsapp.handle, url: S.whatsapp.url, Icon: WhatsAppIcon, color: 'hover:text-green-600' },
] as const;

/** Fila compacta de iconos (footer, cabeceras). */
export function SocialIcons({ className = '' }: { className?: string }) {
  return (
    <ul className={`flex items-center gap-3 ${className}`} aria-label="Redes sociales de Bigotes y Paticas">
      {SOCIAL_LINKS.map(({ key, label, url, Icon, color }) => (
        <li key={key}>
          <a
            href={url}
            target="_blank"
            rel="noopener noreferrer me"
            aria-label={`${label} de Bigotes y Paticas`}
            title={label}
            className={`inline-flex h-10 w-10 items-center justify-center rounded-full border border-border bg-white text-muted-foreground transition-colors ${color} hover:border-current`}
          >
            <Icon className="h-5 w-5" />
          </a>
        </li>
      ))}
    </ul>
  );
}

/** Seccion completa "Siguenos" para la portada, contacto y nosotros. */
export function FollowUsSection({ compact = false }: { compact?: boolean }) {
  return (
    <section className={compact ? '' : 'container-wide py-12'} aria-labelledby="siguenos">
      <div className="rounded-[2rem] border border-border bg-white p-8 md:p-10 shadow-sm">
        <div className="grid gap-8 md:grid-cols-5 items-center">
          <div className="md:col-span-2">
            <p className="text-xs font-semibold uppercase tracking-widest text-[#187f77] mb-2">Comunidad</p>
            <h2 id="siguenos" className="font-display font-extrabold text-2xl md:text-3xl text-[#0d4a45] mb-3">
              Síguenos en nuestras redes
            </h2>
            <p className="text-sm text-muted-foreground leading-relaxed">
              Cada día publicamos una historia corta sobre perros y gatos: lo que hacen, por qué lo hacen y cómo cuidarlos mejor.
              Somos la misma tienda en Instagram, TikTok, Facebook, WhatsApp y aquí en la web.
            </p>
          </div>
          <ul className="md:col-span-3 grid grid-cols-2 gap-3">
            {SOCIAL_LINKS.map(({ key, label, handle, url, Icon, color }) => (
              <li key={key}>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer me"
                  className={`flex items-center gap-3 rounded-2xl border border-border bg-secondary/40 px-4 py-3 transition-colors text-foreground ${color} hover:bg-white hover:border-current`}
                >
                  <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-white border border-border">
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold">{label}</span>
                    <span className="block text-xs text-muted-foreground truncate">{handle}</span>
                  </span>
                </a>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}
