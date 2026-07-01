import type { Metadata } from 'next';
import Link from 'next/link';
import { AlertTriangle, ExternalLink } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Nutrición y salud oral en perros y gatos — Bigotes y Paticas',
  description:
    'El 80% de perros mayores de 3 años ya tienen enfermedad periodontal activa. Aprende cómo la alimentación correcta protege la salud bucal de tu mascota.',
  alternates: { canonical: 'https://bigotesypaticas.com/nutricion-salud-oral' },
  openGraph: {
    title: 'Salud oral y nutrición para mascotas — Bigotes y Paticas Pereira',
    description:
      'La enfermedad periodontal no duele, pero mata en silencio. Descubre cómo prevenirla desde la alimentación.',
    url: 'https://bigotesypaticas.com/nutricion-salud-oral',
  },
};

const STATS = [
  { cifra: '80%', label: 'de perros mayores de 3 años ya tienen enfermedad periodontal' },
  { cifra: '5 años', label: 'sin intervención: pierden piezas dentales funcionales' },
  { cifra: '3x', label: 'más frecuente en razas mini y small' },
  { cifra: '70%', label: 'de gatos adultos presentan algún grado de enfermedad dental' },
];

const SENALES = [
  'Mal aliento persistente (más allá del olor normal)',
  'Dificultad para masticar o preferencia por un lado',
  'Pérdida de apetito sin causa aparente',
  'Salivación excesiva o saliva con sangre',
  'Encías rojizas, inflamadas o con sarro visible',
  'Frotarse la boca con las patas frecuentemente',
];

const PREVENCION = [
  {
    titulo: 'Alimento seco (croquetas) de calidad',
    descripcion:
      'Las croquetas de alta calidad tienen una textura que genera fricción mecánica al masticarse, removiendo parcialmente el sarro acumulado. Las marcas premium como Hills, Royal Canin y Pro Plan tienen líneas específicas con acción dental comprobada. Las genéricas blandas, al contrario, aceleran la acumulación de sarro.',
    emoji: '🦷',
  },
  {
    titulo: 'Snacks dentales específicos',
    descripcion:
      'Los snacks dentales (como Dentastix, CET Chews o huesos naturales aprobados) están diseñados para generar abrasión controlada en la superficie dental. No son un sustituto del cepillado, pero reducen significativamente la velocidad de acumulación de sarro entre limpiezas profesionales.',
    emoji: '🦴',
  },
  {
    titulo: 'Cepillado regular desde cachorro',
    descripcion:
      'El cepillado 2-3 veces por semana con pasta dental veterinaria (NUNCA humana — el flúor es tóxico para perros y gatos) es el método más efectivo. Si tu mascota es adulta y no está acostumbrada, hay que adaptarla gradualmente. Paciencia: vale la pena.',
    emoji: '🪥',
  },
  {
    titulo: 'Limpieza profesional anual',
    descripcion:
      'La profilaxis dental veterinaria (limpieza con ultrasonido bajo anestesia) elimina el sarro subgingival que ningún producto casero puede remover. Se recomienda anualmente desde los 2-3 años. El costo de una limpieza es mucho menor al de extracciones dentales o tratamiento de infección.',
    emoji: '🏥',
  },
];

export default function NutricionSaludOralPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="bg-gradient-to-b from-[#0d4a45] to-[#187f77] text-white py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="text-5xl mb-6">🦷</div>
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            La enfermedad periodontal no duele.<br />Por eso mata en silencio.
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            El 80% de perros mayores de 3 años ya tienen enfermedad periodontal activa. No es halitosis normal: es infección bacteriana destruyendo encías, ligamentos y hueso. Y la alimentación correcta puede frenarla desde hoy.
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

      {/* Lo que nadie te cuenta */}
      <div className="py-16 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-8 mb-10">
            <div className="flex items-start gap-3 mb-4">
              <AlertTriangle className="w-6 h-6 text-red-500 shrink-0 mt-0.5" />
              <h2 className="text-xl font-bold text-red-800">Lo que nadie te cuenta sobre la enfermedad dental</h2>
            </div>
            <div className="space-y-3 text-sm text-red-700 leading-relaxed">
              <p>
                El sarro visible en los dientes de tu perro es solo la punta del problema. La devastación real ocurre <strong>debajo de la línea de encía</strong>, donde las bacterias colonizan el espacio entre diente y encía, destruyendo el ligamento periodontal y el hueso alveolar sin que tu mascota muestre dolor evidente.
              </p>
              <p>
                Un perro con periodontitis crónica tiene <strong>bacteriemia constante</strong>: bacterias orales que viajan por el torrente sanguíneo hacia el corazón, riñones e hígado. La conexión entre enfermedad dental y daño orgánico sistémico está bien documentada en medicina veterinaria.
              </p>
              <p>
                Los animales <strong>no muestran dolor dental</strong> de la forma en que lo hacemos los humanos. Cuando finalmente presentan síntomas evidentes (dejar de comer, comportamiento cambiado), la enfermedad ya está en un estado avanzado.
              </p>
            </div>
          </div>

          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-6">Señales que debes vigilar</h2>
          <div className="grid sm:grid-cols-2 gap-3 mb-10">
            {SENALES.map((s) => (
              <div key={s} className="flex items-center gap-3 bg-[#f9f7f3] rounded-xl p-4 border border-[#e8e0d0]">
                <div className="w-2 h-2 rounded-full bg-[#187f77] shrink-0" />
                <p className="text-sm text-gray-700">{s}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Prevención */}
      <div className="bg-[#f5f0e8] py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-10 text-center">
            Cómo proteger la salud oral desde la nutrición
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {PREVENCION.map((p) => (
              <div key={p.titulo} className="bg-white rounded-2xl p-6 border border-[#e8e0d0] shadow-sm">
                <div className="text-3xl mb-3">{p.emoji}</div>
                <h3 className="font-semibold text-[#0d4a45] mb-2">{p.titulo}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{p.descripcion}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="bg-[#0d4a45] py-16 px-4">
        <div className="max-w-2xl mx-auto text-center text-white">
          <h2 className="text-2xl font-display font-bold mb-4">
            Empieza hoy — tenemos lo que necesitas
          </h2>
          <p className="text-white/75 mb-8">
            Concentrados con acción dental, snacks especializados y productos de higiene oral disponibles con envío en 24-72h en Pereira y Dosquebradas.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/categorias/higiene" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🪥 Higiene y cuidado dental
            </Link>
            <Link href="/categorias/snacks" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🦴 Snacks dentales
            </Link>
            <a href="https://wa.me/573206876633?text=Hola!%20Necesito%20ayuda%20para%20elegir%20productos%20para%20la%20salud%20dental%20de%20mi%20mascota" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-green-500 text-white rounded-xl font-semibold text-sm hover:bg-green-600 transition-colors flex items-center gap-2">
              <ExternalLink className="w-4 h-4" /> Asesoría por WhatsApp
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
