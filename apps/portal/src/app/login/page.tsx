'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { toast } from 'sonner';
import { Phone, CreditCard, ArrowRight, Loader2 } from 'lucide-react';
import { auth, pets, type LoginResponse } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';
import { cn } from '@/lib/utils';

type Step = 'login' | 'onboarding';

export default function LoginPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { setCustomer } = useAuthStore();

  const [step, setStep] = useState<Step>('login');
  const [loginData, setLoginData] = useState<LoginResponse | null>(null);
  const [loading, setLoading] = useState(false);

  // Login form
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

      // Si es cliente existente con datos de mascota en el JSONB (legacy) → onboarding
      if (resp.has_pets && !resp.full_name) {
        setStep('onboarding');
        return;
      }

      // Cargar /me para hidratar el store
      const me = await auth.me();
      setCustomer(me);
      qc.setQueryData(['portal-me'], me);

      // Si no tiene nombre → mostrar onboarding
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
    <div className="min-h-screen bg-primary-700 flex flex-col">
      {/* Header splash */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pt-16 pb-8 text-white gap-4">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', duration: 0.6 }}
          className="text-6xl"
        >
          🐾
        </motion.div>
        <motion.div
          initial={{ y: 16, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          className="text-center"
        >
          <h1 className="font-display text-3xl font-bold">Bigotes y Paticas</h1>
          <p className="mt-1 text-primary-100 text-sm">Tu portal de mascotas</p>
        </motion.div>
      </div>

      {/* Card */}
      <motion.div
        initial={{ y: 40, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ delay: 0.3, duration: 0.5 }}
        className="bg-background rounded-t-3xl px-6 pt-8 pb-12 shadow-2xl"
      >
        <AnimatePresence mode="wait">
          {step === 'login' ? (
            <motion.div
              key="login"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
            >
              <h2 className="font-display text-xl font-bold text-foreground mb-1">
                ¡Hola! Ingresa aquí
              </h2>
              <p className="text-muted text-sm mb-6">
                Usa tu cédula y teléfono registrado en la tienda.
              </p>

              <form onSubmit={handleLogin} className="flex flex-col gap-4">
                <div className="relative">
                  <CreditCard className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
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
                  <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted" />
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

                <button type="submit" disabled={loading} className="btn-primary mt-2">
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      Ingresar
                      <ArrowRight className="h-4 w-4" />
                    </>
                  )}
                </button>
              </form>

              <p className="mt-6 text-center text-xs text-muted">
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

// ── Onboarding: leer datos legacy + registrar mascota ─────────────────

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
    { value: 'teal', color: '#187f77', label: 'Teal' },
    { value: 'coral', color: '#e05252', label: 'Coral' },
    { value: 'amber', color: '#f5a641', label: 'Ámbar' },
    { value: 'purple', color: '#7c3aed', label: 'Violeta' },
    { value: 'pink', color: '#db2777', label: 'Rosa' },
    { value: 'green', color: '#16a34a', label: 'Verde' },
  ];

  async function handleComplete() {
    setLoading(true);
    try {
      // Actualizar nombre si no lo tiene
      if (fullName.trim()) {
        await auth.updateMe({ full_name: fullName.trim() });
      }
      // Crear mascota (tomando datos del legacy JSONB)
      if (petName.trim()) {
        await pets.create({
          name: petName.trim(),
          species: petSpecies,
          color_theme: petTheme as any,
        });
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
              {loginData?.pet_name
                ? `¡Encontramos a ${loginData.pet_name}!`
                : '¡Bienvenido al portal!'}
            </h2>
            <p className="text-muted text-sm mt-2">
              {loginData?.pet_name
                ? `Vamos a crear el perfil de ${loginData.pet_name} en tu portal.`
                : 'Cuéntanos un poco sobre ti y tu mascota.'}
            </p>
          </div>
          <button onClick={() => setStep('name')} className="btn-primary">
            Empezar <ArrowRight className="h-4 w-4" />
          </button>
        </>
      )}

      {step === 'name' && (
        <>
          <h2 className="font-display text-xl font-bold text-foreground">
            ¿Cómo te llamas?
          </h2>
          <input
            type="text"
            placeholder="Tu nombre completo"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="input-field"
            autoFocus
          />
          <button onClick={() => setStep('pet')} className="btn-primary">
            Siguiente <ArrowRight className="h-4 w-4" />
          </button>
        </>
      )}

      {step === 'pet' && (
        <>
          <h2 className="font-display text-xl font-bold text-foreground">
            Tu mascota
          </h2>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
              Nombre
            </label>
            <input
              type="text"
              placeholder="Nombre de tu mascota"
              value={petName}
              onChange={(e) => setPetName(e.target.value)}
              className="input-field"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
              Especie
            </label>
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
          </div>

          <div>
            <label className="text-xs font-semibold text-muted uppercase tracking-wide mb-1.5 block">
              Color de tema
            </label>
            <div className="flex gap-2 flex-wrap">
              {THEMES.map((t) => (
                <button
                  key={t.value}
                  type="button"
                  onClick={() => setPetTheme(t.value)}
                  title={t.label}
                  className={cn(
                    'h-9 w-9 rounded-full border-4 transition-all',
                    petTheme === t.value ? 'border-foreground scale-110' : 'border-transparent'
                  )}
                  style={{ backgroundColor: t.color }}
                />
              ))}
            </div>
          </div>

          <button onClick={handleComplete} disabled={loading} className="btn-primary mt-2">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : '¡Listo! Ir al portal'}
          </button>
        </>
      )}
    </motion.div>
  );
}
