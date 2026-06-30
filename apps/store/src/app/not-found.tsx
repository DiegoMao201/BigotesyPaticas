import Link from 'next/link';
import { Home, Search, MessageCircle } from 'lucide-react';

export const metadata = {
  title: 'Página no encontrada — Bigotes y Paticas',
};

export default function NotFound() {
  return (
    <div className="container-tight py-24 flex flex-col items-center text-center gap-6">
      <p className="text-7xl font-display font-extrabold text-brand-100">404</p>
      <div className="space-y-2">
        <h1 className="text-3xl font-display font-bold">Página no encontrada</h1>
        <p className="text-muted-foreground text-lg max-w-md">
          Este enlace no existe o fue movido. Explora nuestra tienda o escríbenos.
        </p>
      </div>

      <div className="flex flex-wrap justify-center gap-3 mt-2">
        <Link
          href="/"
          className="flex items-center gap-2 px-5 py-2.5 bg-brand-600 text-white rounded-xl font-semibold text-sm hover:bg-brand-700 transition-colors"
        >
          <Home className="h-4 w-4" /> Ir al inicio
        </Link>
        <Link
          href="/categorias/todos"
          className="flex items-center gap-2 px-5 py-2.5 border border-border rounded-xl font-semibold text-sm hover:bg-accent transition-colors"
        >
          <Search className="h-4 w-4" /> Ver productos
        </Link>
        <a
          href="https://wa.me/573206876633?text=Hola!%20No%20encontré%20lo%20que%20buscaba"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-5 py-2.5 bg-green-500 text-white rounded-xl font-semibold text-sm hover:bg-green-600 transition-colors"
        >
          <MessageCircle className="h-4 w-4" /> WhatsApp
        </a>
      </div>
    </div>
  );
}
