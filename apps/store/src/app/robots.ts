import type { MetadataRoute } from 'next';

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [{ userAgent: '*', allow: '/', disallow: ['/admin', '/cuenta', '/checkout'] }],
    sitemap: 'https://bigotesypaticas.com/sitemap.xml',
  };
}
