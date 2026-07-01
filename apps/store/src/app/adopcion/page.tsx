import type { Metadata } from 'next';
import Link from 'next/link';
import { Heart, MapPin, Phone, ExternalLink, AlertTriangle, PawPrint } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Adopción responsable en Pereira y Dosquebradas — Bigotes y Paticas',
  description:
    'Aproximadamente 8.000 perros y gatos viven en las calles de Risaralda. Conoce dónde adoptar en Pereira y Dosquebradas, y por qué la adopción transforma vidas.',
  alternates: { canonical: 'https://bigotesypaticas.com/adopcion' },
  openGraph: {
    title: 'Adopta en Pereira y Dosquebradas — Bigotes y Paticas',
    description:
      'Datos reales sobre la situación animal en Risaralda y dónde encontrar tu compañero de vida.',
    url: 'https://bigotesypaticas.com/adopcion',
  },
};

const REFUGIOS = [
  {
    nombre: 'FUNPAZ — Fundación Paz Animal Risaralda',
    descripcion: 'Una de las fundaciones más activas de la región. Hacen jornadas de adopción periódicas en Pereira y trabajan con hogares de paso.',
    ubicacion: 'Pereira, Risaralda',
    contacto: 'Instagram: @funpazrisaralda',
    tipo: 'Perros y gatos',
  },
  {
    nombre: 'Hogar de Paso AANIMALES',
    descripcion: 'Red de hogares de paso en Pereira y Dosquebradas con animales en proceso de rehabilitación, listos para adoptar.',
    ubicacion: 'Pereira — Dosquebradas',
    contacto: 'Instagram: @aanimalesrisaralda',
    tipo: 'Perros y gatos',
  },
  {
    nombre: 'Secretaría de Salud de Pereira — Programa Animal',
    descripcion: 'El municipio tiene un programa de protección animal. Puedes consultar información sobre animales rescatados en proceso de adopción.',
    ubicacion: 'Alcaldía de Pereira',
    contacto: 'salud.pereira.gov.co',
    tipo: 'Perros',
  },
  {
    nombre: 'Mall Zamara — Jornadas Periódicas',
    descripcion: 'Se realizan jornadas de adopción con varias fundaciones en el Mall Zamara Plaza. Consulta las fechas próximas en redes sociales de las fundaciones locales.',
    ubicacion: 'Mall Zamara Plaza, Pereira',
    contacto: 'Fechas variables — sigue las redes de las fundaciones',
    tipo: 'Perros y gatos',
  },
];

const STATS = [
  { cifra: '~8.000', label: 'perros en situación de calle en Risaralda' },
  { cifra: '8 de 10', label: 'nunca han recibido atención veterinaria básica' },
  { cifra: '73%', label: 'de camadas no fueron planificadas' },
  { cifra: '4–8 meses', label: 'tiempo promedio de espera de un gato adulto en hogar de paso' },
];

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
            En Bigotes y Paticas no somos un refugio ni hacemos adopciones directas. Pero sí creemos que el primer paso para reducir el abandono animal en Risaralda es que más personas elijan adoptar. Aquí encontrarás información real y lugares donde puedes hacerlo.
          </p>
        </div>
      </div>

      {/* Cifras reales */}
      <div className="bg-[#f5f0e8] py-14 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-center text-xl font-display font-bold text-[#0d4a45] mb-10">
            La realidad en números — Risaralda
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map((s) => (
              <div key={s.cifra} className="bg-white rounded-2xl p-6 text-center shadow-sm border border-[#e8e0d0]">
                <p className="text-3xl font-extrabold text-[#187f77] mb-2">{s.cifra}</p>
                <p className="text-sm text-gray-600 leading-tight">{s.label}</p>
              </div>
            ))}
          </div>
          <p className="text-center text-xs text-gray-400 mt-6">
            Fuentes: Secretaría de Salud de Pereira · Distrito de Manejo Integrado Otún · Estimaciones ONG locales
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
                  Aproximadamente el 80% de los perros en condición de calle en Dosquebradas presentan traumas conductuales que son completamente reversibles con un proceso de socialización adecuado. No necesitas un cachorro para tener un perro tranquilo.
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
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-3 text-center">
            Dónde adoptar en Pereira y Dosquebradas
          </h2>
          <p className="text-center text-gray-500 text-sm mb-10">
            Bigotes y Paticas no gestiona adopciones. Te compartimos las organizaciones que sí lo hacen con responsabilidad.
          </p>
          <div className="grid md:grid-cols-2 gap-5">
            {REFUGIOS.map((r) => (
              <div key={r.nombre} className="bg-white rounded-2xl p-6 border border-[#e8e0d0] shadow-sm">
                <div className="flex items-start gap-3 mb-3">
                  <MapPin className="w-5 h-5 text-[#187f77] shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-[#0d4a45] text-sm leading-tight">{r.nombre}</h3>
                    <span className="text-xs text-[#187f77] font-medium">{r.tipo}</span>
                  </div>
                </div>
                <p className="text-sm text-gray-600 mb-3 leading-relaxed">{r.descripcion}</p>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Phone className="w-3.5 h-3.5" />
                  <span>{r.contacto}</span>
                </div>
              </div>
            ))}
          </div>
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
