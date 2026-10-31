/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: { optimizePackageImports: ['lucide-react', 'framer-motion'] },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: '**.bigotesypaticas.com' },
      { protocol: 'https', hostname: 'cdn.bigotesypaticas.com' },
      { protocol: 'https', hostname: '**.digitaloceanspaces.com' },
      { protocol: 'https', hostname: 'catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com' },
      { protocol: 'https', hostname: 'api.bigotesypaticas.com' },
    ],
  },
  async rewrites() {
    // 30-oct-2026: el servidor Next le hablaba a la API por la URL pública (salía a
    // Cloudflare y volvía: 251 ms por llamada contra 16 ms por la red interna de
    // Docker). API_BASE_URL apunta al alias interno `bp-api`; el navegador sigue
    // usando NEXT_PUBLIC_API_BASE_URL.
    const api = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    return [
      { source: '/api/v1/:path*', destination: `${api}/v1/:path*` },
      { source: '/media/:path*', destination: `${api}/media/:path*` },
    ];
  },
  async headers() {
    return [
      {
        source: '/(.*)',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        ],
      },
    ];
  },
};
export default nextConfig;
