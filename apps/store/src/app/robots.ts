import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin', '/api/v1', '/cuenta', '/checkout', '/carrito', '/buscar'],
      },
      // 18-sep-2026: estaba BLOQUEADO GPTBot y por eso ChatGPT no conocía la tienda.
      // Diego lo comprobó: preguntó por una tienda de mascotas con domicilio en
      // Dosquebradas y salieron seis competidores, nosotros no. Hoy mucha gente
      // busca dónde comprar preguntándole a una IA: cerrarles la puerta es
      // regalar esas búsquedas. Se permite explícitamente a los buscadores de IA.
      { userAgent: 'GPTBot', allow: '/' },
      { userAgent: 'OAI-SearchBot', allow: '/' },
      { userAgent: 'ChatGPT-User', allow: '/' },
      { userAgent: 'PerplexityBot', allow: '/' },
      { userAgent: 'ClaudeBot', allow: '/' },
      { userAgent: 'Google-Extended', allow: '/' },
    ],
    // 24-oct-2026: /llms.txt estaba declarado aquí como sitemap y no lo es (es texto
    // plano, no XML de sitemaps): Search Console y Bing lo marcan como sitemap con
    // errores. Los modelos de lenguaje lo buscan solos en /llms.txt, que es la ruta
    // estándar, y va enlazado en el <head> de todas las páginas (layout.tsx).
    sitemap: 'https://bigotesypaticas.com/sitemap.xml',
    host: 'https://bigotesypaticas.com',
  };
}
