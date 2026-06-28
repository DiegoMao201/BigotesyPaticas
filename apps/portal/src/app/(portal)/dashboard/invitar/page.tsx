'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation } from '@tanstack/react-query';
import { motion } from 'framer-motion';
import { toast } from 'sonner';
import { ArrowLeft, Copy, Share2, Check, Gift, Users, Star } from 'lucide-react';
import { auth, referral } from '@/lib/api';
import { Logo } from '@/components/brand/Logo';

const WHATSAPP_MSG = (code: string) => {
  const url = `https://mi.bigotesypaticas.com/?ref=${code}`;
  // Kept under 200 chars so WhatsApp preserves the full text when opening the native app
  return `Hola! Te invito a Bigotes y Paticas, tienda de mascotas en Pereira y Dosquebradas. Pide a domicilio y gana puntos. Registrate gratis: ${url}`;
};

export default function InvitarPage() {
  const router = useRouter();
  const [copied, setCopied] = useState(false);

  const { data: me } = useQuery({
    queryKey: ['portal-me'],
    queryFn: auth.me,
  });

  const { data: refs, isLoading: refsLoading } = useQuery({
    queryKey: ['portal-referrals'],
    queryFn: referral.myReferrals,
  });

  const code = me?.referral_code ?? refs?.referral_code ?? null;
  const myName = me?.full_name?.split(' ')[0] ?? 'tu amigo';

  function copyCode() {
    if (!code) return;
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      toast.success('Código copiado al portapapeles');
      setTimeout(() => setCopied(false), 2000);
    });
  }

  async function shareWhatsApp() {
    if (!code) return;
    const msg = WHATSAPP_MSG(code);

    // Web Share API: native share sheet on mobile — text reaches WhatsApp reliably
    if (typeof navigator !== 'undefined' && navigator.share) {
      try {
        await navigator.share({ text: msg });
        return;
      } catch {
        // User cancelled or not supported — fall through to wa.me
      }
    }

    // Desktop fallback: wa.me with pre-filled text
    window.open(`https://wa.me/?text=${encodeURIComponent(msg)}`, '_blank');
  }

  const totalReferrals = refs?.total_referrals ?? 0;
  const pendingReward = refs?.referrals.filter((r) => r.first_purchase_at && !r.reward_paid_at).length ?? 0;
  const paidRewards = refs?.referrals.filter((r) => r.reward_paid_at).length ?? 0;

  return (
    <div className="flex flex-col min-h-screen bg-gradient-to-b from-teal-50 to-white">
      {/* Header */}
      <div className="p-4 pt-10 pb-6 bg-gradient-to-br from-teal-600 to-teal-700">
        <div className="flex items-center gap-3 mb-6">
          <button
            onClick={() => router.back()}
            className="p-2 rounded-xl bg-white/20 text-white"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <h1 className="font-display text-xl font-bold text-white">Invitar amigos</h1>
        </div>

        <div className="text-center text-white mb-2">
          <Logo size={80} className="mb-3" />
          <p className="text-white/90 text-sm leading-relaxed">
            Por cada amigo que se registre con tu código,<br />
            <strong>ellos ganan 50 puntos</strong> y cuando hagan su <strong>primera compra</strong>,<br />
            ¡tú ganas <strong>100 puntos</strong>!
          </p>
        </div>
      </div>

      <div className="p-4 flex flex-col gap-5 -mt-4">
        {/* Código de referido */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-3xl shadow-card p-6 flex flex-col items-center gap-4"
        >
          <div className="flex items-center gap-2 text-teal-600">
            <Gift className="h-5 w-5" />
            <span className="font-semibold text-sm">Tu código de invitación</span>
          </div>

          {code ? (
            <div className="flex items-center gap-3">
              <div className="bg-teal-50 border-2 border-dashed border-teal-400 rounded-2xl px-6 py-3">
                <p className="font-mono text-2xl font-bold text-teal-700 tracking-widest">{code}</p>
              </div>
              <button
                onClick={copyCode}
                className="p-3 rounded-2xl bg-teal-100 text-teal-700 hover:bg-teal-200 transition-colors"
              >
                {copied ? <Check className="h-5 w-5" /> : <Copy className="h-5 w-5" />}
              </button>
            </div>
          ) : (
            <div className="h-12 w-40 bg-gray-100 rounded-2xl animate-pulse" />
          )}

          <button
            onClick={shareWhatsApp}
            disabled={!code}
            className="w-full flex items-center justify-center gap-2 py-3.5 rounded-2xl font-bold text-white disabled:opacity-60"
            style={{ backgroundColor: '#25D366' }}
          >
            <Share2 className="h-5 w-5" />
            Compartir por WhatsApp
          </button>
        </motion.div>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Invitados', value: totalReferrals, icon: <Users className="h-4 w-4 text-teal-600" /> },
            { label: 'Por cobrar', value: pendingReward * 100, suffix: ' pts', icon: <Star className="h-4 w-4 text-amber-500" /> },
            { label: 'Cobrados', value: paidRewards * 100, suffix: ' pts', icon: <Gift className="h-4 w-4 text-green-600" /> },
          ].map((stat) => (
            <div key={stat.label} className="bg-white rounded-2xl shadow-sm p-3 flex flex-col items-center gap-1">
              {stat.icon}
              <p className="text-lg font-bold text-gray-900">{stat.value}{stat.suffix ?? ''}</p>
              <p className="text-xs text-gray-500">{stat.label}</p>
            </div>
          ))}
        </div>

        {/* Cómo funciona */}
        <div className="bg-teal-50 rounded-2xl p-4 flex flex-col gap-3">
          <p className="font-semibold text-teal-800 text-sm">¿Cómo funciona?</p>
          {[
            { step: '1', text: 'Comparte tu código con un amigo' },
            { step: '2', text: 'Tu amigo se registra y gana 50 puntos al instante' },
            { step: '3', text: 'Cuando tu amigo hace su primera compra, tú ganas 100 puntos' },
          ].map((item) => (
            <div key={item.step} className="flex items-start gap-3">
              <div className="h-6 w-6 rounded-full bg-teal-600 text-white text-xs font-bold flex items-center justify-center shrink-0 mt-0.5">
                {item.step}
              </div>
              <p className="text-teal-700 text-sm">{item.text}</p>
            </div>
          ))}
        </div>

        {/* Lista de referidos */}
        {totalReferrals > 0 && (
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
              <Users className="h-4 w-4 text-teal-600" />
              Mis invitados ({totalReferrals})
            </p>
            <div className="flex flex-col gap-2">
              {refs?.referrals.map((r) => (
                <div key={r.id} className="flex items-center justify-between py-2 border-b border-gray-50 last:border-0">
                  <div>
                    <p className="text-sm font-semibold text-gray-900">{r.referred_name}</p>
                    <p className="text-xs text-gray-400">
                      Se unió {new Date(r.signed_up_at).toLocaleDateString('es-CO')}
                    </p>
                  </div>
                  <span className={`text-xs font-semibold px-2.5 py-1 rounded-full ${
                    r.reward_paid_at
                      ? 'bg-green-100 text-green-700'
                      : r.first_purchase_at
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-gray-100 text-gray-500'
                  }`}>
                    {r.reward_paid_at ? '✅ 100 pts cobrados' : r.first_purchase_at ? '⏳ Compró' : 'Sin compras'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {refsLoading && (
          <div className="flex flex-col gap-2">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-14 bg-gray-100 rounded-2xl animate-pulse" />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
