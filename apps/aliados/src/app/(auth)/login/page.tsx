'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Handshake, Mail, Lock, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { partnerAuth, ApiError } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';

export default function LoginPage() {
  const router = useRouter();
  const setSession = useAuth((s) => s.setSession);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      const data = await partnerAuth.login(email, password);
      setSession(data.partner_user, data.access_token, data.refresh_token);
      toast.success(`¡Hola, ${data.partner_user.full_name}!`);
      router.replace('/dashboard');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'No se pudo iniciar sesión');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex">
      <div className="hidden lg:flex lg:w-1/2 auth-hero flex-col justify-between p-12 text-white relative overflow-hidden">
        <div
          className="absolute inset-0 opacity-[0.07] pointer-events-none"
          style={{
            backgroundImage:
              "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='80' height='80' viewBox='0 0 80 80'%3E%3Cg fill='%23ffffff'%3E%3Cellipse cx='26' cy='20' rx='5' ry='7'/%3E%3Cellipse cx='38' cy='16' rx='4' ry='6'/%3E%3Cellipse cx='49' cy='20' rx='4' ry='6'/%3E%3Cellipse cx='57' cy='30' rx='4' ry='5'/%3E%3Cellipse cx='38' cy='38' rx='10' ry='13'/%3E%3C/g%3E%3C/svg%3E\")",
            backgroundSize: '90px 90px',
          }}
        />
        <div className="relative">
          <div className="h-12 w-12 rounded-2xl bg-white/15 backdrop-blur flex items-center justify-center mb-6">
            <Handshake className="h-6 w-6 text-white" />
          </div>
          <h1 className="font-display text-4xl font-extrabold leading-tight max-w-md">
            Bienvenido de vuelta a tu panel de aliado
          </h1>
          <p className="text-white/80 mt-4 max-w-sm text-[15px] leading-relaxed">
            Gestiona tu perfil, tus servicios, tu disponibilidad y las reservas que te llegan
            desde la comunidad de Bigotes y Paticas.
          </p>
        </div>
        <p className="relative text-white/50 text-xs">Bigotes y Paticas · Red de Aliados</p>
      </div>

      <div className="flex-1 flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-8">
            <div className="h-10 w-10 rounded-xl bg-primary-700 flex items-center justify-center">
              <Handshake className="h-5 w-5 text-white" />
            </div>
            <p className="font-display text-lg font-extrabold text-primary-800">Panel de Aliados</p>
          </div>

          <h2 className="font-display text-2xl font-bold text-foreground">Inicia sesión</h2>
          <p className="text-muted text-sm mt-1 mb-8">Entra con tu correo y contraseña de aliado.</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label-field">Correo</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-field pl-10"
                  placeholder="tucorreo@negocio.com"
                />
              </div>
            </div>
            <div>
              <label className="label-field">Contraseña</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pl-10"
                  placeholder="••••••••"
                />
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn-primary w-full mt-2">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
              Iniciar sesión
            </button>
          </form>

          <p className="text-center text-sm text-muted mt-8">
            ¿Todavía no eres aliado?{' '}
            <Link href="/registro" className="text-primary-700 font-semibold hover:underline">
              Regístrate aquí
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
