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
    sitemap: 'https://bigotesypaticas.com/sitemap.xml',
    host: 'https://bigotesypaticas.com',
  };
}
