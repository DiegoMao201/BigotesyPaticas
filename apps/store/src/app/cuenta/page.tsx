const PORTAL_URL = 'https://mi.bigotesypaticas.com';

export const metadata = {
  title: 'Mi cuenta — Bigotes y Paticas',
  description: 'Ingresa o crea tu cuenta en el portal de fidelización de Bigotes y Paticas.',
};

export default function CuentaPage() {
  return (
    <div className="min-h-[72vh] flex items-center justify-center px-6 py-12">
      <div className="max-w-md w-full text-center">
        <div className="w-24 h-24 rounded-full bg-[#187f77] flex items-center justify-center mx-auto mb-6 shadow-xl">
          <span className="text-5xl" role="img" aria-label="Huella">🐾</span>
        </div>

        <h1 className="text-3xl font-display font-bold text-[#0d4a45] mb-3">
          Mi cuenta
        </h1>
        <p className="text-gray-500 mb-8 leading-relaxed max-w-xs mx-auto">
          Accede a tu portal personal para gestionar tus mascotas,
          ver puntos de fidelidad y agendar citas.
        </p>

        <div className="space-y-3">
          <a
            href={`${PORTAL_URL}/login`}
            className="flex items-center justify-center gap-2 w-full py-3.5 rounded-full
                       bg-[#187f77] text-white font-semibold shadow-lg
                       hover:bg-[#0d4a45] transition-colors duration-200"
          >
            Ingresar al portal →
          </a>
          <a
            href={`${PORTAL_URL}/registro`}
            className="flex items-center justify-center gap-2 w-full py-3.5 rounded-full
                       bg-white text-[#187f77] font-semibold
                       border-2 border-[#187f77]/20
                       hover:bg-[#187f77]/5 transition-colors duration-200"
          >
            Crear cuenta gratis
          </a>
        </div>

        <div className="flex justify-center flex-wrap gap-x-6 gap-y-2 mt-10 text-xs text-gray-500">
          <span>🎁 50 pts de bienvenida</span>
          <span>📋 Carnet digital</span>
          <span>🐾 Historial de mascotas</span>
        </div>

        <p className="text-xs text-gray-400 mt-4">
          Gratis para clientes · Sin descargas
        </p>
      </div>
    </div>
  );
}
