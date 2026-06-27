'use client';

import { useRouter } from 'next/navigation';
import { Minus, Plus, Trash2, X } from 'lucide-react';
import { usePortalCart } from '@/lib/cart-store';
import { formatCOP } from '@/lib/utils';

interface Props {
  open: boolean;
  onClose: () => void;
}

export function CartDrawer({ open, onClose }: Props) {
  const router = useRouter();
  const items = usePortalCart((s) => s.items);
  const subtotal = usePortalCart((s) => s.subtotal());
  const isFreeShipping = usePortalCart((s) => s.isFreeShipping());
  const pointsToEarn = usePortalCart((s) => s.pointsToEarn());
  const updateQuantity = usePortalCart((s) => s.updateQuantity);
  const removeItem = usePortalCart((s) => s.removeItem);

  const shipping = isFreeShipping ? 0 : 8000;
  const missingForFree = Math.max(0, 30000 - subtotal);

  function goToCheckout() {
    onClose();
    router.push('/pedido');
  }

  return (
    <>
      {/* Overlay */}
      {open && (
        <div
          className="fixed inset-0 bg-black/50 z-40"
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        className={`fixed top-0 right-0 h-full w-full max-w-sm bg-white z-50 flex flex-col shadow-2xl transition-transform duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-bold text-lg">
            Tu carrito ({items.reduce((s, i) => s + i.quantity, 0)})
          </h2>
          <button onClick={onClose} className="p-2 rounded-xl hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Items */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {items.length === 0 ? (
            <p className="text-center text-gray-400 mt-12">Tu carrito está vacío</p>
          ) : (
            items.map((item) => (
              <div key={item.product_id} className="flex gap-3 items-center bg-gray-50 rounded-2xl p-3">
                <div className="w-16 h-16 rounded-xl bg-gray-200 overflow-hidden shrink-0">
                  {item.image_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={item.image_url} alt={item.name} className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-2xl">🐾</div>
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold line-clamp-2">{item.name}</p>
                  <p className="text-sm text-teal-700 font-bold">{formatCOP(item.unit_price)}</p>
                </div>
                <div className="flex flex-col items-center gap-2">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                      className="w-7 h-7 rounded-full bg-gray-200 flex items-center justify-center"
                    >
                      <Minus className="h-3 w-3" />
                    </button>
                    <span className="w-6 text-center text-sm font-bold">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                      className="w-7 h-7 rounded-full bg-teal-100 text-teal-700 flex items-center justify-center"
                    >
                      <Plus className="h-3 w-3" />
                    </button>
                  </div>
                  <button
                    onClick={() => removeItem(item.product_id)}
                    className="text-red-400 hover:text-red-600"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {items.length > 0 && (
          <div className="p-4 border-t space-y-3">
            {missingForFree > 0 && (
              <p className="text-xs text-center text-amber-600 bg-amber-50 rounded-xl py-2 px-3">
                Te faltan {formatCOP(missingForFree)} para envío gratis 🚚
              </p>
            )}
            {isFreeShipping && (
              <p className="text-xs text-center text-green-700 bg-green-50 rounded-xl py-2 px-3">
                ¡Tienes envío gratis! 🎉
              </p>
            )}
            <div className="flex justify-between text-sm text-gray-600">
              <span>Subtotal</span>
              <span className="font-bold">{formatCOP(subtotal)}</span>
            </div>
            <div className="flex justify-between text-sm text-gray-600">
              <span>Envío</span>
              <span>{shipping === 0 ? 'Gratis' : formatCOP(shipping)}</span>
            </div>
            <p className="text-xs text-teal-600 text-center">
              🌟 Ganarás {pointsToEarn} Puntos Bigotes con este pedido
            </p>
            <button
              onClick={goToCheckout}
              className="w-full py-4 bg-teal-600 hover:bg-teal-700 text-white font-bold rounded-2xl transition"
            >
              Finalizar pedido →
            </button>
            <button
              onClick={onClose}
              className="w-full py-2 text-gray-500 hover:text-gray-700 text-sm"
            >
              Seguir comprando
            </button>
          </div>
        )}
      </div>
    </>
  );
}
