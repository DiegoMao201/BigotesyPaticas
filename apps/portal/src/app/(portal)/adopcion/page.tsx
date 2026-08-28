'use client';

import Link from 'next/link';
import { Heart, ChevronLeft, Home, Search } from 'lucide-react';

export default function AdoptionHubPage() {
  return (
    <div className="flex flex-col gap-5 pb-4">
      <div
        className="px-4 pt-6 pb-8"
        style={{
          background: 'linear-gradient(145deg, #2fc4a8 0%, #187f77 55%, #085041 100%)',
          borderRadius: '0 0 28px 28px',
          boxShadow: '0 8px 24px rgba(24,127,119,0.28)',
        }}
      >
        <Link href="/" className="inline-flex items-center gap-1 text-white/80 text-xs font-semibold mb-2">
          <ChevronLeft className="h-3.5 w-3.5" /> Inicio
        </Link>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-white/80 text-xs font-semibold uppercase tracking-wide">Comunidad Bigotes y Paticas</p>
            <h1 className="font-display text-2xl font-extrabold text-white mt-0.5">Foro de Adopción</h1>
          </div>
          <div className="h-14 w-14 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center">
            <Heart className="h-7 w-7 text-white" strokeWidth={2.2} />
          </div>
        </div>
        <p className="text-white/90 text-sm mt-3 leading-relaxed">
          Publica un animal que necesita hogar, o publica que estás buscando adoptar. Todo esto también aparece en
          bigotesypaticas.com para que más gente lo vea.
        </p>
      </div>

      <div className="px-4 flex flex-col gap-3">
        <Link href="/adopcion/publicar" className="card flex items-center gap-3 py-4 hover:shadow-card-hover transition-shadow">
          <div className="h-12 w-12 rounded-2xl bg-[#E6F5F1] flex items-center justify-center shrink-0">
            <Home className="h-6 w-6 text-emerald-700" />
          </div>
          <div>
            <p className="font-display font-bold text-foreground">Doy un animalito en adopción</p>
            <p className="text-xs text-muted">Sube fotos, dirección y cómo lo entregas</p>
          </div>
        </Link>

        <Link href="/adopcion/buscar" className="card flex items-center gap-3 py-4 hover:shadow-card-hover transition-shadow">
          <div className="h-12 w-12 rounded-2xl bg-[#E6F5F1] flex items-center justify-center shrink-0">
            <Search className="h-6 w-6 text-emerald-700" />
          </div>
          <div>
            <p className="font-display font-bold text-foreground">Busco adoptar</p>
            <p className="text-xs text-muted">Publica qué tipo de compañero buscas</p>
          </div>
        </Link>
      </div>
    </div>
  );
}
