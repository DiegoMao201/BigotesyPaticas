import type { Metadata } from 'next';
import Link from 'next/link';
import { ExternalLink, Scale, TrendingDown } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Planes nutricionales para perros y gatos — Bigotes y Paticas Pereira',
  description:
    'El 62% de perros adultos en Pereira presentan sobrepeso. Aprende cómo calcular la ración correcta y elegir el alimento adecuado para tu mascota según su etapa de vida.',
  alternates: { canonical: 'https://bigotesypaticas.com/planes-nutricionales' },
  openGraph: {
    title: 'Planes nutricionales para mascotas — Bigotes y Paticas',
    description:
      '2 kg de sobrepeso en un perro de 10 kg equivalen a que tú cargues 15 kg extras en la espalda. Descubre cómo calcular la ración ideal.',
    url: 'https://bigotesypaticas.com/planes-nutricionales',
  },
};

const STATS = [
  { cifra: '62%', label: 'de perros adultos en Pereira tienen sobrepeso' },
  { cifra: '3x', label: 'más rápido se desgasta el cartílago articular con sobrepeso' },
  { cifra: '20%', label: 'sobrecarga articular con solo 2 kg extras en un perro de 10 kg' },
  { cifra: '2–3 años', label: 'menos de vida útil en mascotas con obesidad crónica' },
];

const ETAPAS = [
  {
    etapa: 'Cachorro (0–12 meses)',
    emoji: '🐣',
    necesidades: 'Alta densidad calórica, proteína de calidad para desarrollo muscular y óseo. Calcio y fósforo en proporción correcta para evitar displasia. Nunca suplementar calcio extra en cachorros de razas grandes sin indicación veterinaria.',
    frecuencia: '3–4 comidas al día hasta los 6 meses, luego 2–3.',
    señal: 'Costillas palpables sin ser visibles. Cintura definida al mirar desde arriba.',
  },
  {
    etapa: 'Adulto (1–7 años)',
    emoji: '🐕',
    necesidades: 'Mantenimiento del peso ideal. La cantidad exacta depende de la marca, el peso del animal y su nivel de actividad. Referencia base: entre 2% y 3% del peso corporal en seco, ajustado por la tabla de la marca específica.',
    frecuencia: '2 comidas al día. Siempre a la misma hora.',
    señal: 'Costillas fácilmente palpables con leve capa de grasa. Abdomen recogido sin ser hundido.',
  },
  {
    etapa: 'Senior (7+ años)',
    emoji: '🦮',
    necesidades: 'Reducción calórica y control de proteína si hay compromiso renal. Suplementación de omega-3 para articulaciones. Alimentos senior formulados con menor densidad energética y mayor contenido de fibra para el tránsito intestinal.',
    frecuencia: '2–3 porciones pequeñas para facilitar digestión.',
    señal: 'El peso ideal puede verse diferente: algunos senior pierden masa muscular aunque la grasa aumente. Consulta tu veterinario anualmente.',
  },
];

const ERRORES = [
  { error: 'Dar "un poco más" porque quedó mirando el plato', realidad: 'Los perros y gatos siempre piden más, independientemente de si tienen hambre. El instinto de acumulación es evolutivo.' },
  { error: 'Mezclar alimento seco con casero sin calcular', realidad: 'El alimento balanceado está formulado para ser completo. Agregar pollo, arroz o pasta sin ajustar la cantidad total genera exceso calórico y desequilibrio nutricional.' },
  { error: 'Cambiar de marca de repente', realidad: 'El cambio brusco genera diarrea y rechazo. Siempre hacer transición gradual durante 7-10 días mezclando proporcionalmente.' },
  { error: 'Usar la misma ración para toda la vida', realidad: 'Las necesidades cambian con la edad, el nivel de actividad, la esterilización y las estaciones. Recalcula la ración cada 6 meses.' },
];

export default function PlanesNutricionalesPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="bg-gradient-to-b from-[#0d4a45] to-[#187f77] text-white py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center">
              <Scale className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            2 kg de sobrepeso en tu perro<br />equivalen a 15 kg extras en tu espalda.
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            En el Eje Cafetero, los veterinarios reportan que el <strong className="text-white">62% de perros adultos tienen sobrepeso</strong>. La mayoría desarrolla problemas articulares después de los 7 años. La nutrición correcta no es un lujo — es la diferencia entre caminar sin dolor o no hacerlo.
          </p>
        </div>
      </div>

      {/* Cifras */}
      <div className="bg-[#f5f0e8] py-14 px-4">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            {STATS.map((s) => (
              <div key={s.cifra} className="bg-white rounded-2xl p-6 text-center shadow-sm border border-[#e8e0d0]">
                <p className="text-3xl font-extrabold text-[#187f77] mb-2">{s.cifra}</p>
                <p className="text-sm text-gray-600 leading-tight">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Cómo saber si tiene sobrepeso */}
      <div className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-6 text-center">
            Cómo saber si tu mascota tiene el peso ideal
          </h2>
          <div className="bg-[#f9f7f3] rounded-2xl p-8 border border-[#e8e0d0] mb-10">
            <div className="flex items-start gap-3 mb-4">
              <TrendingDown className="w-5 h-5 text-[#187f77] shrink-0 mt-0.5" />
              <h3 className="font-semibold text-[#0d4a45]">La prueba de las costillas (BCS — Body Condition Score)</h3>
            </div>
            <p className="text-sm text-gray-600 mb-4 leading-relaxed">
              Pasa tus dedos suavemente por los costados de tu perro o gato con presión similar a la que usarías sobre el dorso de tu mano. Deberías <strong>sentir las costillas fácilmente</strong> sin tener que presionar, pero sin verlas prominentemente.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { label: 'Muy delgado', desc: 'Costillas visibles, columna prominente, sin grasa detectable.', color: 'bg-blue-50 border-blue-200 text-blue-800' },
                { label: 'Peso ideal', desc: 'Costillas palpables con leve cobertura. Cintura visible desde arriba.', color: 'bg-green-50 border-green-200 text-green-800' },
                { label: 'Sobrepeso', desc: 'Costillas difíciles de palpar. Abdomen redondeado. Sin cintura.', color: 'bg-red-50 border-red-200 text-red-800' },
              ].map((item) => (
                <div key={item.label} className={`rounded-xl p-4 border ${item.color}`}>
                  <p className="font-semibold text-xs mb-1">{item.label}</p>
                  <p className="text-xs leading-relaxed opacity-80">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Nutrición por etapa */}
      <div className="bg-[#f5f0e8] py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-10 text-center">
            Lo que necesita tu mascota en cada etapa
          </h2>
          <div className="space-y-6">
            {ETAPAS.map((e) => (
              <div key={e.etapa} className="bg-white rounded-2xl p-6 border border-[#e8e0d0] shadow-sm">
                <div className="flex items-center gap-3 mb-4">
                  <span className="text-3xl">{e.emoji}</span>
                  <h3 className="font-bold text-[#0d4a45] text-lg">{e.etapa}</h3>
                </div>
                <div className="grid md:grid-cols-3 gap-4 text-sm text-gray-600">
                  <div>
                    <p className="font-semibold text-[#0d4a45] mb-1 text-xs uppercase tracking-wide">Necesidades</p>
                    <p className="leading-relaxed">{e.necesidades}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-[#0d4a45] mb-1 text-xs uppercase tracking-wide">Frecuencia</p>
                    <p className="leading-relaxed">{e.frecuencia}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-[#0d4a45] mb-1 text-xs uppercase tracking-wide">Cómo reconocer el peso ideal</p>
                    <p className="leading-relaxed">{e.señal}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Errores comunes */}
      <div className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-8 text-center">
            Errores de nutrición que se ven todos los días
          </h2>
          <div className="space-y-4">
            {ERRORES.map((item) => (
              <div key={item.error} className="bg-[#f9f7f3] rounded-xl p-5 border border-[#e8e0d0]">
                <p className="font-semibold text-[#0d4a45] mb-1 text-sm">❌ {item.error}</p>
                <p className="text-sm text-gray-600">✅ {item.realidad}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="bg-[#0d4a45] py-16 px-4">
        <div className="max-w-2xl mx-auto text-center text-white">
          <h2 className="text-2xl font-display font-bold mb-4">
            ¿No sabes qué alimento es el correcto para tu mascota?
          </h2>
          <p className="text-white/75 mb-8">
            Te ayudamos a elegir según el peso, la edad, la raza y el nivel de actividad. Tenemos concentrados premium con envío en 24-72h en Pereira y Dosquebradas.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/categorias/perros?sub_cat=concentrado" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🐕 Concentrado para perros
            </Link>
            <Link href="/categorias/gatos?sub_cat=concentrado" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🐈 Concentrado para gatos
            </Link>
            <a href="https://wa.me/573206876633?text=Hola!%20Necesito%20ayuda%20para%20elegir%20el%20alimento%20ideal%20para%20mi%20mascota" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-green-500 text-white rounded-xl font-semibold text-sm hover:bg-green-600 transition-colors flex items-center gap-2">
              <ExternalLink className="w-4 h-4" /> Asesoría por WhatsApp
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
