import { ChevronRight, Scale } from 'lucide-react';

const WEB = 'https://bigotesypaticas.com';
const ENLACES = [
  { label: 'Política de privacidad', href: `${WEB}/politica-privacidad` },
  { label: 'Términos y condiciones', href: `${WEB}/terminos` },
  { label: 'Devoluciones, retracto y garantías', href: `${WEB}/devoluciones` },
];

/**
 * Quién vende y los documentos legales, dentro de la app (8-nov-2026).
 * Google Play pide la política de privacidad dentro de la app y la Ley 1480
 * (art. 50) que el comprador pueda ver la identidad del vendedor.
 */
export function Legal() {
  return (
    <div className="card flex flex-col divide-y divide-border">
      <div className="flex items-start gap-3 pb-3">
        <Scale className="mt-0.5 h-4 w-4 shrink-0 text-primary-700" />
        <p className="text-xs leading-relaxed text-muted">
          <span className="font-semibold text-foreground">Vende: Diego Mauricio García Rengifo</span> · NIT 1088266407-7 ·
          establecimiento Bigotes y Paticas, matrícula 68875 de la Cámara de Comercio de Dosquebradas · Cl. 15 #3A-07,
          C.C. Samara Plaza, Local 2, Dosquebradas · bigotesypaticasdosquebradas@gmail.com · 320 687 6633
        </p>
      </div>
      {ENLACES.map(({ label, href }) => (
        <a key={href} href={href} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between py-3">
          <span className="text-sm font-medium">{label}</span>
          <ChevronRight className="h-4 w-4 text-muted" />
        </a>
      ))}
    </div>
  );
}
