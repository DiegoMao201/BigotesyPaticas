import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/admin', '/api/v1', '/cuenta', '/checkout', '/carrito', '/buscar'],
      },
      {
        userAgent: 'GPTBot',
        disallow: '/',
      },
    ],
    sitemap: 'https://bigotesypaticas.com/sitemap.xml',
    host: 'https://bigotesypaticas.com',
  };
}
