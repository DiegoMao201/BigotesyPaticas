'use client';

import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { ShoppingBag, Search, Menu, User, X, ChevronRight, MessageCircle } from 'lucide-react';
import { useCart } from '@/lib/cart-store';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Logo } from '@/components/brand/Logo';
import { useMounted } from '@/lib/use-mounted';

// Enlaces del menú móvil. Antes las 3 rayitas no tenían acción: el botón existía
// pero no abría nada (Diego, 27-sep-2026: "las 3 rayitas del celular no funcionan").
const MENU_MOVIL = [
  { href: '/categorias/perros', label: 'Perros', emoji: '🐶' },
  { href: '/categorias/gatos', label: 'Gatos', emoji: '🐱' },
  { href: '/categorias/snacks', label: 'Snacks', emoji: '🦴' },
  { href: '/categorias/accesorios', label: 'Accesorios', emoji: '🎾' },
  { href: '/categorias/todos', label: 'Todo el catálogo', emoji: '🛍️' },
  { href: '/adopcion', label: 'Adopción', emoji: '🏠' },
  { href: '/blog', label: 'Blog', emoji: '📖' },
  { href: '/noticias', label: 'Noticias', emoji: '📰' },
  { href: '/nosotros', label: 'Nosotros', emoji: '💚' },
  { href: '/contacto', label: 'Contacto y ubicación', emoji: '📍' },
];

// Icono-enlace del encabezado. Antes era <Link><Button/></Link>: un botón DENTRO de un
// enlace, que en algunos celulares no responde al toque. Ahora el enlace es el botón.
const ICONO = 'relative inline-flex h-11 w-11 items-center justify-center rounded-full hover:bg-accent active:scale-[0.97] transition-all';

export function Header() {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  // se cierra solo al navegar, y la página de atrás no se desplaza mientras está abierto
  useEffect(() => { setMenuOpen(false); }, [pathname]);
  useEffect(() => {
    document.body.style.overflow = menuOpen ? 'hidden' : '';
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);
  const mounted = useMounted();
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
            <Link href="/noticias" className="hover:text-teal-700 transition-colors">Noticias</Link>
            <Link href="/adopcion" className="text-[#187f77] font-semibold hover:text-[#0d4a45] transition-colors">🏠 Adopción</Link>
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
          <Link href="/cuenta" aria-label="Cuenta" className={ICONO}>
            <User className="h-5 w-5" />
          </Link>
          <Link href="/carrito" aria-label="Carrito" className={ICONO}>
            <ShoppingBag className="h-5 w-5" />
            {mounted && count > 0 && (
              <span className="absolute top-0 right-0 gradient-brand text-white text-[10px] font-semibold w-5 h-5 rounded-full flex items-center justify-center shadow-sm">
                {count}
              </span>
            )}
          </Link>
          <button
            type="button"
            aria-label="Menú"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen(true)}
            className={cn(ICONO, 'md:hidden')}
          >
            <Menu className="h-5 w-5" />
          </button>
        </div>
      </div>

      {/* Menú móvil: panel que entra desde la derecha. Va por PORTAL al <body>: el
          encabezado tiene backdrop-filter (clase glass) y eso convierte al header en el
          contenedor de los `fixed`, así que el panel quedaba encerrado en sus 64 px. */}
      {menuOpen && typeof document !== 'undefined' && createPortal(
        <div className="md:hidden fixed inset-0 z-[70]" role="dialog" aria-modal="true" aria-label="Menú">
          <button aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} className="absolute inset-0 bg-black/40 animate-in fade-in" />
          <nav className="absolute right-0 top-0 h-full w-[86%] max-w-sm bg-white shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            <div className="flex items-center justify-between px-5 h-16 border-b border-gray-100">
              <span className="font-display font-bold text-lg text-[#0d4a45]">Bigotes y Paticas</span>
              <button aria-label="Cerrar menú" onClick={() => setMenuOpen(false)} className={ICONO}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto py-2">
              {MENU_MOVIL.map((l) => (
                <Link
                  key={l.href}
                  href={l.href}
                  onClick={() => setMenuOpen(false)}
                  className={cn(
                    'flex items-center gap-3 px-5 py-3.5 text-base font-semibold text-gray-800 active:bg-gray-50',
                    pathname === l.href && 'text-[#187f77] bg-[#187f77]/5',
                  )}
                >
                  <span className="text-xl w-7 text-center">{l.emoji}</span>
                  <span className="flex-1">{l.label}</span>
                  <ChevronRight className="h-4 w-4 text-gray-300" />
                </Link>
              ))}
            </div>
            <div className="p-4 border-t border-gray-100 space-y-2.5">
              <Link
                href="/cuenta"
                onClick={() => setMenuOpen(false)}
                className="flex items-center justify-center gap-2 w-full h-12 rounded-2xl bg-[#187f77] text-white font-bold"
              >
                <User className="h-5 w-5" /> Mi cuenta · Portal
              </Link>
              <a
                href="https://wa.me/573206876633"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-2 w-full h-12 rounded-2xl bg-green-500 text-white font-bold"
              >
                <MessageCircle className="h-5 w-5" /> Pedir por WhatsApp
              </a>
            </div>
          </nav>
        </div>,
        document.body,
      )}

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

