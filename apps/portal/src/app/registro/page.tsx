'use client';

import { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { ArrowRight, ArrowLeft, Loader2, CheckCircle } from 'lucide-react';
import { useAuthStore } from '@/lib/auth-store';
import { auth } from '@/lib/api';
import { cn } from '@/lib/utils';

const VIDEO_MP4  = process.env.NEXT_PUBLIC_LOGIN_VIDEO_MP4  ?? '';
const VIDEO_WEBM = process.env.NEXT_PUBLIC_LOGIN_VIDEO_WEBM ?? '';
const VIDEO_POSTER = process.env.NEXT_PUBLIC_LOGIN_POSTER   ?? '';
const LOGO_URL = process.env.NEXT_PUBLIC_BRAND_LOGO
  ?? 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

type Step = 1 | 2 | 3 | 4 | 5;

const SPECIES = [
  { value: 'perro',  emoji: '🐶', label: 'Perro'   },
  { value: 'gato',   emoji: '🐱', label: 'Gato'    },
  { value: 'conejo', emoji: '🐰', label: 'Conejo'  },
  { value: 'otro',   emoji: '🐾', label: 'Otro'    },
];

const STEP_LABELS = ['Tus datos', 'Contacto', '¿Tienes mascota?', 'Tu mascota', 'Términos'];

export default function RegistroPage() {
  const router = useRouter();
  const videoRef = useRef<HTMLVideoElement>(null);
  const { setCustomer } = useAuthStore();

  const [step, setStep] = useState<Step>(1);
  const [loading, setLoading] = useState(false);

  const [fullName,    setFullName]    = useState('');
  const [documentId,  setDocumentId]  = useState('');
  const [phone,       setPhone]       = useState('');
  const [email,       setEmail]       = useState('');
  const [hasPet,      setHasPet]      = useState<boolean | null>(null);
  const [petName,     setPetName]     = useState('');
  const [petSpecies,  setPetSpecies]  = useState('perro');
  const [termsOk,     setTermsOk]     = useState(false);

  function next() { setStep((s) => Math.min(5, s + 1) as Step); }
  function back() { setStep((s) => Math.max(1, s - 1) as Step); }

  async function handleSubmit() {
    if (!termsOk) { toast.error('Debes aceptar los términos'); return; }
    setLoading(true);
    try {
      const res = await fetch('/api/v1/portal/auth/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          full_name:   fullName.trim(),
          document_id: documentId.trim(),
          phone:       phone.trim(),
          email:       email.trim() || null,
          pet_name:    hasPet && petName.trim() ? petName.trim() : null,
          pet_species: hasPet ? petSpecies : null,
          accept_terms: true,
        }),
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail ?? 'Error al registrarse');
      }
      const me = await auth.me();
      setCustomer(me);
      router.replace('/dashboard');
    } catch (err: any) {
      toast.error(err.message ?? 'Error al registrarse');
    } finally {
      setLoading(false);
    }
  }

  const progress = ((step - 1) / 4) * 100;

  return (
    <div className="relative min-h-screen overflow-hidden bg-teal-900">
      {/* VIDEO */}
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
      <div className="absolute inset-0 bg-gradient-to-b from-[#187f77]/50 via-[#187f77]/35 to-[#0d4a45]/75" />

      {/* Header */}
      <div className="relative z-10 flex flex-col items-center pt-10 px-6">
        <div className="w-16 h-16 rounded-2xl bg-white/20 backdrop-blur-xl border border-white/30 flex items-center justify-center mb-3 shadow-lg overflow-hidden p-1.5">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={LOGO_URL} alt="Bigotes y Paticas" className="w-full h-full object-contain" />
        </div>
        <h1 className="text-white text-2xl font-semibold tracking-tight drop-shadow-lg">Crear cuenta</h1>
        <p className="text-white/75 text-sm mt-1">Bigotes y Paticas — Portal de fidelización</p>

        {/* Step indicator */}
        <div className="w-full max-w-sm mt-5 px-1">
          <div className="flex justify-between text-white/60 text-[10px] mb-1.5">
            <span>Paso {step} de 5</span>
            <span>{STEP_LABELS[step - 1]}</span>
          </div>
          <div className="h-1 bg-white/20 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-white rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ type: 'spring', damping: 20 }}
            />
          </div>
        </div>
      </div>

      {/* Card */}
      <motion.div
        className="absolute bottom-0 left-0 right-0 bg-white rounded-t-[2rem] shadow-2xl z-10"
        initial={{ y: 300 }}
        animate={{ y: 0 }}
        transition={{ delay: 0.1, type: 'spring', damping: 28, stiffness: 240 }}
      >
        <div className="w-10 h-1 rounded-full bg-gray-200 mx-auto mt-5 mb-1" />
        <div className="px-6 pt-3 pb-10 min-h-[320px]">
          <AnimatePresence mode="wait">
            {/* STEP 1 — Nombre + Cédula */}
            {step === 1 && (
              <motion.div key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-3">
                <h2 className="font-display text-xl font-bold text-gray-900">¿Cómo te llamas?</h2>
                <input
                  className="input-field" placeholder="Nombre completo *" value={fullName}
                  onChange={(e) => setFullName(e.target.value)} autoFocus
                />
                <input
                  className="input-field" placeholder="Número de cédula *" inputMode="numeric"
                  value={documentId} onChange={(e) => setDocumentId(e.target.value)}
                />
                <button
                  onClick={() => {
                    if (!fullName.trim() || !documentId.trim()) { toast.error('Completa nombre y cédula'); return; }
                    next();
                  }}
                  className="btn-primary mt-2"
                >
                  Continuar <ArrowRight className="h-4 w-4" />
                </button>
                <p className="text-center text-xs text-gray-400">
                  ¿Ya tienes cuenta?{' '}
                  <a href="/login" className="text-primary-700 font-semibold">Ingresar</a>
                </p>
              </motion.div>
            )}

            {/* STEP 2 — Teléfono + Email */}
            {step === 2 && (
              <motion.div key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-3">
                <h2 className="font-display text-xl font-bold text-gray-900">¿Cómo te contactamos?</h2>
                <input
                  className="input-field" placeholder="Teléfono celular *" inputMode="tel"
                  value={phone} onChange={(e) => setPhone(e.target.value)} autoFocus
                />
                <input
                  className="input-field" placeholder="Correo electrónico (opcional)" type="email"
                  value={email} onChange={(e) => setEmail(e.target.value)}
                />
                <button
                  onClick={() => { if (!phone.trim()) { toast.error('Ingresa tu teléfono'); return; } next(); }}
                  className="btn-primary mt-2"
                >
                  Continuar <ArrowRight className="h-4 w-4" />
                </button>
                <button onClick={back} className="btn-outline text-sm flex items-center justify-center gap-1">
                  <ArrowLeft className="h-3.5 w-3.5" /> Atrás
                </button>
              </motion.div>
            )}

            {/* STEP 3 — ¿Tienes mascota? */}
            {step === 3 && (
              <motion.div key="s3" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-4">
                <h2 className="font-display text-xl font-bold text-gray-900">¿Tienes mascota?</h2>
                <p className="text-gray-400 text-sm -mt-2">Te ayudaremos a crear su perfil y carnet digital.</p>
                <div className="grid grid-cols-2 gap-3">
                  {[{ v: true, emoji: '🐾', label: 'Sí, tengo' }, { v: false, emoji: '🕐', label: 'Aún no' }].map((opt) => (
                    <button
                      key={String(opt.v)}
                      type="button"
                      onClick={() => { setHasPet(opt.v); next(); }}
                      className={cn(
                        'flex flex-col items-center gap-2 rounded-2xl p-5 border-2 text-sm font-medium transition-all',
                        hasPet === opt.v
                          ? 'border-primary-700 bg-primary-50 text-primary-700'
                          : 'border-border bg-white text-gray-600 hover:border-primary-200'
                      )}
                    >
                      <span className="text-3xl">{opt.emoji}</span>
                      {opt.label}
                    </button>
                  ))}
                </div>
                <button onClick={back} className="btn-outline text-sm flex items-center justify-center gap-1 mt-1">
                  <ArrowLeft className="h-3.5 w-3.5" /> Atrás
                </button>
              </motion.div>
            )}

            {/* STEP 4 — Mascota (solo si hasPet) */}
            {step === 4 && (
              <motion.div key="s4" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-3">
                {hasPet ? (
                  <>
                    <h2 className="font-display text-xl font-bold text-gray-900">¿Cómo se llama tu mascota?</h2>
                    <input
                      className="input-field" placeholder="Nombre de tu mascota *" autoFocus
                      value={petName} onChange={(e) => setPetName(e.target.value)}
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
                    <button
                      onClick={() => { if (!petName.trim()) { toast.error('Ingresa el nombre de tu mascota'); return; } next(); }}
                      className="btn-primary mt-1"
                    >
                      Continuar <ArrowRight className="h-4 w-4" />
                    </button>
                  </>
                ) : (
                  <>
                    <div className="text-center py-4">
                      <div className="text-5xl mb-3">🎉</div>
                      <h2 className="font-display text-lg font-bold">¡Todo listo!</h2>
                      <p className="text-gray-400 text-sm mt-1">Solo falta aceptar los términos.</p>
                    </div>
                    <button onClick={next} className="btn-primary">
                      Continuar <ArrowRight className="h-4 w-4" />
                    </button>
                  </>
                )}
                <button onClick={back} className="btn-outline text-sm flex items-center justify-center gap-1">
                  <ArrowLeft className="h-3.5 w-3.5" /> Atrás
                </button>
              </motion.div>
            )}

            {/* STEP 5 — Términos */}
            {step === 5 && (
              <motion.div key="s5" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-4">
                <h2 className="font-display text-xl font-bold text-gray-900">Casi listo 🐾</h2>
                <div className="rounded-2xl bg-gray-50 border border-gray-200 p-4 text-xs text-gray-500 leading-relaxed max-h-32 overflow-y-auto">
                  Al registrarte aceptas que Bigotes y Paticas almacene y use tus datos personales para
                  gestionar tu cuenta, enviarte información sobre tus pedidos, y brindarte una experiencia
                  personalizada. Puedes solicitar la eliminación de tus datos en cualquier momento.
                  Política de privacidad disponible en bigotesypaticas.com.
                </div>
                <label className="flex items-start gap-3 cursor-pointer group">
                  <div className={cn(
                    'mt-0.5 w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all',
                    termsOk ? 'border-primary-700 bg-primary-700' : 'border-gray-300 group-hover:border-primary-400'
                  )}
                    onClick={() => setTermsOk(!termsOk)}
                  >
                    {termsOk && <CheckCircle className="h-3.5 w-3.5 text-white" />}
                  </div>
                  <span className="text-sm text-gray-600">
                    Acepto los términos de uso y el tratamiento de mis datos personales
                  </span>
                </label>
                <button
                  onClick={handleSubmit}
                  disabled={loading || !termsOk}
                  className="btn-primary mt-1 py-4 text-base disabled:opacity-50"
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <>Crear mi cuenta <ArrowRight className="h-5 w-5" /></>
                  )}
                </button>
                <button onClick={back} className="btn-outline text-sm flex items-center justify-center gap-1">
                  <ArrowLeft className="h-3.5 w-3.5" /> Atrás
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>
    </div>
  );
}
