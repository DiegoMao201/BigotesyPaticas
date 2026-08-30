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
      { protocol: 'https', hostname: '**.googleusercontent.com' },
    ],
  },
  async headers() {
    return [
      {
        // Iconos, manifest y demás estáticos servidos desde /public no cambian
        // de contenido sin un rename/redeploy — cache larga es segura.
        source: '/:path(icon-.*\\.png|apple-touch-icon\\.png|favicon\\.ico|icon\\.svg|site\\.webmanifest|opengraph-image\\.png)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, immutable' },
        ],
      },
    ];
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
      // /legal/privacidad no existe — la página real es /politica-privacidad
      { source: '/legal/privacidad', destination: '/politica-privacidad', permanent: true },
      // /pet-shop-pereira era contenido casi duplicado de /pereira-dosquebradas-mascotas
      // (mismas marcas, mismo FAQ, sin enlaces internos) — Google lo marcaba como
      // canónica distinta / rastreada sin indexar. Se consolida en una sola página.
      { source: '/pet-shop-pereira', destination: '/pereira-dosquebradas-mascotas', permanent: true },
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
