'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { ShoppingBag, Search, Menu, User, X } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/brand/Logo';

export function Header() {
  const count = useCart((s) => s.count());
  const router = useRouter();
  const [searchOpen, setSearchOpen] = useState(false);
  const [query, setQuery] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (searchOpen) setTimeout(() => inputRef.current?.focus(), 50);
  }, [searchOpen]);

  function submitSearch(e: React.FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) return;
    router.push(`/buscar?q=${encodeURIComponent(q)}`);
    setSearchOpen(false);
    setQuery('');
  }

  return (
    <header className="sticky top-0 z-50 w-full glass border-b border-border/50">
      <div className="container-wide flex h-16 items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-3 group shrink-0">
          <Logo size={48} variant="header" priority />
          <span className="font-display font-bold text-lg leading-none tracking-tight hidden md:inline">
            Bigotes <span className="text-gradient">y Paticas</span>
          </span>
        </Link>

        {/* Nav central (desktop) */}
        {!searchOpen && (
          <nav className="hidden md:flex items-center gap-7 text-sm font-medium">
            <Link href="/categorias/perros" className="hover:text-brand transition-colors">Perros</Link>
            <Link href="/categorias/gatos" className="hover:text-brand transition-colors">Gatos</Link>
            <Link href="/categorias/accesorios" className="hover:text-brand transition-colors">Accesorios</Link>
            <Link href="/categorias/snacks" className="hover:text-brand transition-colors">Snacks</Link>
            <Link href="/blog" className="hover:text-brand transition-colors">Blog</Link>
            <Link href="/nosotros" className="hover:text-brand transition-colors">Nosotros</Link>
          </nav>
        )}

        {/* Search expandida (desktop) */}
        {searchOpen && (
          <form onSubmit={submitSearch} className="hidden md:flex flex-1 max-w-md mx-8 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar productos…"
              className="pl-9 pr-10"
            />
            <button type="button" onClick={() => { setSearchOpen(false); setQuery(''); }} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground">
              <X className="h-4 w-4" />
            </button>
          </form>
        )}

        {/* Actions */}
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="icon"
            aria-label="Buscar"
            onClick={() => setSearchOpen((v) => !v)}
            className={cn(searchOpen && 'bg-brand/10 text-brand')}
          >
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
                <span className="absolute -top-1 -right-1 gradient-brand text-white text-[10px] font-semibold w-5 h-5 rounded-full flex items-center justify-center shadow-sm">
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

      {/* Search mobile */}
      {searchOpen && (
        <div className="md:hidden border-t border-border/50 px-4 py-3">
          <form onSubmit={submitSearch} className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Buscar productos…"
              className="pl-9"
            />
          </form>
        </div>
      )}
    </header>
  );
}

