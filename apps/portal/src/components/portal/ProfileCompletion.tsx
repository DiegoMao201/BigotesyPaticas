'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, ChevronRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { intelligence, type MissingField } from '@/lib/api';

const FIELD_TYPES: Record<string, { type: string; placeholder: string }> = {
  address:    { type: 'text',   placeholder: 'Calle 10 #5-32, Dosquebradas' },
  email:      { type: 'email',  placeholder: 'tuCorreo@email.com' },
  city:       { type: 'text',   placeholder: 'Dosquebradas' },
  birth_date: { type: 'date',   placeholder: '' },
  weight_kg:  { type: 'number', placeholder: '4.5' },
  breed:      { type: 'text',   placeholder: 'Ej: Labrador, Siamés...' },
  photo_url:  { type: 'url',    placeholder: 'https://...' },
  food_brand: { type: 'text',   placeholder: 'Ej: Pro Plan, Hills...' },
};

const NUMBER_FIELDS = new Set(['weight_kg', 'food_freq_days']);

function parseFieldValue(field: string, raw: string): unknown {
  if (NUMBER_FIELDS.has(field)) {
    const n = parseFloat(raw);
    return isNaN(n) ? null : n;
  }
  return raw || null;
}

export function ProfileCompletion() {
  const qc = useQueryClient();
  const [dismissed, setDismissed] = useState(false);
  const [activeField, setActiveField] = useState<MissingField | null>(null);
  const [inputVal, setInputVal] = useState('');
  const [showSuccess, setShowSuccess] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['portal-completion'],
    queryFn: intelligence.completion,
    staleTime: 2 * 60 * 1000,
  });

  const { mutate: saveField, isPending } = useMutation<unknown, Error, MissingField>({
    mutationFn: ({ field, entity, entity_id }: MissingField) =>
      intelligence.updateField(entity, entity_id, field, parseFieldValue(field, inputVal)) as Promise<unknown>,
    onSuccess: () => {
      setShowSuccess(true);
      toast.success(`+${activeField?.points_reward} puntos ganados 🎉`);
      qc.invalidateQueries({ queryKey: ['portal-completion'] });
      qc.invalidateQueries({ queryKey: ['portal-me'] });
      qc.invalidateQueries({ queryKey: ['portal-pets'] });
      qc.invalidateQueries({ queryKey: ['portal-loyalty'] });
      setTimeout(() => {
        setActiveField(null);
        setInputVal('');
        setShowSuccess(false);
      }, 1200);
    },
    onError: () => toast.error('No se pudo guardar. Intenta de nuevo.'),
  });

  if (isLoading || dismissed || !data) return null;
  if (data.percentage >= 100) return null;
  if (data.missing_fields.length === 0) return null;

  const nextField = data.missing_fields[0];

  return (
    <>
      <AnimatePresence>
        {!activeField && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95 }}
            className="completion-banner"
          >
            <div className="flex items-start gap-3">
              <div className="h-9 w-9 rounded-xl bg-white/20 flex items-center justify-center shrink-0">
                <Sparkles className="h-4 w-4 text-white" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-white font-semibold text-sm leading-tight">
                  Completa el perfil de {nextField.entity === 'pet' ? nextField.label.split(' ').pop() : 'tu cuenta'}
                </p>
                <p className="text-white/75 text-xs mt-0.5">
                  Gana +{nextField.points_reward} pts · {data.percentage}% completado
                </p>
                {/* Progress bar */}
                <div className="mt-2 h-1.5 rounded-full bg-white/20 overflow-hidden">
                  <motion.div
                    className="h-full rounded-full bg-white"
                    initial={{ width: 0 }}
                    animate={{ width: `${data.percentage}%` }}
                    transition={{ duration: 0.8, ease: 'easeOut' }}
                  />
                </div>
              </div>
              <div className="flex items-center gap-1.5">
                <button
                  onClick={() => setActiveField(nextField)}
                  className="text-white text-xs font-bold bg-white/20 px-3 py-1.5 rounded-lg hover:bg-white/30 transition-colors flex items-center gap-1"
                >
                  Completar <ChevronRight className="h-3 w-3" />
                </button>
                <button
                  onClick={() => setDismissed(true)}
                  className="text-white/60 hover:text-white transition-colors ml-1"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Modal Typeform */}
      <AnimatePresence>
        {activeField && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-4"
            style={{ background: 'rgba(0,0,0,0.4)', backdropFilter: 'blur(4px)' }}
            onClick={(e) => e.target === e.currentTarget && setActiveField(null)}
          >
            <motion.div
              initial={{ y: 60, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: 60, opacity: 0 }}
              transition={{ type: 'spring', damping: 28, stiffness: 300 }}
              className="w-full max-w-sm bg-white rounded-2xl p-6 shadow-2xl"
            >
              <AnimatePresence mode="wait">
                {showSuccess ? (
                  <motion.div
                    key="success"
                    initial={{ scale: 0.8, opacity: 0 }}
                    animate={{ scale: 1, opacity: 1 }}
                    className="flex flex-col items-center gap-3 py-4 text-center"
                  >
                    <div className="text-5xl">🎉</div>
                    <p className="font-display font-bold text-foreground text-lg">¡Guardado!</p>
                    <p className="text-muted text-sm">+{activeField.points_reward} puntos añadidos</p>
                  </motion.div>
                ) : (
                  <motion.div key="form" className="flex flex-col gap-4">
                    <div>
                      <div className="h-10 w-10 rounded-xl bg-purple-100 flex items-center justify-center mb-3">
                        <Sparkles className="h-5 w-5 text-purple-600" />
                      </div>
                      <h3 className="font-display font-bold text-foreground text-xl">
                        {activeField.label}
                      </h3>
                      <p className="text-muted text-sm mt-1">{activeField.reason}</p>
                      <p className="text-purple-600 text-xs font-semibold mt-0.5">
                        +{activeField.points_reward} pts al guardar
                      </p>
                    </div>

                    <input
                      type={FIELD_TYPES[activeField.field]?.type ?? 'text'}
                      className="input-field text-base"
                      placeholder={FIELD_TYPES[activeField.field]?.placeholder ?? ''}
                      value={inputVal}
                      onChange={(e) => setInputVal(e.target.value)}
                      autoFocus
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && inputVal) saveField(activeField);
                      }}
                    />

                    <div className="flex gap-3">
                      <button
                        onClick={() => setActiveField(null)}
                        className="flex-1 py-3 rounded-xl border border-border text-muted text-sm font-semibold hover:bg-gray-50"
                      >
                        Ahora no
                      </button>
                      <button
                        disabled={!inputVal || isPending}
                        onClick={() => saveField(activeField)}
                        className="flex-1 py-3 rounded-xl text-sm font-semibold text-white flex items-center justify-center gap-2 disabled:opacity-50"
                        style={{ background: 'linear-gradient(135deg, #534AB7, #7c5cbf)' }}
                      >
                        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Guardar →'}
                      </button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
