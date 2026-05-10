import Link from 'next/link';
import { ArrowRight, Truck, ShieldCheck, Heart, Sparkles, Star } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { storeApi } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

const CATEGORIES = [
  { slug: 'perros', name: 'Perros', emoji: '🐕', tone: 'from-brand-100 to-brand-50' },
  { slug: 'gatos', name: 'Gatos', emoji: '🐈', tone: 'from-amber-100 to-amber-50' },
  { slug: 'accesorios', name: 'Accesorios', emoji: '🎀', tone: 'from-rose-100 to-rose-50' },
  { slug: 'cuidado', name: 'Cuidado', emoji: '✨', tone: 'from-violet-100 to-violet-50' },
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
