'use client';

import { useState, useRef, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Phone, CreditCard, ArrowRight, Loader2 } from 'lucide-react';
import { auth, pets, referral as referralApi, type LoginResponse } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

const VIDEO_MP4  = process.env.NEXT_PUBLIC_LOGIN_VIDEO_MP4  ?? '';
const VIDEO_WEBM = process.env.NEXT_PUBLIC_LOGIN_VIDEO_WEBM ?? '';
const VIDEO_POSTER = process.env.NEXT_PUBLIC_LOGIN_POSTER   ?? '';
const LOGO_URL = process.env.NEXT_PUBLIC_BRAND_LOGO
  ?? 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

type Step = 'login' | 'onboarding';

const PAWS = [
  { left: '8%',  top: '14%', delay: 0,   size: 18 },
  { left: '78%', top: '10%', delay: 0.8, size: 14 },
  { left: '20%', top: '42%', delay: 1.6, size: 22 },
  { left: '88%', top: '32%', delay: 0.4, size: 16 },
  { left: '55%', top: '22%', delay: 2.2, size: 12 },
  { left: '42%', top: '54%', delay: 1.1, size: 20 },
  { left: '67%', top: '48%', delay: 2.8, size: 14 },
  { left: '12%', top: '62%', delay: 3.4, size: 16 },
];

function LoginPageInner() {
  const router    = useRouter();
  const qc        = useQueryClient();
  const { setCustomer } = useAuthStore();
  const searchParams    = useSearchParams();
  const refCode   = searchParams.get('ref') ?? null;
  const videoRef  = useRef<HTMLVideoElement>(null);

  const [step,      setStep]      = useState<Step>('login');
  const [loginData, setLoginData] = useState<LoginResponse | null>(null);
  const [loading,   setLoading]   = useState(false);
  const [muted,     setMuted]     = useState(true);
  const [expanded,  setExpanded]  = useState(false);

  const [doc,   setDoc]   = useState('');
  const [phone, setPhone] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // Primera pulsación: solo expandir el card
    if (!expanded) {
      setExpanded(true);
      return;
    }

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

      {/* VIDEO desde CDN */}
      <video
        ref={videoRef}
        autoPlay muted loop playsInline
        preload="metadata"
        poster={VIDEO_POSTER || undefined}
        className="absolute inset-0 w-full h-full object-cover"
      >
        {VIDEO_WEBM && <source src={VIDEO_WEBM} type="video/webm" />}
        {VIDEO_MP4  && <source src={VIDEO_MP4}  type="video/mp4"  />}
      </video>

      {/* Overlay teal con atmósfera */}
      <div className="absolute inset-0 bg-gradient-to-b from-[#187f77]/45 via-[#187f77]/35 to-[#0d4a45]/70" />

      {/* Mute */}
      <button
        onClick={() => {
          if (videoRef.current) { videoRef.current.muted = !muted; setMuted(!muted); }
        }}
        className="absolute top-4 right-4 z-20 w-10 h-10 rounded-full bg-white/15 backdrop-blur-sm flex items-center justify-center text-lg active:scale-90 transition-transform"
        aria-label={muted ? 'Activar sonido' : 'Silenciar'}
      >
        {muted ? '🔇' : '🔊'}
      </button>

      {/* Huellas flotantes */}
      {PAWS.map((p, i) => (
        <motion.span
          key={i}
          className="absolute pointer-events-none select-none text-white z-10"
          style={{ left: p.left, top: p.top, fontSize: p.size, opacity: 0 }}
          animate={{ opacity: [0, 0.3, 0.3, 0], y: [0, -35, -70, -110] }}
          transition={{ duration: 7, delay: p.delay, repeat: Infinity, ease: 'easeOut' }}
        >
          🐾
        </motion.span>
      ))}

      {/* Logo + título — solo en estado compacto o login */}
      <AnimatePresence>
        {step === 'login' && (
          <motion.div
            key="logo"
            className="relative z-10 flex flex-col items-center pt-14 px-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.55 }}
          >
            <motion.div
              className="w-20 h-20 rounded-2xl bg-white/20 backdrop-blur-xl border border-white/30 flex items-center justify-center mb-4 shadow-lg shadow-black/20 overflow-hidden p-2"
              animate={{ y: [0, -6, 0] }}
              transition={{ duration: 3.5, repeat: Infinity, ease: 'easeInOut' }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={LOGO_URL} alt="Bigotes y Paticas" className="w-full h-full object-contain" />
            </motion.div>
            <h1 className="text-white text-3xl font-semibold tracking-tight drop-shadow-lg">
              Bigotes y Paticas
            </h1>
            <p className="text-white/90 text-sm mt-1 drop-shadow-md">Tu portal de mascotas</p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── CARD BOTTOM-SHEET ─────────────────────────────── */}
      <motion.div
        layout
        className="absolute bottom-0 left-0 right-0 bg-white rounded-t-[2rem] shadow-2xl z-10 overflow-hidden"
        initial={{ y: 280 }}
        animate={{ y: 0 }}
        transition={{ delay: 0.15, type: 'spring', damping: 28, stiffness: 240 }}
      >
        {/* Handle */}
        <div className="w-10 h-1 rounded-full bg-gray-200 mx-auto mt-5 mb-1" />

        <div className="px-6 pt-3 pb-10">
          <AnimatePresence mode="wait">
            {step === 'login' ? (
              <motion.form
                key="login-form"
                onSubmit={handleSubmit}
                className="flex flex-col gap-3"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              >
                <h2 className="font-display text-xl font-bold text-gray-900">
                  ¡Hola! Ingresa aquí
                </h2>

                {/* Campos: solo visibles tras expandir */}
                <AnimatePresence>
                  {expanded && (
                    <motion.div
                      key="fields"
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      exit={{ opacity: 0, height: 0 }}
                      transition={{ type: 'spring', damping: 22, stiffness: 260 }}
                      className="flex flex-col gap-3 overflow-hidden"
                    >
                      <p className="text-gray-400 text-sm -mt-1">
                        Usa tu cédula y teléfono registrado en la tienda.
                      </p>

                      <div className="relative">
                        <CreditCard className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                          type="text"
                          inputMode="numeric"
                          placeholder="Número de cédula"
                          value={doc}
                          onChange={(e) => setDoc(e.target.value)}
                          className="input-field pl-10"
                          autoFocus
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
                        />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>

                {/* Botón siempre visible */}
                <motion.button
                  layout
                  type="submit"
                  disabled={loading}
                  className="btn-primary mt-1 py-4 text-base"
                  whileTap={{ scale: 0.97 }}
                  transition={{ type: 'spring', damping: 15 }}
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>
                      Ingresar
                      <ArrowRight className="h-5 w-5" />
                    </>
                  )}
                </motion.button>

                <p className="text-center text-xs text-gray-400 mt-1">
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
              </motion.form>
            ) : (
              <OnboardingStep
                key="onboarding"
                loginData={loginData}
                onComplete={() => router.replace('/dashboard')}
                setCustomer={setCustomer}
                qc={qc}
              />
            )}
          </AnimatePresence>
        </div>
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

// ── Onboarding ──────────────────────────────────────────────────────────────

interface OnboardingProps {
  loginData: LoginResponse | null;
  onComplete: () => void;
  setCustomer: (c: any) => void;
  qc: any;
}

function OnboardingStep({ loginData, onComplete, setCustomer, qc }: OnboardingProps) {
  const [step,       setStep]      = useState<'welcome' | 'name' | 'pet'>('welcome');
  const [fullName,   setFullName]  = useState('');
  const [petName,    setPetName]   = useState(loginData?.pet_name ?? '');
  const [petSpecies, setPetSpecies]= useState('perro');
  const [petTheme,   setPetTheme]  = useState<string>('teal');
  const [loading,    setLoading]   = useState(false);

  const SPECIES = [
    { value: 'perro',  emoji: '🐶', label: 'Perro' },
    { value: 'gato',   emoji: '🐱', label: 'Gato' },
    { value: 'conejo', emoji: '🐰', label: 'Conejo' },
    { value: 'otro',   emoji: '🐾', label: 'Otro' },
  ];

  const THEMES = [
    { value: 'teal',   color: '#187f77' },
    { value: 'coral',  color: '#e05252' },
    { value: 'amber',  color: '#f5a641' },
    { value: 'purple', color: '#7c3aed' },
    { value: 'pink',   color: '#db2777' },
    { value: 'green',  color: '#16a34a' },
  ];

  async function handleComplete() {
    setLoading(true);
    try {
      if (fullName.trim()) await auth.updateMe({ full_name: fullName.trim() });
      if (petName.trim())  await pets.create({ name: petName.trim(), species: petSpecies, color_theme: petTheme as any });
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
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -20 }}
      className="flex flex-col gap-4"
    >
      {step === 'welcome' && (
        <>
          <div className="text-center py-3">
            <div className="text-4xl mb-2">👋</div>
            <h2 className="font-display text-lg font-bold text-foreground">
              {loginData?.pet_name ? `¡Encontramos a ${loginData.pet_name}!` : '¡Bienvenido al portal!'}
            </h2>
            <p className="text-muted text-sm mt-1.5">
              {loginData?.pet_name
                ? `Vamos a crear el perfil de ${loginData.pet_name}.`
                : 'Cuéntanos sobre ti y tu mascota.'}
            </p>
          </div>
          <motion.button onClick={() => setStep('name')} className="btn-primary" whileTap={{ scale: 0.97 }}>
            Empezar <ArrowRight className="h-4 w-4" />
          </motion.button>
        </>
      )}

      {step === 'name' && (
        <>
          <h2 className="font-display text-lg font-bold text-foreground">¿Cómo te llamas?</h2>
          <input
            type="text" placeholder="Tu nombre completo"
            value={fullName} onChange={(e) => setFullName(e.target.value)}
            className="input-field" autoFocus
          />
          <motion.button onClick={() => setStep('pet')} className="btn-primary" whileTap={{ scale: 0.97 }}>
            Siguiente <ArrowRight className="h-4 w-4" />
          </motion.button>
        </>
      )}

      {step === 'pet' && (
        <>
          <h2 className="font-display text-lg font-bold text-foreground">Tu mascota</h2>
          <input
            type="text" placeholder="Nombre de tu mascota"
            value={petName} onChange={(e) => setPetName(e.target.value)}
            className="input-field"
          />
          <div className="grid grid-cols-4 gap-2">
            {SPECIES.map((s) => (
              <button
                key={s.value} type="button" onClick={() => setPetSpecies(s.value)}
                className={cn(
                  'flex flex-col items-center gap-1 rounded-xl p-2.5 border-2 text-xs font-medium transition-all',
                  petSpecies === s.value
                    ? 'border-primary-700 bg-primary-50 text-primary-700'
                    : 'border-border bg-white text-muted'
                )}
              >
                <span className="text-2xl">{s.emoji}</span>{s.label}
              </button>
            ))}
          </div>
          <div className="flex gap-2 flex-wrap">
            {THEMES.map((t) => (
              <button
                key={t.value} type="button" onClick={() => setPetTheme(t.value)}
                className={cn('h-8 w-8 rounded-full border-4 transition-all',
                  petTheme === t.value ? 'border-foreground scale-110' : 'border-transparent')}
                style={{ backgroundColor: t.color }}
              />
            ))}
          </div>
          <motion.button
            onClick={handleComplete} disabled={loading}
            className="btn-primary mt-1" whileTap={{ scale: 0.97 }}
          >
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '¡Listo! Ir al portal'}
          </motion.button>
        </>
      )}
    </motion.div>
  );
}
