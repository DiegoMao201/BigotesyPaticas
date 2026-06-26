'use client';

import Link from 'next/link';
import { useRef, useState } from 'react';
import { ArrowRight, Star, Truck, VolumeX, Volume2 } from 'lucide-react';
import { Button } from '@/components/ui/button';

const CDN = 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding';
const VIDEO_MP4  = process.env.NEXT_PUBLIC_HERO_VIDEO_MP4  ?? `${CDN}/login-bg.mp4`;
const VIDEO_WEBM = process.env.NEXT_PUBLIC_HERO_VIDEO_WEBM ?? `${CDN}/login-bg.webm`;
const VIDEO_POSTER = process.env.NEXT_PUBLIC_HERO_VIDEO_POSTER ?? `${CDN}/login-bg.jpg`;

export function HeroSection() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);

  return (
    <section className="relative min-h-[88vh] flex items-center overflow-hidden">
      {/* VIDEO BACKGROUND */}
      <video
        ref={videoRef}
        autoPlay muted loop playsInline
        preload="metadata"
        poster={VIDEO_POSTER}
        className="absolute inset-0 w-full h-full object-cover"
      >
        <source src={VIDEO_WEBM} type="video/webm" />
        <source src={VIDEO_MP4}  type="video/mp4"  />
      </video>

      {/* Gradient overlay */}
      <div className="absolute inset-0 bg-gradient-to-r from-teal-950/90 via-teal-900/70 to-teal-900/20" />
      <div className="absolute inset-0 bg-gradient-to-t from-teal-950/50 via-transparent to-transparent" />

      {/* Mute button */}
      <button
        onClick={() => {
          if (!videoRef.current) return;
          videoRef.current.muted = !muted;
          setMuted(!muted);
        }}
        className="absolute top-5 right-5 z-20 w-10 h-10 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center text-white hover:bg-white/25 transition-colors"
        aria-label={muted ? 'Activar sonido' : 'Silenciar'}
      >
        {muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
      </button>

      {/* CONTENT */}
      <div className="container-wide relative z-10 py-20 md:py-28">
        <div className="max-w-2xl space-y-7 animate-slide-up">
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 text-white text-xs font-semibold">
            ✨ Nueva temporada · Productos premium 2026
          </div>

          {/* Headline */}
          <h1 className="text-5xl md:text-6xl lg:text-7xl font-display font-extrabold text-white leading-[1.05] tracking-tight drop-shadow-2xl">
            El amor que se<br />
            <span className="text-amber-300">merece tu mascota.</span>
          </h1>

          <p className="text-lg md:text-xl text-white/85 max-w-lg leading-relaxed">
            Alimentos premium, accesorios y cuidado para perros y gatos.
            Entregamos en Pereira y Dosquebradas en 24-72 horas.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap gap-3 pt-2">
            <Link href="/categorias/perros">
              <Button size="lg" className="bg-white text-teal-800 hover:bg-white/90 shadow-xl font-bold text-sm">
                Comprar ahora <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link href="/nosotros">
              <Button size="lg" variant="outline" className="border-white/40 text-white hover:bg-white/10 backdrop-blur-sm">
                Conoce la marca
              </Button>
            </Link>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap items-center gap-6 pt-2">
            <div className="flex items-center gap-1.5">
              {[1,2,3,4,5].map((i) => (
                <Star key={i} className="h-4 w-4 fill-amber-400 text-amber-400" />
              ))}
              <span className="text-white font-bold ml-1">4.9</span>
            </div>
            <div className="text-white/75 text-sm">+500 productos disponibles</div>
            <div className="flex items-center gap-1.5 text-white/75 text-sm">
              <Truck className="h-4 w-4 text-teal-300" />
              Entrega 24-72h
            </div>
          </div>
        </div>
      </div>

      {/* Free shipping badge — desktop only */}
      <div className="absolute bottom-8 right-8 hidden md:block">
        <div className="bg-white/95 backdrop-blur-xl rounded-2xl p-4 shadow-2xl border border-white/60">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center text-white">
              <Truck className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs text-muted-foreground">Envío gratis</div>
              <div className="font-bold text-sm">desde $30.000</div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
