'use client';
import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface FAQ {
  pregunta: string;
  respuesta: string;
}

export function ProductFAQ({ faqs }: { faqs: FAQ[] }) {
  const [open, setOpen] = useState<number | null>(null);

  if (!faqs || faqs.length === 0) return null;

  return (
    <section className="mt-10">
      <h2 className="text-xl font-display font-bold text-[#0d4a45] mb-4">
        Preguntas frecuentes
      </h2>
      <div className="divide-y divide-border rounded-2xl border border-border overflow-hidden">
        {faqs.map((faq, i) => (
          <div key={i}>
            <button
              type="button"
              onClick={() => setOpen(open === i ? null : i)}
              className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-semibold hover:bg-muted/50 transition-colors"
            >
              <span>{faq.pregunta}</span>
              <ChevronDown
                className={cn(
                  'h-4 w-4 shrink-0 text-muted-foreground transition-transform',
                  open === i && 'rotate-180',
                )}
              />
            </button>
            {open === i && (
              <div className="px-5 pb-4 text-sm text-muted-foreground leading-relaxed">
                {faq.respuesta}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
