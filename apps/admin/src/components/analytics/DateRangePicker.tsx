'use client';

import { useEffect, useRef, useState } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import { startOfMonth, endOfMonth, subMonths, subDays, format } from 'date-fns';
import { Input } from '@/components/ui/input';

export interface DateRange {
  start: string; // YYYY-MM-DD
  end: string; // YYYY-MM-DD
  label: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function fmt(d: Date): string {
  return format(d, 'yyyy-MM-dd');
}

// El backend interpreta start_date/end_date en America/Bogota
// (_date_ranges.py) — "hoy" acá debe ser el día en Bogotá, no en la zona del
// navegador del usuario ni UTC. Se resuelve explícito vía Intl en vez de
// confiar en que el dispositivo esté en esa zona horaria.
function nowBogota(): Date {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'America/Bogota',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).formatToParts(new Date());
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? '00';
  return new Date(
    Number(get('year')),
    Number(get('month')) - 1,
    Number(get('day')),
    Number(get('hour')),
    Number(get('minute')),
    Number(get('second')),
  );
}

function buildPresets(): { label: string; range: () => DateRange }[] {
  return [
    {
      label: 'Hoy',
      range: () => {
        const n = fmt(nowBogota());
        return { start: n, end: n, label: 'Hoy' };
      },
    },
    {
      label: 'Ayer',
      range: () => {
        const n = fmt(subDays(nowBogota(), 1));
        return { start: n, end: n, label: 'Ayer' };
      },
    },
    {
      label: 'Últimos 7 días',
      range: () => {
        const hoy = nowBogota();
        return { start: fmt(subDays(hoy, 6)), end: fmt(hoy), label: 'Últimos 7 días' };
      },
    },
    {
      label: 'Últimos 30 días',
      range: () => {
        const hoy = nowBogota();
        return { start: fmt(subDays(hoy, 29)), end: fmt(hoy), label: 'Últimos 30 días' };
      },
    },
    {
      label: 'Este mes',
      range: () => {
        const hoy = nowBogota();
        return { start: fmt(startOfMonth(hoy)), end: fmt(hoy), label: 'Este mes' };
      },
    },
    {
      label: 'Mes anterior',
      range: () => {
        const mesAnterior = subMonths(nowBogota(), 1);
        return {
          start: fmt(startOfMonth(mesAnterior)),
          end: fmt(endOfMonth(mesAnterior)),
          label: 'Mes anterior',
        };
      },
    },
  ];
}

export function defaultDateRange(): DateRange {
  return buildPresets()[3].range(); // Últimos 30 días — mismo default que el dropdown anterior
}

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [open, setOpen] = useState(false);
  const [customStart, setCustomStart] = useState(value.start);
  const [customEnd, setCustomEnd] = useState(value.end);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const presets = buildPresets();
  const hoyStr = fmt(nowBogota());

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 rounded-lg border border-border bg-white px-3 py-2 text-sm hover:bg-muted/40 transition-colors"
      >
        <Calendar className="w-4 h-4 text-brand-600" />
        <span className="font-medium">{value.label}</span>
        <ChevronDown className="w-3.5 h-3.5 text-muted-foreground" />
      </button>

      {open && (
        <div className="absolute z-20 mt-1 w-72 rounded-lg border border-border bg-white shadow-lg p-2">
          <div className="grid grid-cols-2 gap-1 mb-2">
            {presets.map((p) => (
              <button
                key={p.label}
                onClick={() => {
                  onChange(p.range());
                  setOpen(false);
                }}
                className={`text-left text-sm px-2 py-1.5 rounded-md hover:bg-brand-50 transition-colors ${
                  value.label === p.label ? 'bg-brand-100 text-brand-700 font-medium' : ''
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          <div className="border-t border-border pt-2 space-y-2">
            <div className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
              Personalizado
            </div>
            <div className="flex items-center gap-2">
              <Input
                type="date"
                value={customStart}
                max={customEnd}
                onChange={(e) => setCustomStart(e.target.value)}
                className="text-xs"
              />
              <span className="text-muted-foreground text-xs">→</span>
              <Input
                type="date"
                value={customEnd}
                min={customStart}
                max={hoyStr}
                onChange={(e) => setCustomEnd(e.target.value)}
                className="text-xs"
              />
            </div>
            <button
              onClick={() => {
                onChange({ start: customStart, end: customEnd, label: `${customStart} → ${customEnd}` });
                setOpen(false);
              }}
              className="w-full text-center text-sm bg-brand-600 hover:bg-brand-700 text-white rounded-md py-1.5 transition-colors"
            >
              Aplicar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
