'use client';

import Link from 'next/link';
import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, ChevronRight, RefreshCw, Calendar, Cake, ShoppingBag } from 'lucide-react';
import { intelligence, type SmartCard } from '@/lib/api';

const TYPE_ICONS: Record<string, React.ReactNode> = {
  reorder:     <ShoppingBag className="h-5 w-5" />,
  vaccine_due: <AlertCircle className="h-5 w-5" />,
  appointment: <Calendar className="h-5 w-5" />,
  birthday:    <Cake className="h-5 w-5" />,
  loyalty:     <RefreshCw className="h-5 w-5" />,
};

const PET_COLORS: Record<string, { accent: string; light: string; dark: string }> = {
  teal:   { accent: '#187f77', light: '#E1F5EE', dark: '#085041' },
  coral:  { accent: '#D85A30', light: '#FAECE7', dark: '#712B13' },
  amber:  { accent: '#BA7517', light: '#FAEEDA', dark: '#633806' },
  purple: { accent: '#534AB7', light: '#EEEDFE', dark: '#3C3489' },
  pink:   { accent: '#D4537E', light: '#FBEAF0', dark: '#72243E' },
  green:  { accent: '#639922', light: '#EAF3DE', dark: '#27500A' },
};

interface SmartCardsProps {
  max?: number;
}

export function SmartCards({ max = 3 }: SmartCardsProps) {
  const { data: cards, isLoading } = useQuery({
    queryKey: ['portal-smart-cards'],
    queryFn: intelligence.smartCards,
    refetchInterval: 20 * 1000,
    staleTime: 15 * 1000,
  });

  if (isLoading || !cards || cards.length === 0) return null;

  const visible = cards.slice(0, max);

  return (
    <div className="flex flex-col gap-2.5">
      {visible.map((card, i) => (
        <motion.div
          key={`${card.type}-${card.pet_id}-${i}`}
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: i * 0.06 }}
        >
          <SmartCardItem card={card} />
        </motion.div>
      ))}
    </div>
  );
}

function SmartCardItem({ card }: { card: SmartCard }) {
  const colors = PET_COLORS[card.color_theme] ?? PET_COLORS.teal;
  const isHigh = card.urgency === 'high';
  const borderColor = isHigh ? '#f5a641' : colors.light;
  const iconBg = isHigh ? 'rgba(245,166,65,0.12)' : colors.light;
  const iconColor = isHigh ? '#BA7517' : colors.accent;
  const badgeBg = isHigh ? '#fff8ed' : colors.light;
  const badgeColor = isHigh ? '#92400e' : colors.dark;

  return (
    <Link href={card.action_url}>
      <div
        className="rounded-2xl bg-white p-4 flex items-center gap-3.5 active:scale-[0.98] transition-transform"
        style={{
          border: `1.5px solid ${borderColor}`,
          boxShadow: isHigh
            ? '0 3px 14px rgba(245,166,65,0.14), 0 1px 4px rgba(0,0,0,0.04)'
            : '0 2px 10px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03)',
        }}
      >
        {/* Icono */}
        <div
          className="h-10 w-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: iconBg, color: iconColor }}
        >
          {TYPE_ICONS[card.type] ?? <AlertCircle className="h-5 w-5" />}
        </div>

        {/* Texto */}
        <div className="flex-1 min-w-0">
          {card.badge && (
            <span
              className="inline-block text-[10px] font-bold px-2 py-0.5 rounded-full mb-1"
              style={{ background: badgeBg, color: badgeColor }}
            >
              {card.badge}
            </span>
          )}
          <p className="font-semibold text-foreground text-sm leading-tight truncate">
            {card.title}
          </p>
          <p className="text-muted text-xs mt-0.5">{card.subtitle}</p>
        </div>

        {/* CTA */}
        <div className="flex items-center gap-1 shrink-0">
          <span
            className="text-xs font-semibold"
            style={{ color: isHigh ? '#BA7517' : colors.accent }}
          >
            {card.cta}
          </span>
          <ChevronRight
            className="h-4 w-4"
            style={{ color: isHigh ? '#BA7517' : colors.accent }}
          />
        </div>
      </div>
    </Link>
  );
}
