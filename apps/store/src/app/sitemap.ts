import type { MetadataRoute } from 'next';

export default function sitemap(): MetadataRoute.Sitemap {
  const base = 'https://bigotesypaticas.com';
  const now = new Date();
  return [
    { url: base, lastModified: now, changeFrequency: 'daily', priority: 1 },
    { url: `${base}/categorias/perros`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${base}/categorias/gatos`, lastModified: now, changeFrequency: 'weekly', priority: 0.9 },
    { url: `${base}/categorias/accesorios`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${base}/nosotros`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
  ];
}
