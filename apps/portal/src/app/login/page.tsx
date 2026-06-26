'use client';

import { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Phone, CreditCard, ArrowRight, Loader2 } from 'lucide-react';
import { auth, pets, referral as referralApi, type LoginResponse } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

type Step = 'login' | 'onboarding';

const PAWS = [
  { left: '8%',  top: '18%', delay: 0,   size: 18 },
  { left: '78%', top: '12%', delay: 0.8, size: 14 },
  { left: '22%', top: '55%', delay: 1.6, size: 22 },
  { left: '88%', top: '42%', delay: 0.4, size: 16 },
  { left: '55%', top: '28%', delay: 2.2, size: 12 },
  { left: '40%', top: '70%', delay: 1.1, size: 20 },
  { left: '65%', top: '62%', delay: 2.8, size: 14 },
  { left: '12%', top: '80%', delay: 3.4, size: 16 },
];

function LoginPageInner() {
  const router = useRouter();
  const qc = useQueryClient();
  const { setCustomer } = useAuthStore();
  const searchParams = useSearchParams();
  const refCode = searchParams.get('ref') ?? null;

  const [step, setStep] = useState<Step>('login');
  const [loginData, setLoginData] = useState<LoginResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const [doc, setDoc] = useState('');
  const [phone, setPhone] = useState('');

  async function handleLogin(e: React.FormEvent) {
    e.preventDefault();
    if (!doc.trim() || !phone.trim()) {
      toast.error('Ingresa tu cédula y teléfono');
      return;
    }
    setLoading(true);
    try {
      const resp = await auth.login(doc.trim(), phone.trim());
      setLoginData(resp);

      if (resp.has_pets && !resp.full_name) {
        setStep('onboarding');
        return;
      }

      const me = await auth.me();
      setCustomer(me);
      qc.setQueryData(['portal-me'], me);

      if (refCode && resp.status === 'new') {
        referralApi.applyCode(refCode).catch(() => {});
      }

      if (!me.full_name) {
        setStep('onboarding');
        return;
      }

      router.replace('/dashboard');
    } catch (err: any) {
      toast.error(err.message ?? 'Error al iniciar sesión');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen overflow-hidden bg-teal-900">
      {/* VIDEO de fondo */}
      <video
        autoPlay
        muted
        loop
        playsInline
        preload="auto"
        className="absolute inset-0 w-full h-full object-cover opacity-70"
      >
        <source src="/videos/login-bg.mp4" type="video/mp4" />
      </video>

      {/* Overlay degradado teal */}
      <div className="absolute inset-0 bg-gradient-to-b from-teal-900/50 via-teal-800/30 to-teal-950/80" />

      {/* Huellas flotantes */}
      {PAWS.map((p, i) => (
        <motion.span
          key={i}
          className="absolute pointer-events-none select-none text-white"
          style={{ left: p.left, top: p.top, fontSize: p.size, opacity: 0 }}
          animate={{ opacity: [0, 0.35, 0.35, 0], y: [0, -35, -70, -110] }}
          transition={{ duration: 7, delay: p.delay, repeat: Infinity, ease: 'easeOut' }}
        >
          🐾
        </motion.span>
      ))}

      {/* Logo + título */}
      <motion.div
        className="relative z-10 flex flex-col items-center pt-16 pb-4"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7 }}
      >
        <motion.div
          className="w-20 h-20 rounded-3xl bg-white/15 backdrop-blur-md border border-white/20 flex items-center justify-center text-4xl mb-4 shadow-2xl"
          animate={{ y: [0, -7, 0] }}
          transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
        >
          🐾
        </motion.div>
        <h1 className="text-white text-3xl font-bold tracking-tight drop-shadow-lg">
          Bigotes y Paticas
        </h1>
        <p className="text-white/70 text-sm mt-1">Tu portal de mascotas</p>
      </motion.div>

      {/* Card glass deslizante desde abajo */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 bg-white rounded-t-[2rem] px-6 pt-7 pb-12 shadow-2xl z-10"
        initial={{ y: 340 }}
        animate={{ y: 0 }}
        transition={{ delay: 0.2, type: 'spring', damping: 26, stiffness: 220 }}
      >
        {/* Handle indicator */}
        <div className="w-10 h-1 rounded-full bg-gray-200 mx-auto mb-6" />

        <AnimatePresence mode="wait">
          {step === 'login' ? (
            <motion.div
              key="login"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <h2 className="font-display text-2xl font-bold text-gray-900 mb-1">
                ¡Hola! Ingresa aquí
              </h2>
              <p className="text-gray-400 text-sm mb-6">
                Usa tu cédula y teléfono registrado en la tienda.
              </p>

              <form onSubmit={handleLogin} className="flex flex-col gap-4">
                <div className="relative">
                  <CreditCard className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="text"
                    inputMode="numeric"
                    placeholder="Número de cédula"
                    value={doc}
                    onChange={(e) => setDoc(e.target.value)}
                    className="input-field pl-10"
                    required
                  />
                </div>

                <div className="relative">
                  <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                  <input
                    type="tel"
                    inputMode="tel"
                    placeholder="Teléfono (ej. 3206876633)"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="input-field pl-10"
                    required
                  />
                </div>

                <motion.button
                  type="submit"
                  disabled={loading}
                  className="btn-primary mt-1"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.97 }}
                  transition={{ type: 'spring', damping: 15 }}
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Ingresar
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </motion.button>
              </form>

              <p className="mt-6 text-center text-xs text-gray-400">
                ¿Primera vez?{' '}
                <a
                  href={`https://wa.me/573206876633?text=${encodeURIComponent('Hola! Quiero registrarme en el portal de Bigotes y Paticas')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-primary-700 font-semibold"
                >
                  Escríbenos por WhatsApp
                </a>
              </p>
            </motion.div>
          ) : (
            <OnboardingStep
              loginData={loginData}
              onComplete={() => router.replace('/dashboard')}
              setCustomer={setCustomer}
              qc={qc}
            />
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense>
      <LoginPageInner />
    </Suspense>
  );
}

// ── Onboarding ─────────────────────────────────────────────────────────

interface OnboardingProps {
  loginData: LoginResponse | null;
  onComplete: () => void;
  setCustomer: (c: any) => void;
  qc: any;
}

function OnboardingStep({ loginData, onComplete, setCustomer, qc }: OnboardingProps) {
  const [step, setStep] = useState<'welcome' | 'name' | 'pet'>('welcome');
  const [fullName, setFullName] = useState('');
  const [petName, setPetName] = useState(loginData?.pet_name ?? '');
  const [petSpecies, setPetSpecies] = useState('perro');
  const [petTheme, setPetTheme] = useState<string>('teal');
  const [loading, setLoading] = useState(false);

  const SPECIES = [
    { value: 'perro', emoji: '🐶', label: 'Perro' },
    { value: 'gato', emoji: '🐱', label: 'Gato' },
    { value: 'conejo', emoji: '🐰', label: 'Conejo' },
    { value: 'otro', emoji: '🐾', label: 'Otro' },
  ];

  const THEMES = [
    { value: 'teal', color: '#187f77' },
    { value: 'coral', color: '#e05252' },
    { value: 'amber', color: '#f5a641' },
    { value: 'purple', color: '#7c3aed' },
    { value: 'pink', color: '#db2777' },
    { value: 'green', color: '#16a34a' },
  ];

  async function handleComplete() {
    setLoading(true);
    try {
      if (fullName.trim()) {
        await auth.updateMe({ full_name: fullName.trim() });
      }
      if (petName.trim()) {
        await pets.create({ name: petName.trim(), species: petSpecies, color_theme: petTheme as any });
      }
      const me = await auth.me();
      setCustomer(me);
      qc.setQueryData(['portal-me'], me);
      qc.invalidateQueries({ queryKey: ['portal-pets'] });
      onComplete();
    } catch (err: any) {
      toast.error(err.message ?? 'Error al guardar datos');
    } finally {
      setLoading(false);
    }
  }

  return (
    <motion.div
      key="onboarding"
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col gap-5"
    >
      {step === 'welcome' && (
        <>
          <div className="text-center py-4">
            <div className="text-5xl mb-3">👋</div>
            <h2 className="font-display text-xl font-bold text-foreground">
              {loginData?.pet_name ? `¡Encontramos a ${loginData.pet_name}!` : '¡Bienvenido al portal!'}
            </h2>
            <p className="text-muted text-sm mt-2">
              {loginData?.pet_name
                ? `Vamos a crear el perfil de ${loginData.pet_name} en tu portal.`
                : 'Cuéntanos un poco sobre ti y tu mascota.'}
            </p>
          </div>
          <motion.button
            onClick={() => setStep('name')}
            className="btn-primary"
            whileTap={{ scale: 0.97 }}
          >
            Empezar <ArrowRight className="h-4 w-4" />
          </motion.button>
        </>
      )}

      {step === 'name' && (
        <>
          <h2 className="font-display text-xl font-bold text-foreground">¿Cómo te llamas?</h2>
          <input
            type="text"
            placeholder="Tu nombre completo"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="input-field"
            autoFocus
          />
          <motion.button onClick={() => setStep('pet')} className="btn-primary" whileTap={{ scale: 0.97 }}>
            Siguiente <ArrowRight className="h-4 w-4" />
          </motion.button>
        </>
      )}

      {step === 'pet' && (
        <>
          <h2 className="font-display text-xl font-bold text-foreground">Tu mascota</h2>
          <input
            type="text"
            placeholder="Nombre de tu mascota"
            value={petName}
            onChange={(e) => setPetName(e.target.value)}
            className="input-field"
          />
          <div className="grid grid-cols-4 gap-2">
            {SPECIES.map((s) => (
              <button
                key={s.value}
                type="button"
                onClick={() => setPetSpecies(s.value)}
                className={cn(
                  'flex flex-col items-center gap-1 rounded-xl p-2.5 border-2 text-xs font-medium transition-all',
                  petSpecies === s.value
                    ? 'border-primary-700 bg-primary-50 text-primary-700'
                    : 'border-border bg-white text-muted'
                )}
              >
                <span className="text-2xl">{s.emoji}</span>
                {s.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2 flex-wrap">
            {THEMES.map((t) => (
              <button
                key={t.value}
                type="button"
                onClick={() => setPetTheme(t.value)}
                className={cn(
                  'h-9 w-9 rounded-full border-4 transition-all',
                  petTheme === t.value ? 'border-foreground scale-110' : 'border-transparent'
                )}
                style={{ backgroundColor: t.color }}
              />
            ))}
          </div>
          <motion.button
            onClick={handleComplete}
            disabled={loading}
            className="btn-primary mt-2"
            whileTap={{ scale: 0.97 }}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '¡Listo! Ir al portal'}
          </motion.button>
        </>
      )}
    </motion.div>
  );
}
