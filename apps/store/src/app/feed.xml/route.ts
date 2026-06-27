import { NextResponse } from 'next/server';

const BASE = 'https://bigotesypaticas.com';
const API =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000';

function rfc822(iso: string | null): string {
  if (!iso) return new Date().toUTCString();
  return new Date(iso).toUTCString();
}

function escapeXml(str: string): string {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&apos;');
}

export async function GET() {
  let posts: Array<{
    slug: string;
    title: string;
    excerpt: string | null;
    published_at: string | null;
    updated_at: string | null;
    category: string | null;
    author: string;
  }> = [];

  try {
    const res = await fetch(`${API}/v1/blog/posts?published=true&per_page=50`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json();
      posts = data.posts ?? [];
    }
  } catch {
    // Return empty feed on error
  }

  const items = posts
    .map(
      (p) => `
    <item>
      <title>${escapeXml(p.title)}</title>
      <link>${BASE}/blog/${p.slug}</link>
      <guid isPermaLink="true">${BASE}/blog/${p.slug}</guid>
      <pubDate>${rfc822(p.published_at)}</pubDate>
      ${p.excerpt ? `<description>${escapeXml(p.excerpt)}</description>` : ''}
      ${p.category ? `<category>${escapeXml(p.category)}</category>` : ''}
      <author>${escapeXml(p.author)}</author>
    </item>`,
    )
    .join('');

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
  xmlns:atom="http://www.w3.org/2005/Atom"
  xmlns:content="http://purl.org/rss/1.0/modules/content/">
  <channel>
    <title>Blog Bigotes y Paticas</title>
    <link>${BASE}/blog</link>
    <description>Consejos de veterinarios para mascotas en Pereira y Dosquebradas, Risaralda</description>
    <atom:link href="${BASE}/feed.xml" rel="self" type="application/rss+xml"/>
    <language>es-CO</language>
    <managingEditor>bigotesypaticasdosquebradas@gmail.com (Bigotes y Paticas)</managingEditor>
    <webMaster>bigotesypaticasdosquebradas@gmail.com</webMaster>
    <image>
      <url>https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png</url>
      <title>Blog Bigotes y Paticas</title>
      <link>${BASE}/blog</link>
    </image>
    ${items}
  </channel>
</rss>`;

  return new NextResponse(xml, {
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600, stale-while-revalidate=86400',
    },
  });
}
