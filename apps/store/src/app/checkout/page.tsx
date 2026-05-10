import { Button } from '@/components/ui/button';

export default function CheckoutPage() {
  return (
    <div className="container-tight py-12">
      <h1 className="text-4xl font-display font-bold">Checkout</h1>
      <p className="text-muted-foreground mt-2">Próximo sprint: integración con pasarela de pago (Wompi/Mercado Pago).</p>
      <div className="mt-8 p-12 rounded-2xl border-2 border-dashed border-border text-center">
        <div className="text-5xl mb-3">🚧</div>
        <p className="text-muted-foreground">
          Mientras tanto, contáctanos por WhatsApp para finalizar tu pedido.
        </p>
        <a
          href={`https://wa.me/${process.env.NEXT_PUBLIC_WHATSAPP || '573001234567'}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-block mt-4"
        >
          <Button>Chatear por WhatsApp</Button>
        </a>
      </div>
    </div>
  );
}
