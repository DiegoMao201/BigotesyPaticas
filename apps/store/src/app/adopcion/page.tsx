import type { Metadata } from 'next';
import Link from 'next/link';
import { PetPhoto } from '@/components/ui/PetPhoto';
import { Heart, AlertTriangle, PawPrint, ExternalLink, LifeBuoy, HomeIcon, MapPin } from 'lucide-react';
import { storeApi } from '@/lib/api';
import { BreadcrumbSchema, FAQPageSchema } from '@/components/seo/JsonLd';
import { QuickPostForm } from '@/components/adoption/QuickPostForm';
import { SuccessStoryCard } from '@/components/community/SuccessStoryCard';

export const revalidate = 300;

export const metadata: Metadata = {
  title: 'Adopción, Rescate y Mascotas Perdidas en Pereira y Dosquebradas',
  description:
    'Adoptar perro o gato, dar en adopción, reportar mascota perdida o animal encontrado en Pereira y Dosquebradas — todo en un solo foro real de la comunidad Bigotes y Paticas.',
  keywords: [
    'adoptar perro Pereira',
    'adoptar perro Dosquebradas',
    'adoptar gato Pereira',
    'adoptar gato Dosquebradas',
    'adopcion perro Dosquebradas',
    'adopcion de mascotas Pereira',
    'dar en adopcion perro',
    'dar en adopcion gato',
    'rescate de animales Pereira Dosquebradas',
    'rescate perros Risaralda',
    'foro adopción animales',
    'mascota perdida Pereira',
    'mascota encontrada Dosquebradas',
  ],
  alternates: { canonical: 'https://bigotesypaticas.com/adopcion' },
  openGraph: {
    title: 'Adopción, Rescate y Mascotas Perdidas — Pereira y Dosquebradas',
    description: 'El foro real de la comunidad: adopta, da en adopción, reporta o encuentra mascotas en Pereira y Dosquebradas.',
    url: 'https://bigotesypaticas.com/adopcion',
  },
};

const ADOPTION_FAQS = [
  {
    pregunta: '¿Cómo adopto un perro o gato en Pereira o Dosquebradas?',
    respuesta:
      'Revisa la sección "Animales en adopción" de esta página — son publicaciones reales de la comunidad, con foto y contacto directo. Escribe por WhatsApp a quien publicó para coordinar la adopción. También puedes publicar en el foro qué tipo de mascota buscas y que te contacten a ti.',
  },
  {
    pregunta: '¿Cómo doy un perro o gato en adopción?',
    respuesta:
      'Publica en el foro de esta página con tu nombre y teléfono — toma 10 segundos y no necesitas crear una cuenta. Si quieres subir varias fotos y la dirección exacta de entrega, puedes hacer la publicación completa desde el portal de Bigotes y Paticas.',
  },
  {
    pregunta: '¿Qué hago si se me perdió mi mascota en Pereira o Dosquebradas?',
    respuesta:
      'Repórtala en bigotesypaticas.com/mascotas-perdidas con foto, color y tu teléfono de contacto. La comunidad podrá verla y avisarte si la encuentra.',
  },
  {
    pregunta: '¿Qué hago si encontré un perro o gato perdido?',
    respuesta:
      'Publícalo en bigotesypaticas.com/mascotas-encontradas con fotos y el lugar donde lo encontraste, para que su familia pueda reconocerlo y contactarte.',
  },
  {
    pregunta: '¿Es gratis publicar en el foro de adopción?',
    respuesta: 'Sí, publicar en el foro de Bigotes y Paticas es completamente gratis, tanto para dar en adopción como para buscar adoptar.',
  },
];

function timeAgo(iso: string) {
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days < 1) return 'hoy';
  if (days === 1) return 'ayer';
  return `hace ${days} días`;
}

export default async function AdopcionPage() {
  const [offers, wants, foundEvents, successStories] = await Promise.all([
    storeApi.adoptionListings('offer'),
    storeApi.adoptionListings('want'),
    storeApi.foundAnimals(),
    storeApi.adoptionSuccessStories(),
  ]);
  const recentFound = foundEvents.slice(0, 4);

  return (
    <div className="min-h-screen">
      <BreadcrumbSchema
        items={[
          { name: 'Inicio', url: 'https://bigotesypaticas.com' },
          { name: 'Adopción', url: 'https://bigotesypaticas.com/adopcion' },
        ]}
      />
      <FAQPageSchema faqs={ADOPTION_FAQS} />

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
            El centro de la comunidad de Bigotes y Paticas: aquí se publica quién da un animal en adopción, quién
            busca adoptar, quién perdió a su mascota y quién encontró una. Directo, real, sin intermediarios.
          </p>
          <a
            href="#foro"
            className="inline-flex items-center gap-2 mt-6 px-7 py-3.5 bg-white text-[#0d4a45] rounded-xl font-bold text-sm hover:bg-white/90 transition-colors shadow-lg"
          >
            💬 Publicar en el foro ahora
          </a>
        </div>
      </div>

      {/* Aviso: somos un puente, no gestionamos la adopción */}
      <div className="container-wide pt-8">
        <p className="text-center text-xs text-muted-foreground max-w-2xl mx-auto leading-relaxed">
          Bigotes y Paticas conecta a quienes tienen un animal en adopción con quienes desean adoptar — no
          gestionamos ni somos responsables del proceso de adopción en sí. Requisitos, condiciones y seguimiento
          son un acuerdo directo entre las partes.
        </p>
      </div>

      {/* Historias de éxito */}
      {successStories.length > 0 && (
        <div className="container-wide pt-10">
          <div className="flex items-end justify-between gap-3 flex-wrap mb-6">
            <div className="flex items-center gap-2 flex-wrap">
              <h2 className="text-2xl font-display font-bold text-[#0d4a45]">🎉 Historias de éxito</h2>
              <span className="text-sm text-muted-foreground">— así de bien funciona el foro</span>
            </div>
            <Link href="/finales-felices" className="text-sm font-semibold text-[#187f77] hover:underline">Ver todos los finales felices →</Link>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {successStories.map((l) => (
              <SuccessStoryCard
                key={l.id}
                href={`/adopcion/${l.id}`}
                photo={l.photos[0]}
                title={l.title}
                subtitle={l.species ? `${l.species}${l.breed ? ` · ${l.breed}` : ''}` : null}
                headline={l.success_headline ?? (l.post_type === 'want' ? '¡Ya adoptó! 🎉' : '¡Encontró un hogar! 🎉')}
                note={l.resolution_note ?? l.outcome_note ?? ''}
                badge={l.post_type === 'want' ? 'Ya adoptó' : 'Adoptado'}
                date={l.resolved_at}
              />
            ))}
          </div>
        </div>
      )}

      {/* Puente a perdidos / encontrados */}
      <div className="container-wide pt-12">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Link
            href="/mascotas-perdidas"
            className="group flex items-center gap-4 rounded-3xl p-6 text-white transition-transform hover:-translate-y-1"
            style={{ background: 'linear-gradient(135deg, #ff7a63, #c62f28)' }}
          >
            <div className="h-14 w-14 rounded-2xl bg-white/15 flex items-center justify-center shrink-0">
              <LifeBuoy className="h-7 w-7" />
            </div>
            <div>
              <p className="font-display font-bold text-lg">¿Se te perdió tu mascota?</p>
              <p className="text-sm text-white/85">Repórtala y que la comunidad te ayude a buscarla →</p>
            </div>
          </Link>
          <Link
            href="/mascotas-encontradas"
            className="group flex items-center gap-4 rounded-3xl p-6 text-white transition-transform hover:-translate-y-1"
            style={{ background: 'linear-gradient(135deg, #2fc4a8, #085041)' }}
          >
            <div className="h-14 w-14 rounded-2xl bg-white/15 flex items-center justify-center shrink-0">
              <HomeIcon className="h-7 w-7" />
            </div>
            <div>
              <p className="font-display font-bold text-lg">¿Encontraste un animalito?</p>
              <p className="text-sm text-white/85">Publica sus fotos para ayudarlo a volver a casa →</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Encontrados recientemente (vitrina) */}
      {recentFound.length > 0 && (
        <div className="container-wide py-14">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-display font-bold text-[#0d4a45]">🐾 Encontrados recientemente</h2>
            <Link href="/mascotas-encontradas" className="text-sm font-semibold text-[#187f77] hover:underline">
              Ver todos →
            </Link>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {recentFound.map((ev) => (
              <Link
                key={ev.id}
                href={`/mascotas-encontradas/${ev.id}`}
                className="group block rounded-2xl overflow-hidden border border-border hover:shadow-lg transition-shadow"
              >
                {ev.cover_thumb_url ? (
                  <div className="relative w-full h-32 overflow-hidden bg-[#F8F9FA]">
                    <PetPhoto
                      src={ev.cover_thumb_url}
                      alt={ev.title}
                      sizes="(max-width: 768px) 50vw, 25vw"
                      className="group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                ) : (
                  <div className="w-full h-32 bg-gradient-to-br from-[#187f77] to-[#085041] flex items-center justify-center">
                    <PawPrint className="h-8 w-8 text-white/70" />
                  </div>
                )}
                <div className="p-3">
                  <p className="text-xs font-semibold line-clamp-1">{ev.title}</p>
                  {ev.address && (
                    <p className="text-[11px] text-muted-foreground inline-flex items-center gap-1 mt-0.5 line-clamp-1">
                      <MapPin className="h-2.5 w-2.5 shrink-0" /> {ev.address}
                    </p>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Foro rápido */}
      <div id="foro" className="bg-[#f5f0e8] py-14 px-4 scroll-mt-6">
        <div className="max-w-2xl mx-auto">
          <QuickPostForm />
          <p className="text-center text-xs text-gray-500 mt-4">
            ¿Vas a dar en adopción y quieres subir varias fotos con dirección exacta?{' '}
            <a href="https://mi.bigotesypaticas.com/adopcion/publicar" className="underline font-medium">
              Publica la versión completa aquí
            </a>
            .
          </p>
        </div>
      </div>

      {/* En adopción */}
      <div className="container-wide py-14">
        <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-6">🏠 Animales en adopción</h2>
        {offers.length === 0 ? (
          <p className="text-muted-foreground">Todavía no hay publicaciones abiertas. ¡Sé el primero!</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {offers.map((l) => (
              <Link
                key={l.id}
                href={`/adopcion/${l.id}`}
                className="group block rounded-3xl border border-border bg-card overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-300"
              >
                {l.photos[0] ? (
                  <div className="relative w-full h-48 overflow-hidden bg-[#F8F9FA]">
                    <PetPhoto
                      src={l.photos[0]}
                      alt={l.title}
                      sizes="(max-width: 768px) 50vw, 33vw"
                      className="group-hover:scale-105 transition-transform duration-300"
                    />
                  </div>
                ) : (
                  <div className="w-full h-48 bg-gradient-to-br from-[#187f77] to-[#085041] flex items-center justify-center text-6xl">
                    <PawPrint className="h-12 w-12 text-white/70" />
                  </div>
                )}
                <div className="p-5">
                  <h3 className="font-display font-bold text-lg line-clamp-1 mb-1">{l.title}</h3>
                  {(l.species || l.breed) && (
                    <p className="text-sm text-muted-foreground capitalize mb-2 line-clamp-1">
                      {l.species}{l.breed ? ` · ${l.breed}` : ''}
                    </p>
                  )}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                    <span>{timeAgo(l.created_at)}</span>
                    {l.reporter_name && <span>· Publicó {l.reporter_name}</span>}
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Buscan adoptar */}
      <div className="bg-[#f5f0e8] py-14 px-4">
        <div className="container-wide">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-6">🔍 Buscan adoptar</h2>
          {wants.length === 0 ? (
            <p className="text-gray-600">Todavía no hay solicitudes publicadas.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {wants.map((l) => (
                <Link
                  key={l.id}
                  href={`/adopcion/${l.id}`}
                  className="block rounded-2xl bg-white border border-border p-5 hover:shadow-md transition-shadow"
                >
                  <h3 className="font-display font-bold mb-1">{l.title}</h3>
                  {l.species && <p className="text-sm text-muted-foreground capitalize mb-2">{l.species}{l.breed ? ` · ${l.breed}` : ''}</p>}
                  <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                    <span>{timeAgo(l.created_at)}</span>
                    {l.reporter_name && <span>· Publicó {l.reporter_name}</span>}
                  </div>
                </Link>
              ))}
            </div>
          )}
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
                  Con un perro o gato adulto sabes de entrada su tamaño, temperamento y energía. No hay sorpresas de "se me creció más de lo esperado".
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
                  Cada compra de cachorro de criadero informal (la mayoría en Risaralda no están certificados) financia condiciones de reproducción intensiva. Mientras tanto, miles de animales con exactamente las mismas capacidades esperan un hogar.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Preguntas frecuentes */}
      <div className="bg-[#f5f0e8] py-16 px-4">
        <div className="max-w-2xl mx-auto">
          <h2 className="text-2xl font-display font-bold text-[#0d4a45] mb-8 text-center">Preguntas frecuentes</h2>
          <div className="space-y-5">
            {ADOPTION_FAQS.map((f) => (
              <div key={f.pregunta} className="rounded-2xl bg-white p-5 border border-border">
                <h3 className="font-semibold text-[#0d4a45] mb-1.5">{f.pregunta}</h3>
                <p className="text-sm text-gray-600 leading-relaxed">{f.respuesta}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* CTA — si ya adoptaste */}
      <div className="pb-16 px-4">
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
