import { redirect } from 'next/navigation';

export default function RootPage() {
  // Redirige a /login en lugar de /dashboard para que Google no encuentre
  // un redirect chain (/ → /dashboard → client-side → /login).
  // El (portal)/layout.tsx redirige a /login si no hay sesión activa.
  redirect('/login');
}
