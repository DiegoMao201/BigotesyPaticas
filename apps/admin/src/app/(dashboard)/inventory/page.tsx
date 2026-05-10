import { Card } from '@/components/ui/card';
import { Boxes } from 'lucide-react';

export default function InventoryPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl font-display font-bold tracking-tight">Inventario</h1>
        <p className="text-muted-foreground mt-1">Stock, movimientos y reservas</p>
      </div>
      <Card className="p-12 text-center">
        <Boxes className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
        <h3 className="font-display font-semibold text-lg">Inventario en preparación</h3>
        <p className="text-muted-foreground text-sm mt-1">
          Próximo sprint: vista por ubicación, ajustes y kardex.
        </p>
      </Card>
    </div>
  );
}
