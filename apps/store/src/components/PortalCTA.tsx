import { ArrowRight } from 'lucide-react';
import { Logo } from '@/components/brand/Logo';

const FEATURES = [
  { icon: '🎁', label: 'Puntos de lealtad' },
  { icon: '📋', label: 'Carnet digital' },
  { icon: '🛁', label: 'Recordatorio baño' },
  { icon: '💉', label: 'Vacunas al día' },
];

export function PortalCTA() {
  return (
    <section className="container-wide py-16">
      <div className="rounded-[2.5rem] bg-gradient-to-br from-teal-600 via-teal-700 to-teal-900 p-8 md:p-12 overflow-hidden relative">
        {/* Decorative circles */}
        <div className="absolute -top-20 -right-20 w-72 h-72 rounded-full bg-white/5 pointer-events-none" />
        <div className="absolute -bottom-16 -left-16 w-56 h-56 rounded-full bg-white/5 pointer-events-none" />

        <div className="relative grid md:grid-cols-2 gap-10 items-center">
          {/* Left */}
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/15 border border-white/20 text-white/90 text-xs font-semibold mb-5">
              🐾 Portal de fidelización · Exclusivo para clientes
            </div>
            <h2 className="text-3xl md:text-4xl font-display font-extrabold text-white mb-3 leading-tight">
              Todo sobre tu mascota,<br />en un solo lugar
            </h2>
            <p className="text-white/75 text-sm leading-relaxed mb-6 max-w-sm">
              Gestiona la salud, vacunas, historial y puntos de fidelidad de tu mascota
              desde el portal exclusivo de Bigotes y Paticas.
            </p>

            {/* Feature chips */}
            <div className="flex flex-wrap gap-2 mb-8">
              {FEATURES.map((f) => (
                <span
                  key={f.label}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-white/15 backdrop-blur-sm border border-white/20 text-white text-xs font-medium"
                >
                  {f.icon} {f.label}
                </span>
              ))}
            </div>

            {/* CTAs */}
            <div className="flex flex-wrap gap-3">
              <a
                href="https://mi.bigotesypaticas.com"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-2xl bg-white text-teal-800 font-bold text-sm hover:bg-white/90 transition-colors shadow-lg"
              >
                Ingresar al portal <ArrowRight className="h-4 w-4" />
              </a>
              <a
                href="https://mi.bigotesypaticas.com/registro"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 px-5 py-3 rounded-2xl border border-white/30 text-white text-sm font-medium hover:bg-white/10 transition-colors"
              >
                Crear cuenta gratis
              </a>
            </div>
          </div>

          {/* Right — mock phone */}
          <div className="hidden md:flex justify-center">
            <div className="relative w-56 h-96">
              <div className="absolute inset-0 rounded-[2.5rem] bg-teal-950/70 border-2 border-white/20 shadow-2xl backdrop-blur-sm overflow-hidden">
                {/* Status bar */}
                <div className="h-6 flex items-center justify-center">
                  <div className="w-16 h-1 rounded-full bg-white/20" />
                </div>
                {/* App header */}
                <div className="px-4 py-2.5 border-b border-white/10 flex items-center gap-2">
                  <Logo size={24} />
                  <span className="text-white text-xs font-semibold">Mi Portal</span>
                </div>
                {/* Mock UI */}
                <div className="p-3 space-y-2">
                  {/* Points */}
                  <div className="rounded-xl bg-white/10 p-3">
                    <div className="text-white/55 text-[9px] mb-0.5">Mis puntos</div>
                    <div className="text-white font-bold text-lg">1,250 pts</div>
                    <div className="mt-2 h-1 rounded-full bg-white/20">
                      <div className="h-full w-3/5 rounded-full bg-amber-400" />
                    </div>
                  </div>
                  {/* Pet */}
                  <div className="rounded-xl bg-white/10 p-3 flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-amber-400/30 flex items-center justify-center text-base">🐶</div>
                    <div>
                      <div className="text-white text-xs font-semibold">Max</div>
                      <div className="text-white/50 text-[9px]">Próx. vacuna: 15 jul</div>
                    </div>
                  </div>
                  {/* Health */}
                  <div className="rounded-xl bg-white/10 p-3">
                    <div className="text-white/55 text-[9px] mb-1.5">💉 Estado de vacunas</div>
                    <div className="space-y-1.5">
                      <div className="flex justify-between">
                        <span className="text-white text-[9px]">Rabia</span>
                        <span className="text-green-400 text-[9px]">✓ OK</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-white text-[9px]">Moquillo</span>
                        <span className="text-amber-400 text-[9px]">⚠ Pronto</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
