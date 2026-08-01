import type { Metadata } from 'next';
import Link from 'next/link';
import { Heart, ExternalLink, AlertTriangle, PawPrint } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Adopción responsable en Pereira y Dosquebradas — Bigotes y Paticas',
  description:
    'Por qué la adopción responsable transforma vidas, y cómo elegir bien si vas a sumar un perro o gato adulto a tu familia en Pereira y Dosquebradas.',
  alternates: { canonical: 'https://bigotesypaticas.com/adopcion' },
  openGraph: {
    title: 'Adopta en Pereira y Dosquebradas — Bigotes y Paticas',
    description: 'Por qué adoptar cambia todo, y cómo prepararte para hacerlo con responsabilidad.',
    url: 'https://bigotesypaticas.com/adopcion',
  },
};

export default function AdopcionPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="bg-gradient-to-b from-[#0d4a45] to-[#187f77] text-white py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center">
              <Heart className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            Cada perro callejero en Pereira<br />tiene una historia que merece contarse.
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            En Bigotes y Paticas no somos un refugio ni hacemos adopciones directas. Pero sí creemos que el primer paso para reducir el abandono animal en Risaralda es que más personas elijan adoptar.
          </p>
        </div>
      </div>

      {/* Por qué adoptar */}
      <div className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-8 text-center">
            Por qué adoptar cambia todo
          </h2>
          <div className="space-y-6">
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-[#187f77]/10 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                <PawPrint className="w-5 h-5 text-[#187f77]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0d4a45] mb-1">Los traumas conductuales son reversibles</h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  Muchos perros en condición de calle presentan traumas conductuales que son reversibles con un proceso de socialización adecuado. No necesitas un cachorro para tener un perro tranquilo.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-[#187f77]/10 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                <Heart className="w-5 h-5 text-[#187f77]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0d4a45] mb-1">Un adulto ya sabe quién es</h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  Con un perro o gato adulto sabes de entrada su tamaño, temperamento y energía. No hay sorpresas de "se me creció más de lo esperado". Los adultos en hogares de paso son evaluados por personas que los conocen de cerca.
                </p>
              </div>
            </div>
            <div className="flex gap-4">
              <div className="w-10 h-10 bg-[#187f77]/10 rounded-full flex items-center justify-center shrink-0 mt-0.5">
                <AlertTriangle className="w-5 h-5 text-[#187f77]" />
              </div>
              <div>
                <h3 className="font-semibold text-[#0d4a45] mb-1">Comprar alimenta el ciclo del abandono</h3>
                <p className="text-gray-600 text-sm leading-relaxed">
                  Cada compra de cachorro de criadero informal (la mayoría en Risaralda no están certificados) financia condiciones de reproducción intensiva. Mientras tanto, miles de animales con exactamente las mismas capacidades esperan en un hogar de paso.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Dónde adoptar */}
      <div className="bg-[#f5f0e8] py-16 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-3">
            Dónde adoptar en Pereira y Dosquebradas
          </h2>
          <p className="text-gray-600 text-sm leading-relaxed">
            Bigotes y Paticas no gestiona adopciones directamente. Hay fundaciones, hogares de paso y jornadas municipales activas en Pereira y Dosquebradas — búscalas en redes sociales y consulta con tu clínica veterinaria de confianza, que suele conocer las opciones vigentes en la zona.
          </p>
        </div>
      </div>

      {/* CTA — si ya adoptaste */}
      <div className="py-16 px-4">
        <div className="max-w-2xl mx-auto text-center">
          <div className="bg-[#0d4a45] rounded-3xl p-10 text-white">
            <h2 className="text-2xl font-display font-bold mb-4">
              ¿Ya adoptaste? Ayúdanos a cuidarlo bien.
            </h2>
            <p className="text-white/75 mb-8 leading-relaxed">
              Un animal adoptado merece la misma alimentación, salud y cuidado que cualquier otro. En Bigotes y Paticas tenemos todo lo que necesitas para que tu nuevo compañero tenga la vida que siempre mereció.
            </p>
            <div className="flex flex-wrap justify-center gap-3">
              <Link
                href="/categorias/perros"
                className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors"
              >
                🐕 Productos para perros
              </Link>
              <Link
                href="/categorias/gatos"
                className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors"
              >
                🐈 Productos para gatos
              </Link>
              <a
                href="https://wa.me/573206876633?text=Hola!%20Acabo%20de%20adoptar%20y%20quiero%20asesoría%20sobre%20alimentación"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 bg-green-500 text-white rounded-xl font-semibold text-sm hover:bg-green-600 transition-colors flex items-center gap-2"
              >
                <ExternalLink className="w-4 h-4" /> Asesoría por WhatsApp
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
