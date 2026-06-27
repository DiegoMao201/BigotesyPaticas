'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Phone, Mail, MapPin, Star } from 'lucide-react';
import { BUSINESS_INFO } from '@/lib/business-info';

const LOGO_URL =
  process.env.NEXT_PUBLIC_BRAND_LOGO ??
  'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

const GOOGLE_REVIEW_URL = 'https://g.page/r/CfL67OgLB-10EBM/review';
const API = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

function NewsletterForm() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'ok' | 'error'>('idle');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus('loading');
    try {
      const res = await fetch(`${API}/v1/contact/newsletter`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      setStatus(res.ok ? 'ok' : 'error');
    } catch {
      setStatus('error');
    }
  }

  if (status === 'ok') {
    return (
      <p className="text-teal-700 font-semibold">
        🎉 ¡Listo! Revisa tu correo para tu cupón de bienvenida.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-md mx-auto">
      <input
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="Tu email"
        className="flex-1 px-4 py-3 rounded-xl border border-gray-200 bg-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
      />
      <button
        type="submit"
        disabled={status === 'loading'}
        className="px-6 py-3 rounded-xl bg-[#187f77] hover:bg-[#0d4a45] text-white font-semibold text-sm transition"
      >
        {status === 'loading' ? 'Suscribiendo...' : 'Suscribirme'}
      </button>
    </form>
  );
}

export function Footer() {
  return (
    <footer className="border-t border-border bg-secondary/40 mt-24">
      {/* Newsletter */}
      <section className="bg-[#187f77]/5 py-12">
        <div className="container mx-auto px-6 text-center max-w-2xl">
          <h3 className="text-2xl font-bold text-[#0d4a45] mb-2">
            🎁 Suscríbete y gana 50 Puntos Bigotes
          </h3>
          <p className="text-gray-600 mb-6">
            En tu primera compra. Cero spam, solo ofertas y tips de cuidado de mascotas.
          </p>
          <NewsletterForm />
          <p className="text-xs text-gray-500 mt-3">
            Al suscribirte aceptas nuestra{' '}
            <Link href="/politica-privacidad" className="underline hover:text-[#187f77]">
              política de privacidad
            </Link>
            .
          </p>
        </div>
      </section>

      {/* Main columns */}
      <div className="container-wide py-16 grid gap-10 md:grid-cols-5">
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
          {/* Google stars */}
          <div className="flex items-center gap-2 mt-4">
            <div className="flex">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star key={i} className="w-4 h-4 fill-yellow-400 text-yellow-400" />
              ))}
            </div>
            <a
              href={GOOGLE_REVIEW_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs font-medium text-[#187f77] hover:underline"
            >
              Califícanos en Google
            </a>
          </div>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Tienda</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/categorias/perros" className="text-muted-foreground hover:text-brand">Perros</Link></li>
            <li><Link href="/categorias/gatos" className="text-muted-foreground hover:text-brand">Gatos</Link></li>
            <li><Link href="/categorias/accesorios" className="text-muted-foreground hover:text-brand">Accesorios</Link></li>
            <li><Link href="/categorias/snacks" className="text-muted-foreground hover:text-brand">Snacks</Link></li>
            <li><Link href="/landing/hills-pereira" className="text-muted-foreground hover:text-brand">Hill&apos;s en Pereira</Link></li>
            <li><Link href="/landing/royal-canin-pereira" className="text-muted-foreground hover:text-brand">Royal Canin Pereira</Link></li>
            <li><Link href="/landing/antipulgas-perros-colombia" className="text-muted-foreground hover:text-brand">Antipulgas perros</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Ciudades</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/landing/comida-perros-pereira" className="text-muted-foreground hover:text-brand">Mascotas Pereira</Link></li>
            <li><Link href="/landing/concentrado-perro-dosquebradas" className="text-muted-foreground hover:text-brand">Mascotas Dosquebradas</Link></li>
            <li><Link href="/landing/domicilio-mascotas-pereira" className="text-muted-foreground hover:text-brand">Domicilio Pereira</Link></li>
            <li><Link href="/landing/domicilio-mascotas-dosquebradas" className="text-muted-foreground hover:text-brand">Domicilio Dosquebradas</Link></li>
            <li><Link href="/pereira-dosquebradas-mascotas" className="text-muted-foreground hover:text-brand">Pereira y Dosquebradas</Link></li>
            <li><Link href="/landing/tienda-mascotas-risaralda" className="text-muted-foreground hover:text-brand">Tienda Risaralda</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-display font-semibold text-sm mb-4 uppercase tracking-wider">Empresa</h4>
          <ul className="space-y-2 text-sm">
            <li><Link href="/nosotros" className="text-muted-foreground hover:text-brand">Sobre nosotros</Link></li>
            <li><Link href="/blog" className="text-muted-foreground hover:text-brand">Blog de mascotas</Link></li>
            <li><Link href="/contacto" className="text-muted-foreground hover:text-brand">Contacto</Link></li>
            <li><Link href="/landing/carnet-digital-mascota" className="text-muted-foreground hover:text-brand">Carnet digital mascota</Link></li>
            <li><Link href="/landing/app-mascotas-colombia" className="text-muted-foreground hover:text-brand">App para mascotas</Link></li>
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
            <li className="flex items-start gap-2">
              <MapPin className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{BUSINESS_INFO.address.streetAddress},<br />Dosquebradas, Risaralda</span>
            </li>
          </ul>
          <a
            href={BUSINESS_INFO.mapsUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-amber-600 hover:text-amber-500 transition-colors"
          >
            <Star className="h-3.5 w-3.5 fill-amber-500 text-amber-500" />
            5.0 ★★★★★ en Google
          </a>
          <div className="flex gap-3 mt-4">
            <a href="https://wa.me/573206876633" target="_blank" rel="noopener noreferrer"
               className="text-muted-foreground hover:text-brand text-[1.2rem] leading-none">💬</a>
          </div>
        </div>
      </div>

      {/* Legal bar */}
      <div className="border-t border-border">
        <div className="container-wide py-6 flex flex-col md:flex-row justify-between items-center gap-3 text-sm text-muted-foreground">
          <p>© {new Date().getFullYear()} Bigotes y Paticas. Mall Zamara Plaza, Cl. 15 #3A-07 Local 2, Dosquebradas, Risaralda.</p>
          <div className="flex gap-4">
            <Link href="/politica-privacidad" className="hover:text-brand">Privacidad</Link>
            <Link href="/terminos" className="hover:text-brand">Términos</Link>
            <Link href="/devoluciones" className="hover:text-brand">Devoluciones</Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
