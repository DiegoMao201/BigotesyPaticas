'use client';

import { useEffect, useState } from 'react';
import { X, Download } from 'lucide-react';
import { trackEvent } from '@/lib/analytics';

interface BeforeInstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

const STORAGE_KEY = 'pwa_install_dismissed_until';
const DISMISS_DAYS = 7;

export function PWAInstallBanner() {
  const [show, setShow] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    const dismissed = localStorage.getItem(STORAGE_KEY);
    if (dismissed && Date.now() < Number(dismissed)) return;

    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      setTimeout(() => setShow(true), 30_000);
    };
    window.addEventListener('beforeinstallprompt', handler);
    return () => window.removeEventListener('beforeinstallprompt', handler);
  }, []);

  function dismiss() {
    setShow(false);
    localStorage.setItem(STORAGE_KEY, String(Date.now() + DISMISS_DAYS * 86_400_000));
    trackEvent('pwa_install_dismissed');
  }

  async function install() {
    if (!deferredPrompt) return;
    trackEvent('pwa_install_intent');
    await deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === 'accepted') trackEvent('pwa_install_accepted');
    setShow(false);
    setDeferredPrompt(null);
  }

  if (!show) return null;

  return (
    <div className="fixed bottom-20 left-4 right-4 sm:left-auto sm:right-6 sm:w-80 z-50 animate-slide-up">
      <div className="rounded-2xl bg-white border border-border shadow-xl p-4 flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl gradient-brand flex items-center justify-center shrink-0">
          <Download className="w-5 h-5 text-white" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-sm">Instalar Bigotes y Paticas</p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Accede más rápido y compra sin abrir el navegador.
          </p>
          <button
            onClick={install}
            className="mt-3 w-full py-2 rounded-xl gradient-brand text-white text-sm font-semibold hover:opacity-90 transition-opacity"
          >
            Instalar app
          </button>
        </div>
        <button onClick={dismiss} className="p-1 -mt-1 -mr-1 rounded-full hover:bg-gray-100 shrink-0">
          <X className="w-4 h-4 text-muted-foreground" />
        </button>
      </div>
    </div>
  );
}
