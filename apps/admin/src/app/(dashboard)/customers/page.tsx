import { Card } from '@/components/ui/card';
import { Users } from 'lucide-react';

export default function CustomersPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-display font-bold tracking-tight">Clientes</h1>
        <p className="text-muted-foreground mt-1">CRM con segmentación RFM</p>
      </div>
      <Card className="p-12 text-center">
        <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="font-display font-semibold text-lg">CRM en preparación</h3>
        <p className="text-muted-foreground text-sm mt-1">Próximo sprint: lista, segmentos, historial.</p>
      </Card>
    </div>
  );
}
