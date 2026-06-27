import Link from 'next/link';
import { Instagram, Facebook, Mail, Phone, MapPin } from 'lucide-react';

const LOGO_URL = process.env.NEXT_PUBLIC_BRAND_LOGO
  ?? 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

export function Footer() {
  return (
    <footer className="border-t border-border bg-secondary/40 mt-24">
      <div className="container-wide py-16 grid gap-12 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-2xl bg-teal-700 flex items-center justify-center overflow-hidden p-1.5">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={LOGO_URL} alt="Bigotes y Paticas" className="w-full h-full object-contain" />
            </div>
            <span className="font-display font-bold text-lg">
              Bigotes <span className="text-gradient">y Paticas</span>
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Productos premium para mascotas en Pereira y Dosquebradas. Cuidamos a quien te cuida.
          </p>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Tienda</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/categorias/perros" className="text-muted-foreground hover:text-brand">Perros</Link></li>
            <li><Link href="/categorias/gatos" className="text-muted-foreground hover:text-brand">Gatos</Link></li>
            <li><Link href="/categorias/accesorios" className="text-muted-foreground hover:text-brand">Accesorios</Link></li>
            <li><Link href="/ofertas" className="text-muted-foreground hover:text-brand">Ofertas</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Empresa</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/nosotros" className="text-muted-foreground hover:text-brand">Sobre nosotros</Link></li>
            <li><Link href="/blog" className="text-muted-foreground hover:text-brand">Blog de mascotas</Link></li>
            <li><Link href="/contacto" className="text-muted-foreground hover:text-brand">Contacto</Link></li>
            <li><Link href="/pereira-dosquebradas-mascotas" className="text-muted-foreground hover:text-brand">Pereira y Dosquebradas</Link></li>
            <li>
              <a href="https://mi.bigotesypaticas.com" target="_blank" rel="noopener noreferrer"
                 className="text-muted-foreground hover:text-brand">Portal clientes</a>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Contacto</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2">
              <Phone className="h-4 w-4 shrink-0" />
              <a href="tel:+573206876633" className="hover:text-brand">+57 320 687 6633</a>
            </li>
            <li className="flex items-start gap-2">
              <Mail className="h-4 w-4 shrink-0 mt-0.5" />
              <a href="mailto:bigotesypaticasdosquebradas@gmail.com" className="hover:text-brand break-all">
                bigotesypaticasdosquebradas@gmail.com
              </a>
            </li>
            <li className="flex items-center gap-2">
              <MapPin className="h-4 w-4 shrink-0" />
              Dosquebradas, Risaralda
            </li>
          </ul>
          <div className="flex gap-3 mt-4">
            <a href="https://www.instagram.com/bigotesypaticas" target="_blank" rel="noopener noreferrer"
               className="text-muted-foreground hover:text-brand">
              <Instagram className="h-5 w-5" />
            </a>
            <a href="https://www.facebook.com/bigotesypaticas" target="_blank" rel="noopener noreferrer"
               className="text-muted-foreground hover:text-brand">
              <Facebook className="h-5 w-5" />
            </a>
            <a href="https://wa.me/573206876633" target="_blank" rel="noopener noreferrer"
               className="text-muted-foreground hover:text-brand text-[1.2rem] leading-none">💬</a>
          </div>
        </div>
      </div>

      <div className="border-t border-border">
        <div className="container-wide py-6 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-muted-foreground">
          <p>© {new Date().getFullYear()} Bigotes y Paticas. Todos los derechos reservados.</p>
          <div className="flex gap-4">
            <Link href="/legal/terminos" className="hover:text-brand">Términos</Link>
            <Link href="/legal/privacidad" className="hover:text-brand">Privacidad</Link>
            <Link href="/legal/cookies" className="hover:text-brand">Cookies</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
