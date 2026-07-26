'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LifeBuoy } from 'lucide-react';
import { motion } from 'framer-motion';

export function SOSButton() {
  const pathname = usePathname();
  const active = pathname.startsWith('/sos');

  return (
    <Link
      href="/sos"
      aria-label="SOS — Reportar mascota perdida"
      className="fixed bottom-20 left-4 z-50 flex flex-col items-center gap-1"
    >
      <motion.div
        whileTap={{ scale: 0.9 }}
        whileHover={{ scale: 1.05 }}
        className="relative flex h-14 w-14 items-center justify-center rounded-full shadow-lg"
        style={{
          background: 'linear-gradient(135deg, #ff7a63, #e8433a)',
          boxShadow: '0 8px 20px rgba(232, 67, 58, 0.4)',
        }}
      >
        {!active && <span className="sos-fab-ring" />}
        <LifeBuoy className="h-7 w-7 text-white" strokeWidth={2} />
      </motion.div>
      <span className="rounded-full bg-white/90 px-2 py-0.5 text-[10px] font-bold tracking-wide text-[#c62f28] shadow-sm">
        SOS
      </span>
    </Link>
  );
}
