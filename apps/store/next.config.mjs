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
      { protocol: 'https', hostname: 'images.unsplash.com' },
    ],
  },
  async redirects() {
    return [
      // www → non-www (301 permanente para que Google unifique autoridad SEO)
      {
        source: '/:path*',
        has: [{ type: 'host', value: 'www.bigotesypaticas.com' }],
        destination: 'https://bigotesypaticas.com/:path*',
        permanent: true,
      },
      // /ofertas no existe — redirige a catálogo general
      { source: '/ofertas', destination: '/categorias/todos', permanent: true },
      // Post Jul 2 publicado con producto inexistente en catálogo
      { source: '/producto/royal-canin-maxi-adult-15kg', destination: '/categorias/perros', permanent: false },
    ];
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
    return [{ source: '/api/v1/:path*', destination: `${api}/v1/:path*` }];
  },
};
export default nextConfig;
