'use client';

declare global {
  interface Window {
    fbq: (...args: unknown[]) => void;
  }
}

export function useMetaPixelEvent() {
  function track(eventName: string, params?: Record<string, unknown>) {
    if (typeof window === 'undefined' || !window.fbq) return;
    try {
      window.fbq('track', eventName, params ?? {});
    } catch {
      // pixel not loaded or blocked
    }
  }

  function trackCustom(eventName: string, params?: Record<string, unknown>) {
    if (typeof window === 'undefined' || !window.fbq) return;
    try {
      window.fbq('trackCustom', eventName, params ?? {});
    } catch {
      // pixel not loaded or blocked
    }
  }

  return { track, trackCustom };
}
