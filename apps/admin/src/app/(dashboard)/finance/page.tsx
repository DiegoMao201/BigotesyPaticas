'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Landmark, RefreshCw, FileSpreadsheet } from 'lucide-react';
import { finance } from '@/lib/api';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { DateRangePicker, thisMonthRange, type DateRange } from '@/components/analytics/DateRangePicker';
import {
  ResumenKpis, EstadoResultadosCard, BalanceCard, FlujoCajaCard, HistorialCard,
  IndicadoresCard, AlertasCard, EstadoBadge,
} from '@/components/finance/EstadosFinancieros';

export default function FinancePage() {
  const [range, setRange] = useState<DateRange>(thisMonthRange);
  const [exportando, setExportando] = useState(false);
  const q = useQuery({
    queryKey: ['finance-estados', range.start, range.end],
    queryFn: () => finance.estados(range),
    staleTime: 2 * 60_000,
  });

  async function exportar() {
    setExportando(true);
    try {
      const blob = await finance.exportExcel(12);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `estados-financieros-${range.start}-${range.end}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setExportando(false);
    }
  }

  const data = q.data;

  return (
    <div className="space-y-5">
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold font-display flex items-center gap-2">
            <Landmark className="w-6 h-6 text-brand-600" /> Estados financieros
            {data && <EstadoBadge r={data.resultados} />}
          </h1>
          <p className="text-sm text-muted-foreground">Estado de resultados, balance, flujo de caja e indicadores, con una sola regla contable</p>
        </div>
        <div className="flex items-center gap-2">
          <DateRangePicker value={range} onChange={setRange} />
          <Button variant="outline" size="sm" onClick={() => q.refetch()} title="Recalcular">
            <RefreshCw className={`w-4 h-4 ${q.isFetching ? 'animate-spin' : ''}`} />
          </Button>
          <Button variant="outline" size="sm" onClick={exportar} disabled={exportando}>
            <FileSpreadsheet className="w-4 h-4 mr-1" /> {exportando ? 'Generando…' : 'Excel 12 meses'}
          </Button>
        </div>
      </div>

      {q.isLoading && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[0, 1, 2, 3].map((i) => <div key={i} className="h-24 rounded-2xl bg-muted/40 animate-pulse" />)}
        </div>
      )}
      {q.isError && <Card className="p-8 text-center text-rose-600">No se pudieron calcular los estados: {String(q.error)}</Card>}

      {data && (
        <>
          <ResumenKpis data={data} />
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-5">
            <div className="xl:col-span-2 space-y-5">
              <EstadoResultadosCard r={data.resultados} anterior={data.anterior} />
              <FlujoCajaCard f={data.flujo_caja} />
            </div>
            <div className="space-y-5">
              <IndicadoresCard data={data} />
              <BalanceCard b={data.balance} />
              <AlertasCard data={data} />
            </div>
          </div>
          <HistorialCard h={data.historial} />
        </>
      )}
    </div>
  );
}
