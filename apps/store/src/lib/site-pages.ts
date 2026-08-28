/** Páginas de contenido (no-producto) que el buscador del sitio también debe encontrar. */
export interface SitePage {
  title: string;
  description: string;
  href: string;
  emoji: string;
  keywords: string[];
}

export const SITE_PAGES: SitePage[] = [
  {
    title: 'Foro de Adopción',
    description: 'Animales en adopción y personas buscando adoptar en Pereira y Dosquebradas.',
    href: '/adopcion',
    emoji: '🏠',
    keywords: ['adopcion', 'adopción', 'adoptar', 'foro', 'regalar mascota', 'dar en adopcion'],
  },
  {
    title: 'Mascotas Perdidas',
    description: 'Reportes de perros y gatos perdidos en Pereira y Dosquebradas.',
    href: '/mascotas-perdidas',
    emoji: '🐾',
    keywords: ['perdid', 'se perdio', 'se me perdio', 'extraviad', 'mascota perdida'],
  },
  {
    title: 'Animales Encontrados',
    description: 'Animales rescatados que están a salvo, esperando a su familia.',
    href: '/mascotas-encontradas',
    emoji: '🐕',
    keywords: ['encontrad', 'encontre', 'rescatad', 'rescate', 'me encontre un perro', 'me encontre un gato'],
  },
  {
    title: 'Blog de mascotas',
    description: 'Guías y consejos veterinarios para el cuidado de tu mascota.',
    href: '/blog',
    emoji: '📝',
    keywords: ['blog', 'consejos', 'guia', 'articulo'],
  },
  {
    title: 'Contáctanos',
    description: 'Escríbenos por WhatsApp, dirección y horarios de atención.',
    href: '/contacto',
    emoji: '📍',
    keywords: ['contacto', 'direccion', 'ubicacion', 'horario', 'telefono', 'whatsapp'],
  },
];

function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, ''); // quita tildes
}

export function matchSitePages(query: string): SitePage[] {
  const q = normalize(query.trim());
  if (!q) return [];
  return SITE_PAGES.filter((page) =>
    page.keywords.some((k) => {
      const nk = normalize(k);
      return q.includes(nk) || nk.includes(q);
    })
  );
}
