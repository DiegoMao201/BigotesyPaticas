import Link from 'next/link';
import { ArrowRight, Truck, ShieldCheck, Heart, Sparkles, Star, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

const CATEGORIES = [
  { slug: 'perros', name: 'Perros', emoji: '🐕', tone: 'from-orange-100 to-amber-50', accent: 'text-orange-700' },
  { slug: 'gatos', name: 'Gatos', emoji: '🐈', tone: 'from-brand-100 to-orange-50', accent: 'text-brand-700' },
  { slug: 'accesorios', name: 'Accesorios', emoji: '🎀', tone: 'from-rose-100 to-pink-50', accent: 'text-rose-700' },
  { slug: 'snacks', name: 'Snacks', emoji: '🦴', tone: 'from-amber-100 to-yellow-50', accent: 'text-amber-700' },
];

const VALUES = [
  { icon: Truck, title: 'Envío rápido', desc: 'Entregas en 24-72h en todo el país', color: 'from-teal-500 to-teal-600' },
  { icon: ShieldCheck, title: 'Compra segura', desc: 'Pagos protegidos y garantía de calidad', color: 'from-emerald-500 to-emerald-600' },
  { icon: Heart, title: 'Curado con cariño', desc: 'Marcas seleccionadas por veterinarios', color: 'from-rose-500 to-rose-600' },
  { icon: Sparkles, title: 'Premium siempre', desc: 'Solo productos de la mejor calidad', color: 'from-amber-500 to-orange-500' },
];

export default async function HomePage() {
  const featured = await storeApi.featured();

  return (
    <>
      {/* PROMO BANNER */}
      <div className="gradient-brand text-white text-center py-2.5 text-sm font-medium tracking-wide">
        🎉 Envío GRATIS en compras mayores a $150.000 · Dosquebradas y todo Colombia 🐾
      </div>

      {/* HERO */}
      <section className="relative overflow-hidden bg-paw-pattern">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-40 -left-40 w-[600px] h-[600px] rounded-full bg-brand-300/20 blur-3xl" />
          <div className="absolute -bottom-40 -right-40 w-[700px] h-[700px] rounded-full bg-amber-200/30 blur-3xl" />
        </div>

        <div className="container-wide pt-16 pb-24 md:pt-20 md:pb-32 grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-7 animate-slide-up">
            <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-brand-50 border border-brand-100 text-brand-700 text-xs font-semibold">
              <Zap className="h-3.5 w-3.5 fill-brand-500 text-brand-500" />
              Nueva temporada · Productos premium 2026
            </div>
            <h1 className="text-5xl md:text-6xl lg:text-7xl font-display font-extrabold leading-[1.05] tracking-tight">
              El amor que se<br />
              <span className="text-gradient">merece tu mascota.</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-lg leading-relaxed">
              Alimentos premium, accesorios y cuidado para perros y gatos,
              seleccionados con amor por expertos. Entregamos directo a tu puerta.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/categorias/perros">
                <Button size="lg" className="shadow-glow">
                  Comprar ahora <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/nosotros">
                <Button size="lg" variant="outline">
                  Conoce la marca
                </Button>
              </Link>
            </div>
            <div className="flex items-center gap-6 pt-2 text-sm">
              <div className="flex items-center gap-1.5">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                ))}
                <span className="ml-1 font-semibold text-foreground">4.9</span>
              </div>
              <span className="text-muted-foreground">+1,000 mascotas felices</span>
            </div>
          </div>

          <div className="relative">
            <div className="aspect-square rounded-[3rem] gradient-brand shadow-glow relative overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center text-[14rem] leading-none select-none animate-[float_4s_ease-in-out_infinite]">
                🐾
              </div>
              {/* Floating badge */}
              <div className="absolute top-6 right-6 glass-brand rounded-2xl p-3 backdrop-blur-xl bg-white/80 border border-white/60">
                <div className="flex items-center gap-2 text-sm font-semibold text-brand-700">
                  <span className="text-2xl">🐕</span> <span>+500 productos</span>
                </div>
              </div>
            </div>
            {/* Envío card */}
            <div className="absolute -bottom-6 -left-6 glass rounded-2xl p-4 shadow-warm">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl gradient-teal flex items-center justify-center text-white">
                  <Truck className="h-5 w-5" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Envío gratis</div>
                  <div className="font-bold text-sm">desde $150.000</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
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

      {/* FEATURED */}
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
                <div className="aspect-square bg-secondary relative overflow-hidden">
                  {p.primary_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={p.primary_image_url}
                      alt={p.name}
                      className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-110"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-6xl bg-gradient-to-br from-orange-50 to-amber-50">🐾</div>
                  )}
                  {/* Availability badge */}
                  <div className={`absolute top-3 left-3 text-xs font-semibold px-2.5 py-1 rounded-full backdrop-blur-sm ${
                    p.in_stock
                      ? 'bg-emerald-100/90 text-emerald-700 border border-emerald-200/60'
                      : 'bg-gray-100/90 text-gray-500 border border-gray-200/60'
                  }`}>
                    {p.in_stock ? '✓ Disponible' : 'Sin stock'}
                  </div>
                  {/* CTA hover overlay */}
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
            <div className="flex flex-col sm:flex-row gap-3 justify-center max-w-md mx-auto">
              <input
                type="email"
                placeholder="tu@email.com"
                className="flex-1 px-5 py-3 rounded-2xl bg-white/20 backdrop-blur-sm border border-white/30 text-white placeholder:text-white/60 focus:outline-none focus:ring-2 focus:ring-white/50"
              />
              <button className="px-6 py-3 rounded-2xl bg-white text-brand-600 font-bold hover:bg-white/90 transition-colors shadow-md">
                Suscribirme 🎁
              </button>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}


const CATEGORIES = [
  { slug: 'perros', name: 'Perros', emoji: '🐕', tone: 'from-brand-100 to-brand-50' },
  { slug: 'gatos', name: 'Gatos', emoji: '🐈', tone: 'from-amber-100 to-amber-50' },
  { slug: 'accesorios', name: 'Accesorios', emoji: '🎀', tone: 'from-rose-100 to-rose-50' },
  { slug: 'snacks', name: 'Snacks', emoji: '🦴', tone: 'from-violet-100 to-violet-50' },
];

const VALUES = [
  { icon: Truck, title: 'Envío rápido', desc: 'Entregas en 24-72h en todo el país' },
  { icon: ShieldCheck, title: 'Compra segura', desc: 'Pagos protegidos y garantía de calidad' },
  { icon: Heart, title: 'Curado con cariño', desc: 'Marcas seleccionadas por veterinarios' },
  { icon: Sparkles, title: 'Premium siempre', desc: 'Solo productos de la mejor calidad' },
];

export default async function HomePage() {
  const featured = await storeApi.featured();

  return (
    <>
      {/* HERO */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 -z-10">
          <div className="absolute -top-32 -left-32 w-[500px] h-[500px] rounded-full bg-brand/30 blur-3xl" />
          <div className="absolute -bottom-32 -right-32 w-[600px] h-[600px] rounded-full bg-brand-300/20 blur-3xl" />
        </div>

        <div className="container-wide pt-16 pb-24 md:pt-24 md:pb-32 grid lg:grid-cols-2 gap-12 items-center">
          <div className="space-y-6 animate-slide-up">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-brand/10 text-brand text-xs font-medium">
              <Sparkles className="h-3 w-3" />
              Nueva colección · Premium 2026
            </div>
            <h1 className="text-5xl md:text-7xl font-display font-bold leading-[1.05] tracking-tight">
              Cuidamos a quien <br />
              <span className="text-gradient">te cuida.</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-lg leading-relaxed">
              Productos premium seleccionados con cariño para perros y gatos. Comida, accesorios y
              cuidado de las mejores marcas, entregados a tu puerta.
            </p>
            <div className="flex flex-wrap gap-3 pt-2">
              <Link href="/categorias/perros">
                <Button size="lg">
                  Comprar ahora <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
              <Link href="/nosotros">
                <Button size="lg" variant="outline">
                  Conoce la marca
                </Button>
              </Link>
            </div>
            <div className="flex items-center gap-6 pt-4 text-sm text-muted-foreground">
              <div className="flex items-center gap-1">
                {[1, 2, 3, 4, 5].map((i) => (
                  <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
                ))}
              </div>
              <span>+1000 mascotas felices</span>
            </div>
          </div>

          <div className="relative">
            <div className="aspect-square rounded-[3rem] gradient-brand shadow-elegant relative overflow-hidden">
              <div className="absolute inset-0 flex items-center justify-center text-[16rem] leading-none select-none opacity-90">
                🐾
              </div>
            </div>
            <div className="absolute -bottom-6 -left-6 glass rounded-2xl p-4 shadow-elegant">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-emerald-500/20 flex items-center justify-center">
                  <Truck className="h-5 w-5 text-emerald-600" />
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Envío gratis</div>
                  <div className="font-semibold text-sm">desde $150.000</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* CATEGORIES */}
      <section className="container-wide py-16">
        <div className="flex items-end justify-between mb-8">
          <div>
            <h2 className="text-3xl md:text-4xl font-display font-bold">Compra por categoría</h2>
            <p className="text-muted-foreground mt-2">Encuentra justo lo que tu mascota necesita</p>
          </div>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {CATEGORIES.map((cat) => (
            <Link
              key={cat.slug}
              href={`/categorias/${cat.slug}`}
              className={`group relative overflow-hidden rounded-3xl bg-gradient-to-br ${cat.tone} p-6 aspect-[4/5] flex flex-col justify-between transition-all hover:shadow-elegant hover:-translate-y-1`}
            >
              <div className="text-7xl">{cat.emoji}</div>
              <div>
                <h3 className="text-xl font-display font-bold text-ink">{cat.name}</h3>
                <div className="flex items-center gap-1 text-sm text-ink/70 group-hover:gap-2 transition-all">
                  Ver productos <ArrowRight className="h-3 w-3" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>

      {/* FEATURED */}
      {featured.length > 0 && (
        <section className="container-wide py-16">
          <div className="flex items-end justify-between mb-8">
            <div>
              <h2 className="text-3xl md:text-4xl font-display font-bold">Destacados</h2>
              <p className="text-muted-foreground mt-2">Los favoritos de nuestra comunidad</p>
            </div>
            <Link href="/categorias/todos" className="text-sm text-brand hover:underline">
              Ver todo →
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {featured.slice(0, 8).map((p) => (
              <Link
                key={p.id}
                href={`/producto/${p.slug}`}
                className="group rounded-2xl overflow-hidden border border-border bg-card transition-all hover:shadow-elegant hover:-translate-y-1"
              >
                <div className="aspect-square bg-secondary relative">
                  {p.primary_image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={p.primary_image_url} alt={p.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-6xl">🐾</div>
                  )}
                  <div className={`absolute top-2 left-2 text-xs font-medium px-2 py-0.5 rounded-full ${
                    p.in_stock
                      ? 'bg-emerald-100 text-emerald-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}>
                    {p.in_stock ? 'Disponible' : 'No disponible'}
                  </div>
                </div>
                <div className="p-4">
                  <h3 className="font-medium text-sm line-clamp-2 group-hover:text-brand transition-colors">
                    {p.name}
                  </h3>
                  <div className="flex items-baseline gap-2 mt-2">
                    <span className="font-bold">{formatCurrency(p.price)}</span>
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

      {/* VALUES */}
      <section className="container-wide py-16">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-6">
          {VALUES.map((v) => {
            const Icon = v.icon;
            return (
              <div
                key={v.title}
                className="rounded-2xl border border-border bg-card p-6 transition-all hover:border-brand/40 hover:-translate-y-1"
              >
                <div className="w-12 h-12 rounded-xl gradient-brand flex items-center justify-center text-white mb-4">
                  <Icon className="h-5 w-5" />
                </div>
                <h3 className="font-display font-semibold mb-1">{v.title}</h3>
                <p className="text-sm text-muted-foreground">{v.desc}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* CTA */}
      <section className="container-wide py-16">
        <div className="rounded-[2.5rem] gradient-brand text-white p-12 md:p-16 text-center shadow-elegant relative overflow-hidden">
          <div className="absolute inset-0 opacity-20 text-9xl flex items-center justify-center pointer-events-none">
            🐾
          </div>
          <div className="relative">
            <h2 className="text-3xl md:text-5xl font-display font-bold mb-4">
              Únete al club Bigotes y Paticas
            </h2>
            <p className="text-white/90 max-w-xl mx-auto mb-8">
              10% de descuento en tu primera compra y acceso anticipado a lanzamientos.
            </p>
            <form className="flex max-w-md mx-auto gap-2">
              <input
                type="email"
                required
                placeholder="tu@email.com"
                className="flex-1 h-12 rounded-full px-5 text-foreground bg-white"
              />
              <Button type="submit" variant="ink" size="lg">
                Suscribirme
              </Button>
            </form>
          </div>
        </div>
      </section>
    </>
  );
}
