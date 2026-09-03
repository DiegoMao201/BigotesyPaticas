import Link from 'next/link';
import { ArrowRight, Heart, LifeBuoy, HomeIcon, PartyPopper } from 'lucide-react';

interface Props {
  adoptionCount: number;
  lostCount: number;
  foundCount: number;
}

export function CommunityCTA({ adoptionCount, lostCount, foundCount }: Props) {
  return (
    <section className="container-wide py-16">
      <div className="rounded-[2.5rem] bg-gradient-to-br from-[#187f77] via-[#0d4a45] to-[#085041] p-8 md:p-12 overflow-hidden relative">
        <div className="absolute -top-24 -left-16 w-72 h-72 rounded-full bg-white/5 pointer-events-none" />
        <div className="absolute -bottom-16 -right-20 w-56 h-56 rounded-full bg-white/5 pointer-events-none" />

        <div className="relative grid md:grid-cols-[1.2fr_1fr] gap-10 items-center">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 border border-white/20 text-white/90 text-xs font-semibold mb-5">
              <Heart className="h-3.5 w-3.5" /> Comunidad Bigotes y Paticas · Adopción y ayuda mutua
            </div>
            <h2 className="text-3xl md:text-4xl font-display font-extrabold text-white mb-3 leading-tight">
              Un hogar para cada animal,<br />una mano para cada familia
            </h2>
            <p className="text-white/75 text-sm leading-relaxed mb-8 max-w-md">
              Nuestro foro de adopción, reportes de mascotas perdidas y animales encontrados — todo en un solo lugar,
              publicado por la propia comunidad de Pereira y Dosquebradas.
            </p>

            <Link
              href="/adopcion"
              className="inline-flex items-center gap-2 px-6 py-3.5 rounded-2xl bg-white text-[#0d4a45] font-bold text-sm hover:bg-white/90 transition-colors shadow-lg"
            >
              Ir al foro de adopción <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="flex flex-col gap-3">
            <Link
              href="/adopcion"
              className="flex items-center gap-3 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/15 p-4 hover:bg-white/15 transition-colors"
            >
              <div className="h-11 w-11 rounded-xl bg-white/15 flex items-center justify-center shrink-0">
                <Heart className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-white font-semibold text-sm">Foro de Adopción</p>
                <p className="text-white/60 text-xs">{adoptionCount > 0 ? `${adoptionCount} publicaciones abiertas` : 'Publica en segundos, sin cuenta'}</p>
              </div>
            </Link>
            <Link
              href="/mascotas-perdidas"
              className="flex items-center gap-3 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/15 p-4 hover:bg-white/15 transition-colors"
            >
              <div className="h-11 w-11 rounded-xl bg-white/15 flex items-center justify-center shrink-0">
                <LifeBuoy className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-white font-semibold text-sm">Mascotas Perdidas</p>
                <p className="text-white/60 text-xs">{lostCount > 0 ? `${lostCount} reportes activos` : 'Reporta y pide ayuda a la comunidad'}</p>
              </div>
            </Link>
            <Link
              href="/mascotas-encontradas"
              className="flex items-center gap-3 rounded-2xl bg-white/10 backdrop-blur-sm border border-white/15 p-4 hover:bg-white/15 transition-colors"
            >
              <div className="h-11 w-11 rounded-xl bg-white/15 flex items-center justify-center shrink-0">
                <HomeIcon className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-white font-semibold text-sm">Animales Encontrados</p>
                <p className="text-white/60 text-xs">{foundCount > 0 ? `${foundCount} esperando a su familia` : 'Publica lo que encontraste'}</p>
              </div>
            </Link>
            <Link
              href="/finales-felices"
              className="flex items-center gap-3 rounded-2xl bg-emerald-400/20 backdrop-blur-sm border border-emerald-300/40 p-4 hover:bg-emerald-400/30 transition-colors"
            >
              <div className="h-11 w-11 rounded-xl bg-emerald-400/30 flex items-center justify-center shrink-0">
                <PartyPopper className="h-5 w-5 text-white" />
              </div>
              <div className="min-w-0">
                <p className="text-white font-semibold text-sm">🎉 Finales Felices</p>
                <p className="text-white/70 text-xs">Mascotas que volvieron a casa y encontraron hogar</p>
              </div>
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
