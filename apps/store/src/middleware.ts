import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

const API_URL = process.env.API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? '';

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const match = pathname.match(/^\/producto\/(.+)$/);
  if (!match) return NextResponse.next();

  const slug = match[1];

  try {
    const res = await fetch(`${API_URL}/v1/search/redirect?old=${encodeURIComponent(slug)}`, {
      next: { revalidate: 3600 },
    });
    if (res.ok) {
      const data = await res.json() as { new_slug?: string };
      if (data.new_slug && data.new_slug !== slug) {
        const url = request.nextUrl.clone();
        url.pathname = `/producto/${data.new_slug}`;
        return NextResponse.redirect(url, { status: 301 });
      }
    }
  } catch {
    // Silently skip — product page will handle not-found naturally
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/producto/:path*'],
};
