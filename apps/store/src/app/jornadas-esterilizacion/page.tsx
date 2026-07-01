import type { Metadata } from 'next';
import Link from 'next/link';
import { Calendar, Shield, AlertTriangle, ExternalLink, Phone } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Jornadas de esterilización en Pereira y Dosquebradas — Bigotes y Paticas',
  description:
    'Información sobre jornadas de esterilización subsidiada en Pereira y Dosquebradas. Por qué esterilizar a tu mascota es el acto más responsable que puedes hacer.',
  alternates: { canonical: 'https://bigotesypaticas.com/jornadas-esterilizacion' },
  openGraph: {
    title: 'Jornadas de esterilización en Pereira y Dosquebradas',
    description:
      'Una hembra sin esterilizar puede ser ancestro de 67.000 descendientes en 6 años. Conoce las jornadas subsidiadas en Risaralda.',
    url: 'https://bigotesypaticas.com/jornadas-esterilizacion',
  },
};

const STATS = [
  { cifra: '~45.000', label: 'perros en condición de calle en Risaralda' },
  { cifra: '73%', label: 'de camadas callejeras no fueron planificadas' },
  { cifra: '67.000', label: 'descendientes posibles de 1 hembra en 6 años' },
  { cifra: '90%', label: 'reducción de tumores mamarios si se esteriliza antes del primer celo' },
];

const BENEFICIOS = [
  {
    titulo: 'Previene enfermedades graves',
    descripcion:
      'En hembras: elimina el riesgo de piometra (infección uterina mortal) y reduce hasta un 90% el riesgo de tumores mamarios si se hace antes del primer celo. En machos: previene hiperplasia prostática y tumores testiculares.',
    icono: '🛡️',
  },
  {
    titulo: 'Reduce comportamientos problemáticos',
    descripcion:
      'Machos no esterilizados marcan territorio constantemente, se escapan buscando hembras en celo y son más agresivos. La esterilización reduce significativamente estos comportamientos sin cambiar la personalidad del animal.',
    icono: '🧠',
  },
  {
    titulo: 'Mayor esperanza de vida',
    descripcion:
      'Estudios veterinarios documentan que perros y gatos esterilizados viven en promedio entre 1 y 3 años más que los no esterilizados, al eliminar los riesgos reproductivos y reducir el estrés hormonal crónico.',
    icono: '❤️',
  },
  {
    titulo: 'Corta el ciclo de abandono',
    descripcion:
      'La mayoría de camadas no planificadas terminan abandonadas. Esterilizar es la única medida que reduce la sobrepoblación de manera efectiva y permanente. Las campañas de adopción ayudan, pero no alcanzan si no se controla la reproducción.',
    icono: '🔄',
  },
];

const DONDE = [
  {
    nombre: 'Secretaría de Salud de Pereira',
    info: 'El municipio coordina jornadas de esterilización subsidiada periódicamente. Comunícate directamente para conocer fechas y requisitos.',
    contacto: 'salud.pereira.gov.co · línea 195',
  },
  {
    nombre: 'Secretaría de Salud de Dosquebradas',
    info: 'El municipio tiene su propio programa de esterilización con costos subsidiados. Los cupos son limitados y se asignan por orden de solicitud.',
    contacto: 'dosquebradas.gov.co',
  },
  {
    nombre: 'Clínicas Veterinarias con convenio',
    info: 'Varias clínicas veterinarias en Pereira y Dosquebradas trabajan con tarifas especiales en convenio con las alcaldías y fundaciones. Consulta en tu clínica más cercana.',
    contacto: 'Pregunta por convenios con la Secretaría de Salud',
  },
  {
    nombre: 'ONG locales — FUNPAZ y AANIMALES',
    info: 'Estas organizaciones gestionan jornadas específicas con donaciones y apoyo de clínicas aliadas. Están activas en redes sociales con información actualizada de fechas.',
    contacto: '@funpazrisaralda · @aanimalesrisaralda',
  },
];

export default function JornadasEsterilizacionPage() {
  return (
    <div className="min-h-screen">
      {/* Hero */}
      <div className="bg-gradient-to-b from-[#0d4a45] to-[#187f77] text-white py-20 px-4">
        <div className="max-w-3xl mx-auto text-center">
          <div className="flex justify-center mb-6">
            <div className="w-16 h-16 bg-white/10 rounded-full flex items-center justify-center">
              <Shield className="w-8 h-8 text-white" />
            </div>
          </div>
          <h1 className="text-3xl md:text-5xl font-display font-extrabold mb-4 leading-tight">
            Esterilizar no es mutilación.<br />Es el acto más responsable.
          </h1>
          <p className="text-lg text-white/80 max-w-2xl mx-auto">
            Una hembra sin esterilizar puede ser origen de hasta <strong className="text-white">67.000 descendientes en solo 6 años</strong>. En Risaralda hay aproximadamente 45.000 perros en condición de calle. La matemática es clara.
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
          <p className="text-center text-xs text-gray-400 mt-6">
            Fuentes: Secretaría de Salud de Pereira · ONG Risaralda · Estudios veterinarios AVMA
          </p>
        </div>
      </div>

      {/* Beneficios */}
      <div className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-10 text-center">
            Por qué la esterilización transforma la vida de tu mascota
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {BENEFICIOS.map((b) => (
              <div key={b.titulo} className="bg-[#f9f7f3] rounded-2xl p-6 border border-[#e8e0d0]">
                <div className="text-3xl mb-3">{b.icono}</div>
                <h3 className="font-semibold text-[#0d4a45] mb-2">{b.titulo}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{b.descripcion}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Mito vs Realidad */}
      <div className="bg-amber-50 border-y border-amber-200 py-12 px-4">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center gap-3 mb-6">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <h2 className="text-lg font-bold text-amber-800">Mitos frecuentes que debes conocer</h2>
          </div>
          <div className="space-y-4">
            {[
              { mito: '"Mi perro va a engordar"', realidad: 'El metabolismo cambia ligeramente, pero el peso se controla con alimentación adecuada. Un perro bien nutrido y con ejercicio mantiene su peso ideal.' },
              { mito: '"Necesita tener una camada primero"', realidad: 'Falso. No existe ningún beneficio médico ni conductual en que una hembra tenga una camada antes de ser esterilizada. Es un mito cultural sin base científica.' },
              { mito: '"Va a perder su carácter"', realidad: 'La personalidad del animal no cambia. Lo que desaparece son los comportamientos hormonales (marcación, escapadas, agresividad reproductiva) que muchos confunden con "carácter".' },
            ].map((item) => (
              <div key={item.mito} className="bg-white rounded-xl p-5 border border-amber-200">
                <p className="font-semibold text-amber-800 mb-1 text-sm">{item.mito}</p>
                <p className="text-sm text-gray-600">{item.realidad}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dónde hacerlo en Pereira */}
      <div className="py-16 px-4">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-3 text-center">
            Jornadas subsidiadas en Pereira y Dosquebradas
          </h2>
          <p className="text-center text-gray-500 text-sm mb-10">
            Las fechas y cupos varían. Comunícate directamente con cada entidad para confirmar disponibilidad.
          </p>
          <div className="grid md:grid-cols-2 gap-5">
            {DONDE.map((d) => (
              <div key={d.nombre} className="bg-[#f9f7f3] rounded-2xl p-6 border border-[#e8e0d0]">
                <div className="flex items-start gap-3 mb-2">
                  <Calendar className="w-5 h-5 text-[#187f77] shrink-0 mt-0.5" />
                  <h3 className="font-semibold text-[#0d4a45] text-sm">{d.nombre}</h3>
                </div>
                <p className="text-sm text-gray-600 mb-3 leading-relaxed">{d.info}</p>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Phone className="w-3.5 h-3.5" />
                  <span>{d.contacto}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="bg-[#0d4a45] py-16 px-4">
        <div className="max-w-2xl mx-auto text-center text-white">
          <h2 className="text-2xl font-display font-bold mb-4">
            ¿Tu mascota ya está esterilizada? Cuídala al máximo.
          </h2>
          <p className="text-white/75 mb-8">
            Un animal sano necesita nutrición de calidad en cada etapa de su vida. Te ayudamos a elegir el alimento correcto.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Link href="/categorias/perros" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🐕 Alimentos para perros
            </Link>
            <Link href="/categorias/gatos" className="px-6 py-3 bg-white text-[#0d4a45] rounded-xl font-semibold text-sm hover:bg-white/90 transition-colors">
              🐈 Alimentos para gatos
            </Link>
            <a href="https://wa.me/573206876633?text=Hola!%20Quiero%20información%20sobre%20esterilización%20o%20productos%20para%20mi%20mascota" target="_blank" rel="noopener noreferrer"
              className="px-6 py-3 bg-green-500 text-white rounded-xl font-semibold text-sm hover:bg-green-600 transition-colors flex items-center gap-2">
              <ExternalLink className="w-4 h-4" /> Hablar con nosotros
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
