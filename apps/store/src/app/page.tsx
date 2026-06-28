import type { Metadata } from 'next';
import Link from 'next/link';
import { ArrowRight, Truck, ShieldCheck, Heart, Sparkles, MapPin } from 'lucide-react';

export const revalidate = 600; // 10 min

export const metadata: Metadata = {
  alternates: { canonical: 'https://bigotesypaticas.com' },
};
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import { HeroSection } from '@/components/HeroSection';
import { PortalCTA } from '@/components/PortalCTA';
import { NewsletterForm } from '@/components/NewsletterForm';

const CATEGORIES = [
  { slug: 'perros',     name: 'Perros',     emoji: '🐕', tone: 'from-orange-100 to-amber-50', accent: 'text-orange-700' },
  { slug: 'gatos',      name: 'Gatos',      emoji: '🐈', tone: 'from-brand-100 to-orange-50', accent: 'text-brand-700' },
  { slug: 'accesorios', name: 'Accesorios', emoji: '🎀', tone: 'from-rose-100 to-pink-50',    accent: 'text-rose-700'  },
  { slug: 'snacks',     name: 'Snacks',     emoji: '🦴', tone: 'from-amber-100 to-yellow-50', accent: 'text-amber-700' },
];

const VALUES = [
  { icon: Truck,       title: 'Envío rápido',      desc: 'Entregas en 24-72h en Pereira y Dosquebradas', color: 'from-teal-500 to-teal-600'      },
  { icon: ShieldCheck, title: 'Compra segura',      desc: 'Pagos protegidos y garantía de calidad',       color: 'from-emerald-500 to-emerald-600' },
  { icon: Heart,       title: 'Curado con cariño', desc: 'Marcas seleccionadas por veterinarios',         color: 'from-rose-500 to-rose-600'       },
  { icon: Sparkles,    title: 'Premium siempre',   desc: 'Solo productos de la mejor calidad',            color: 'from-amber-500 to-orange-500'    },
];


const MARQUEE_ITEMS = [
  '🐾 Envío gratis desde $30.000',
  '⭐ 4.9 en satisfacción',
  '🐕 +500 productos',
  '🚚 Entrega 24-72h',
  '🎁 10% en tu primera compra',
  '💉 Carnet digital gratis',
  '📦 Pereira y Dosquebradas',
  '🏠 Zona urbana Risaralda',
];

export default async function HomePage() {
  const featured = await storeApi.featured();

  return (
    <>
      {/* MARQUEE BANNER */}
      <div className="gradient-brand text-white py-2.5 overflow-hidden">
        <div className="flex whitespace-nowrap animate-marquee">
          {[...MARQUEE_ITEMS, ...MARQUEE_ITEMS].map((item, i) => (
            <span key={i} className="mx-8 text-sm font-medium shrink-0">{item}</span>
          ))}
        </div>
      </div>

      {/* HERO — VIDEO */}
      <HeroSection />

      {/* FEATURED — Destacados */}
      {featured.length > 0 && (
        <section className="container-wide py-20 bg-paw-pattern">
          <div className="flex items-end justify-between mb-10">
            <div>
              <p className="text-brand-600 font-semibold text-sm mb-1">Más vendidos</p>
              <h2 className="text-3xl md:text-4xl font-display font-extrabold">Destacados</h2>
              <p className="text-muted-foreground mt-2">Los favoritos de nuestra comunidad</p>
            </div>
            <Link href="/categorias/todos" className="text-sm font-semibold text-brand-600 hover:text-brand-500 flex items-center gap-1">
              Ver todo <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {featured.slice(0, 8).map((p) => (
              <Link
                key={p.id}
                href={`/producto/${p.slug}`}
                className="group rounded-3xl overflow-hidden border border-border bg-card transition-all hover:shadow-warm hover:-translate-y-2 duration-300"
              >
                <div className="aspect-square bg-white flex items-center justify-center overflow-hidden relative p-3">
                  {p.primary_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.primary_image_url}
                      alt={p.name}
                      className="w-full h-full object-contain transition-transform duration-500 group-hover:scale-110 drop-shadow-sm"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-6xl bg-gradient-to-br from-orange-50 to-amber-50">🐾</div>
                  )}
                  <div className={`absolute top-3 left-3 text-xs font-semibold px-2.5 py-1 rounded-full backdrop-blur-sm ${
                    p.in_stock
                      ? 'bg-emerald-100/90 text-emerald-700 border border-emerald-200/60'
                      : 'bg-gray-100/90 text-gray-500 border border-gray-200/60'
                  }`}>
                    {p.in_stock ? '✓ Disponible' : 'Sin stock'}
                  </div>
                  <div className="absolute inset-0 gradient-brand opacity-0 group-hover:opacity-90 transition-opacity flex items-center justify-center">
                    <span className="text-white font-bold text-sm">Agregar al carrito 🛒</span>
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-sm line-clamp-2 group-hover:text-brand-600 transition-colors">
                    {p.name}
                  </h3>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="text-lg font-extrabold text-brand-600">{formatCurrency(p.price)}</span>
                    {p.compare_at_price && (
                      <span className="text-xs text-muted-foreground line-through">
                        {formatCurrency(p.compare_at_price)}
                      </span>
                    )}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* CATEGORIES — Compra por categoría */}
      <section className="container-wide py-20">
        <div className="flex items-end justify-between mb-10">
          <div>
            <p className="text-brand-600 font-semibold text-sm mb-1">Explora nuestro catálogo</p>
            <h2 className="text-3xl md:text-4xl font-display font-extrabold">Compra por categoría</h2>
            <p className="text-muted-foreground mt-2">Encuentra justo lo que tu mascota necesita</p>
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-5">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/categorias/${cat.slug}`}
              className={`group relative overflow-hidden rounded-3xl bg-gradient-to-br ${cat.tone} p-6 aspect-[4/5] flex flex-col justify-between transition-all hover:shadow-warm hover:-translate-y-2 border border-white/60`}
            >
              <div className="text-8xl transition-transform group-hover:scale-110 group-hover:rotate-6 duration-300">
                {cat.emoji}
              </div>
              <div>
                <h3 className={`text-2xl font-display font-extrabold ${cat.accent}`}>{cat.name}</h3>
                <div className={`flex items-center gap-1 text-sm font-medium ${cat.accent} opacity-70 group-hover:opacity-100 group-hover:gap-2 transition-all`}>
                  Ver productos <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* PORTAL CTA */}
      <PortalCTA />

      {/* VALUES */}
      <section className="container-wide py-20">
        <div className="text-center mb-12">
          <p className="text-brand-600 font-semibold text-sm mb-2">¿Por qué elegirnos?</p>
          <h2 className="text-3xl md:text-4xl font-display font-extrabold">El estándar Bigotes y Paticas</h2>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {VALUES.map((v) => {
            const Icon = v.icon;
            return (
              <div
                key={v.title}
                className="group rounded-3xl border border-border bg-card p-6 transition-all hover:shadow-warm hover:-translate-y-1 duration-300"
              >
                <div className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${v.color} flex items-center justify-center text-white mb-5 transition-transform group-hover:scale-110 duration-300 shadow-md`}>
                  <Icon className="h-6 w-6" />
                </div>
                <h3 className="font-display font-bold text-lg mb-2">{v.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{v.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ZONAS DE COBERTURA */}
      <section className="container-wide py-20">
        <div className="text-center mb-10">
          <p className="text-brand-600 font-semibold text-sm mb-2">Cobertura de entrega</p>
          <h2 className="text-3xl md:text-4xl font-display font-extrabold">Atendemos en Pereira y Dosquebradas</h2>
          <p className="text-muted-foreground mt-3 max-w-xl mx-auto">
            Domicilio rápido a toda la zona urbana de Risaralda. Haz tu pedido y lo recibís en casa.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 max-w-2xl mx-auto">
          {[
            { ciudad: 'Pereira', barrios: 'Circunvalar, Cuba, Álamos, Centro, Pinares, Cerritos', emoji: '🏙️' },
            { ciudad: 'Dosquebradas', barrios: 'La Pradera, El Balso, Otún, Fermín López, Molinos', emoji: '🏘️' },
          ].map((z) => (
            <div key={z.ciudad} className="rounded-3xl border border-border bg-card p-7 flex gap-4 items-start">
              <div className="w-12 h-12 rounded-2xl gradient-brand flex items-center justify-center text-2xl shrink-0">
                {z.emoji}
              </div>
              <div>
                <p className="font-display font-bold text-lg">{z.ciudad}</p>
                <p className="text-sm text-muted-foreground mt-1 leading-relaxed">{z.barrios} y más.</p>
              </div>
            </div>
          ))}
        </div>
        <div className="text-center mt-8">
          <a
            href="https://wa.me/573206876633?text=Hola!%20Quiero%20saber%20si%20hacen%20domicilio%20a%20mi%20zona"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 rounded-full bg-[#187f77] text-white font-semibold hover:bg-[#0d4a45] transition-colors"
          >
            <MapPin className="h-4 w-4" />
            Consultar cobertura por WhatsApp
          </a>
        </div>
      </section>

      {/* CTA NEWSLETTER */}
      <section className="container-wide py-16">
        <div className="rounded-[2.5rem] gradient-brand text-white p-12 md:p-16 text-center shadow-glow relative overflow-hidden bg-paw-pattern">
          <div className="absolute inset-0 opacity-10 text-[200px] flex items-center justify-around pointer-events-none select-none leading-none">
            🐾🐕🐈🦴
          </div>
          <div className="relative">
            <p className="text-white/80 text-sm font-semibold mb-3 uppercase tracking-widest">Club de mascotas felices</p>
            <h2 className="text-3xl md:text-5xl font-display font-extrabold mb-4">
              Únete al club Bigotes y Paticas
            </h2>
            <p className="text-white/85 text-lg max-w-xl mx-auto mb-8">
              Suscríbete y recibe 10% de descuento en tu primera compra + tips de cuidado para tu mascota.
            </p>
            <NewsletterForm />
          </div>
        </div>
      </section>
    </>
  );
}
