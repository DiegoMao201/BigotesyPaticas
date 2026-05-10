'use client';

import Link from 'next/link';
import { ShoppingBag, Search, Menu, User } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { Button } from '@/components/ui/button';

export function Header() {
  const count = useCart((s) => s.count());

  return (
    <header className="sticky top-0 z-50 w-full glass">
      <div className="container-wide flex h-16 items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-9 h-9 rounded-2xl gradient-brand flex items-center justify-center text-white text-lg shadow-elegant transition-transform group-hover:rotate-6">
            🐾
          </div>
          <div className="font-display font-bold text-lg leading-none tracking-tight">
            Bigotes <span className="text-gradient">y Paticas</span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-8 text-sm font-medium">
          <Link href="/categorias/perros" className="hover:text-brand transition-colors">Perros</Link>
          <Link href="/categorias/gatos" className="hover:text-brand transition-colors">Gatos</Link>
          <Link href="/categorias/accesorios" className="hover:text-brand transition-colors">Accesorios</Link>
          <Link href="/blog" className="hover:text-brand transition-colors">Blog</Link>
          <Link href="/nosotros" className="hover:text-brand transition-colors">Nosotros</Link>
        </nav>

        <div className="flex items-center gap-1">
          <Button variant="ghost" size="icon" aria-label="Buscar">
            <Search className="h-5 w-5" />
          </Button>
          <Link href="/cuenta">
            <Button variant="ghost" size="icon" aria-label="Cuenta">
              <User className="h-5 w-5" />
            </Button>
          </Link>
          <Link href="/carrito" className="relative">
            <Button variant="ghost" size="icon" aria-label="Carrito">
              <ShoppingBag className="h-5 w-5" />
              {count > 0 && (
                <span className="absolute -top-1 -right-1 bg-brand text-white text-[10px] font-semibold w-5 h-5 rounded-full flex items-center justify-center">
                  {count}
                </span>
              )}
            </Button>
          </Link>
          <Button variant="ghost" size="icon" className="md:hidden" aria-label="Menú">
            <Menu className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </header>
  );
}
