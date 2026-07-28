'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Handshake, ArrowRight, ArrowLeft, Loader2, Eye, EyeOff } from 'lucide-react';
import { toast } from 'sonner';
import { partnerAuth, ApiError, type PartnerType, type RegisterPayload } from '@/lib/api';
import { useAuth } from '@/lib/auth-store';
import { LocationPicker } from '@/components/maps/LocationPicker';

const TYPE_OPTIONS: { value: PartnerType; label: string; emoji: string }[] = [
  { value: 'vet', label: 'Veterinaria', emoji: '🩺' },
  { value: 'walker', label: 'Paseador', emoji: '🐕' },
  { value: 'shelter', label: 'Refugio', emoji: '🏠' },
  { value: 'groomer', label: 'Peluquería', emoji: '✂️' },
];

type FormState = {
  partner_type: PartnerType | '';
  business_name: string;
  legal_name: string;
  document_id: string;
  city: string;
  address: string;
  phone: string;
  lat: number | null;
  lng: number | null;
  bio: string;
  full_name: string;
  email: string;
  password: string;
  password2: string;
};

const EMPTY: FormState = {
  partner_type: '', business_name: '', legal_name: '', document_id: '', city: '',
  address: '', phone: '', lat: null, lng: null, bio: '', full_name: '', email: '',
  password: '', password2: '',
};

export default function RegistroPage() {
  const router = useRouter();
  const setSession = useAuth((s) => s.setSession);
  const [step, setStep] = useState(1);
  const [form, setForm] = useState<FormState>(EMPTY);
  const [loading, setLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  function set<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function canContinueStep1() {
    return !!form.partner_type && form.business_name.trim().length >= 2 &&
      form.legal_name.trim().length >= 2 && form.document_id.trim().length >= 3 &&
      form.city.trim().length >= 2;
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (form.password !== form.password2) {
      toast.error('Las contraseñas no coinciden');
      return;
    }
    if (form.password.length < 6) {
      toast.error('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    setLoading(true);
    try {
      const payload: RegisterPayload = {
        partner_type: form.partner_type as PartnerType,
        business_name: form.business_name.trim(),
        legal_name: form.legal_name.trim(),
        document_id: form.document_id.trim(),
        city: form.city.trim(),
        address: form.address.trim() || undefined,
        phone: form.phone.trim() || undefined,
        lat: form.lat ?? undefined,
        lng: form.lng ?? undefined,
        bio: form.bio.trim() || undefined,
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      };
      const data = await partnerAuth.register(payload);
      setSession(data.partner_user, data.access_token, data.refresh_token);
      toast.success('¡Registro exitoso!');
      router.replace('/pendiente-aprobacion');
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'No se pudo completar el registro');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-background py-8 px-4 sm:py-12">
      <div className="max-w-xl mx-auto">
        <Link href="/login" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-foreground mb-6">
          <ArrowLeft className="h-4 w-4" /> Volver a iniciar sesión
        </Link>

        <div className="flex items-center gap-3 mb-2">
          <div className="h-10 w-10 rounded-xl bg-primary-700 flex items-center justify-center shrink-0">
            <Handshake className="h-5 w-5 text-white" />
          </div>
          <h1 className="font-display text-2xl font-bold text-foreground">Únete como aliado</h1>
        </div>
        <p className="text-muted text-sm mb-8">
          Súmate a la red de aliados de Bigotes y Paticas — veterinarias, paseadores, refugios y
          peluquerías que la comunidad puede encontrar y agendar directamente.
        </p>

        {/* Indicador de pasos */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2, 3].map((n) => (
            <div key={n} className={`h-1.5 flex-1 rounded-full ${n <= step ? 'bg-primary-700' : 'bg-border'}`} />
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          {step === 1 && (
            <div className="card space-y-5">
              <h2 className="font-display font-bold text-foreground">1. Tu negocio</h2>

              <div>
                <label className="label-field">Tipo de aliado</label>
                <div className="grid grid-cols-2 gap-2">
                  {TYPE_OPTIONS.map((t) => (
                    <button
                      type="button"
                      key={t.value}
                      onClick={() => set('partner_type', t.value)}
                      className={
                        'flex items-center gap-2 rounded-xl border px-3 py-2.5 text-sm font-medium transition-all ' +
                        (form.partner_type === t.value
                          ? 'border-primary-700 bg-primary-50 text-primary-800'
                          : 'border-border text-foreground/80 hover:bg-primary-50/50')
                      }
                    >
                      <span className="text-lg">{t.emoji}</span> {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="label-field">Nombre comercial</label>
                <input className="input-field" value={form.business_name} onChange={(e) => set('business_name', e.target.value)} placeholder="Ej. Veterinaria Huellitas" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-field">Razón social</label>
                  <input className="input-field" value={form.legal_name} onChange={(e) => set('legal_name', e.target.value)} placeholder="Ej. Huellitas SAS" />
                </div>
                <div>
                  <label className="label-field">NIT / Documento</label>
                  <input className="input-field" value={form.document_id} onChange={(e) => set('document_id', e.target.value)} placeholder="900123456-1" />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-field">Ciudad</label>
                  <input className="input-field" value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="Pereira" />
                </div>
                <div>
                  <label className="label-field">Teléfono / WhatsApp</label>
                  <input className="input-field" value={form.phone} onChange={(e) => set('phone', e.target.value)} placeholder="320 000 0000" />
                </div>
              </div>

              <button
                type="button"
                disabled={!canContinueStep1()}
                onClick={() => setStep(2)}
                className="btn-primary w-full"
              >
                Continuar <ArrowRight className="h-4 w-4" />
              </button>
            </div>
          )}

          {step === 2 && (
            <div className="card space-y-5">
              <h2 className="font-display font-bold text-foreground">2. Ubicación y presentación</h2>

              <div>
                <label className="label-field">Dirección</label>
                <input className="input-field" value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="Cra 8 # 23-45" />
              </div>

              <div>
                <label className="label-field">Ubicación en el mapa</label>
                <LocationPicker lat={form.lat} lng={form.lng} onChange={(lat, lng) => { set('lat', lat); set('lng', lng); }} />
              </div>

              <div>
                <label className="label-field">Cuéntale a los clientes sobre tu negocio (opcional)</label>
                <textarea
                  className="input-field resize-none"
                  rows={3}
                  value={form.bio}
                  onChange={(e) => set('bio', e.target.value)}
                  placeholder="Ej. Más de 10 años cuidando mascotas, atención con cita previa..."
                />
              </div>

              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(1)} className="btn-outline flex-1">
                  <ArrowLeft className="h-4 w-4" /> Atrás
                </button>
                <button type="button" onClick={() => setStep(3)} className="btn-primary flex-1">
                  Continuar <ArrowRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}

          {step === 3 && (
            <div className="card space-y-5">
              <h2 className="font-display font-bold text-foreground">3. Tu cuenta de acceso</h2>

              <div>
                <label className="label-field">Tu nombre (dueño / encargado)</label>
                <input className="input-field" value={form.full_name} onChange={(e) => set('full_name', e.target.value)} placeholder="Ej. Juan Pérez" />
              </div>
              <div>
                <label className="label-field">Correo</label>
                <input type="email" className="input-field" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="tucorreo@negocio.com" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label-field">Contraseña</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="input-field pr-9"
                      value={form.password}
                      onChange={(e) => set('password', e.target.value)}
                      placeholder="Mínimo 6 caracteres"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
                      tabIndex={-1}
                      aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="label-field">Repetir contraseña</label>
                  <div className="relative">
                    <input
                      type={showPassword ? 'text' : 'password'}
                      className="input-field pr-9"
                      value={form.password2}
                      onChange={(e) => set('password2', e.target.value)}
                      placeholder="••••••••"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword((v) => !v)}
                      className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted hover:text-foreground"
                      tabIndex={-1}
                      aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                    >
                      {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                    </button>
                  </div>
                </div>
              </div>

              <p className="text-xs text-muted">
                Al registrarte, tu negocio queda pendiente de revisión por el equipo de Bigotes y
                Paticas antes de aparecer en el directorio público. Mientras tanto, puedes ir
                configurando tu perfil, servicios y disponibilidad.
              </p>

              <div className="flex gap-3">
                <button type="button" onClick={() => setStep(2)} className="btn-outline flex-1">
                  <ArrowLeft className="h-4 w-4" /> Atrás
                </button>
                <button type="submit" disabled={loading} className="btn-primary flex-1">
                  {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
                  Crear mi cuenta
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
