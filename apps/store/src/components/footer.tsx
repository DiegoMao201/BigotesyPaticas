import Link from 'next/link';
import { Instagram, Facebook, Mail, Phone, MapPin } from 'lucide-react';

export function Footer() {
  return (
    <footer className="border-t border-border bg-secondary/40 mt-24">
      <div className="container-wide py-16 grid gap-12 md:grid-cols-4">
        <div>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-2xl gradient-brand flex items-center justify-center text-white text-xl">
              🐾
            </div>
            <span className="font-display font-bold text-lg">
              Bigotes <span className="text-gradient">y Paticas</span>
            </span>
          </div>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Productos premium para mascotas. Cuidamos a quien te cuida.
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
            <li><Link href="/blog" className="text-muted-foreground hover:text-brand">Blog</Link></li>
            <li><Link href="/contacto" className="text-muted-foreground hover:text-brand">Contacto</Link></li>
            <li><Link href="/admin" className="text-muted-foreground hover:text-brand">Acceso admin</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Contacto</h4>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li className="flex items-center gap-2"><Phone className="h-4 w-4" /> +57 300 123 4567</li>
            <li className="flex items-center gap-2"><Mail className="h-4 w-4" /> hola@bigotesypaticas.com</li>
            <li className="flex items-center gap-2"><MapPin className="h-4 w-4" /> Colombia</li>
          </ul>
          <div className="flex gap-3 mt-4">
            <a href="#" className="text-muted-foreground hover:text-brand"><Instagram className="h-5 w-5" /></a>
            <a href="#" className="text-muted-foreground hover:text-brand"><Facebook className="h-5 w-5" /></a>
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
