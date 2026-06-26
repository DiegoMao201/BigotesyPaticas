'use client';

import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { Shield, Loader2, Check } from 'lucide-react';
import { toast } from 'sonner';
import { auth } from '@/lib/api';
import { useAuthStore } from '@/lib/auth-store';

const TERMS_VERSION = '1.0';
const LOGO_URL = process.env.NEXT_PUBLIC_BRAND_LOGO
  ?? 'https://catalogo-ferreinox.nyc3.cdn.digitaloceanspaces.com/bigotesypaticas/branding/logo-512.png';

export function TermsModal() {
  const { customer, setCustomer } = useAuthStore();
  const qc = useQueryClient();
  const [termsOk, setTermsOk] = useState(false);
  const [dataOk, setDataOk] = useState(false);

  const { mutate: accept, isPending } = useMutation({
    mutationFn: () => auth.acceptTerms(TERMS_VERSION),
    onSuccess: (updated) => {
      setCustomer(updated);
      qc.invalidateQueries({ queryKey: ['portal-me'] });
      toast.success('¡Bienvenido a Bigotes y Paticas! 🐾');
    },
    onError: () => toast.error('No se pudo registrar tu aceptación. Inténtalo de nuevo.'),
  });

  // Solo mostrar si el usuario no ha aceptado
  const needsTerms = customer && !customer.terms_accepted_at;
  if (!needsTerms) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center"
        style={{ background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(6px)' }}
      >
        <motion.div
          initial={{ y: 80, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ type: 'spring', damping: 28, stiffness: 280 }}
          className="w-full max-w-sm bg-white rounded-t-3xl sm:rounded-3xl overflow-hidden shadow-2xl"
        >
          {/* Header teal */}
          <div
            className="flex flex-col items-center gap-2 py-6 px-6 text-center"
            style={{ background: 'linear-gradient(135deg, #187f77, #085041)' }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={LOGO_URL} alt="Bigotes y Paticas" className="w-16 h-16 object-contain" />
            <p className="text-white/80 text-sm">Bienvenido a tu espacio</p>
            <h2 className="font-display font-bold text-white text-2xl leading-tight">
              Bigotes y Paticas
            </h2>
          </div>

          {/* Contenido */}
          <div className="p-6 flex flex-col gap-5 max-h-[70vh] overflow-y-auto">
            <div>
              <h3 className="font-bold text-foreground text-base mb-2">
                Antes de empezar, queremos ser transparentes
              </h3>
              <p className="text-muted text-sm mb-3">
                Recolectamos tu cédula, teléfono, correo y dirección para:
              </p>
              <ul className="flex flex-col gap-2">
                {[
                  'Procesar tus pedidos y coordinar entregas a tu casa',
                  'Agendar servicios y mantener el historial médico de tu mascota',
                  'Recordarte vacunas, desparasitación y cuándo se acaba el alimento',
                  'Darte beneficios exclusivos del programa de fidelización Bigotes',
                ].map((item, i) => (
                  <li key={i} className="flex items-start gap-2.5 text-sm text-foreground">
                    <span className="mt-0.5 h-5 w-5 rounded-full bg-primary-100 flex items-center justify-center shrink-0">
                      <Check className="h-3 w-3 text-primary-700" strokeWidth={3} />
                    </span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            {/* Promesa */}
            <div
              className="rounded-2xl p-4 flex gap-3"
              style={{ background: '#E1F5EE' }}
            >
              <Shield className="h-5 w-5 text-primary-700 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-primary-700 text-sm">Nuestra promesa</p>
                <p className="text-primary-900 text-xs mt-0.5 leading-relaxed">
                  No vendemos ni compartimos tus datos con terceros con fines publicitarios.
                  Cumplimos la Ley 1581 de 2012 de Protección de Datos Personales de Colombia.
                </p>
              </div>
            </div>

            {/* Checkboxes */}
            <div className="flex flex-col gap-3">
              {[
                {
                  checked: termsOk,
                  onChange: () => setTermsOk((v) => !v),
                  label: (
                    <>
                      He leído y acepto los{' '}
                      <span className="text-primary-700 font-semibold underline cursor-pointer">
                        términos de uso
                      </span>
                    </>
                  ),
                },
                {
                  checked: dataOk,
                  onChange: () => setDataOk((v) => !v),
                  label: 'Autorizo el tratamiento de mis datos personales',
                },
              ].map(({ checked, onChange, label }, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={onChange}
                  className="flex items-center gap-3 text-left"
                >
                  <div
                    className="h-6 w-6 rounded-lg border-2 flex items-center justify-center shrink-0 transition-all"
                    style={{
                      borderColor: checked ? '#187f77' : '#d1d5db',
                      background: checked ? '#187f77' : 'white',
                    }}
                  >
                    {checked && <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />}
                  </div>
                  <span className="text-sm text-foreground">{label}</span>
                </button>
              ))}
            </div>

            {/* Botón */}
            <button
              disabled={!termsOk || !dataOk || isPending}
              onClick={() => accept()}
              className="w-full py-4 rounded-2xl font-bold text-white text-base flex items-center justify-center gap-2 disabled:opacity-50 transition-opacity"
              style={{ background: 'linear-gradient(135deg, #187f77, #085041)' }}
            >
              {isPending ? <Loader2 className="h-5 w-5 animate-spin" /> : 'Acepto y continúo →'}
            </button>

            <p className="text-center text-xs text-muted">
              Puedes pedir modificar o borrar tus datos al WhatsApp{' '}
              <a href="https://wa.me/573206876633" className="text-primary-700 font-semibold">
                +57 320 687 6633
              </a>
            </p>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
