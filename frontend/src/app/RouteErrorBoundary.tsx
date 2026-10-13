import { useRouteError, isRouteErrorResponse } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { RefreshCw, AlertTriangle, Home } from 'lucide-react';

function isChunkError(err: unknown): boolean {
  if (!err) return false;
  const message =
    typeof err === 'object' && err !== null && 'message' in err
      ? String((err as any).message)
      : String(err);
  return (
    message.includes('Failed to fetch dynamically imported module') ||
    message.includes('Importing a module script failed') ||
    message.includes('error loading dynamically imported module') ||
    message.includes('Loading chunk')
  );
}

export default function RouteErrorBoundary() {
  const error = useRouteError();
  const [isUpdating, setIsUpdating] = useState(false);

  useEffect(() => {
    if (isChunkError(error)) {
      setIsUpdating(true);
      const reloadKey = 'sicop_chunk_error_reload';
      const lastReload = sessionStorage.getItem(reloadKey);
      const now = Date.now();

      // Si no hemos reintentado en los últimos 15 segundos, recargar limpiamente
      if (!lastReload || now - Number(lastReload) > 15000) {
        sessionStorage.setItem(reloadKey, String(now));
        // Limpiar todas las cachés y forzar actualización
        const purgeAndReload = async () => {
          if ('caches' in window) {
            try {
              const keys = await caches.keys();
              await Promise.all(keys.map((k) => caches.delete(k)));
            } catch (_) {}
          }
          if ('serviceWorker' in navigator) {
            try {
              const regs = await navigator.serviceWorker.getRegistrations();
              for (const reg of regs) {
                await reg.update().catch(() => {});
              }
            } catch (_) {}
          }
          const target = new URL(window.location.href);
          target.searchParams.set('_v', Date.now().toString());
          window.location.replace(target.toString());
        };

        void purgeAndReload();
      }
    }
  }, [error]);

  const handleManualRefresh = async () => {
    setIsUpdating(true);
    if ('caches' in window) {
      try {
        const keys = await caches.keys();
        await Promise.all(keys.map((k) => caches.delete(k)));
      } catch (_) {}
    }
    if ('serviceWorker' in navigator) {
      try {
        const regs = await navigator.serviceWorker.getRegistrations();
        for (const reg of regs) {
          await reg.unregister();
        }
      } catch (_) {}
    }
    const target = new URL(window.location.href);
    target.searchParams.set('_v', Date.now().toString());
    window.location.replace(target.toString());
  };

  if (isUpdating) {
    return (
      <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-cyan-50 border border-cyan-200 flex items-center justify-center mb-4 text-[#3484A5] animate-spin">
          <RefreshCw className="w-8 h-8" />
        </div>
        <h2 className="text-xl font-bold text-slate-800 mb-2">
          Actualizando a la última versión...
        </h2>
        <p className="text-sm text-slate-500 max-w-md">
          Se detectó una nueva actualización del sistema en el servidor. Estamos recargando los módulos más recientes.
        </p>
      </div>
    );
  }

  let errorMessage = 'Ocurrió un error inesperado al procesar la solicitud.';
  if (isRouteErrorResponse(error)) {
    errorMessage = `${error.status} ${error.statusText} — ${error.data || 'Ruta no encontrada'}`;
  } else if (error instanceof Error) {
    errorMessage = error.message;
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="w-full max-w-lg bg-white rounded-2xl shadow-xl border border-slate-200/80 p-8 text-center">
        <div className="w-16 h-16 rounded-2xl bg-amber-50 border border-amber-200 flex items-center justify-center mx-auto mb-5 text-amber-600 shadow-sm">
          <AlertTriangle className="w-8 h-8" />
        </div>

        <span className="inline-block text-[11px] font-bold uppercase tracking-wider text-[#3484A5] bg-cyan-50 px-3 py-1 rounded-full mb-3">
          Municipalidad Distrital de San Jerónimo
        </span>

        <h1 className="text-2xl font-bold text-slate-900 tracking-tight mb-2">
          Actualización o inconveniente de carga
        </h1>

        <p className="text-sm text-slate-600 leading-relaxed mb-6">
          Es probable que se haya desplegado una nueva versión del sistema o que la conexión a los módulos se haya interrumpido. Puede recargar para obtener la versión más reciente.
        </p>

        <div className="flex flex-col sm:flex-row gap-3 justify-center mb-6">
          <button
            type="button"
            onClick={handleManualRefresh}
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-white bg-[#3484A5] hover:bg-[#286882] shadow-sm hover:shadow transition-all active:scale-[0.98] cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
            Recargar versión reciente
          </button>

          <a
            href="/"
            className="inline-flex items-center justify-center gap-2 px-5 py-2.5 rounded-xl font-semibold text-sm text-slate-700 bg-slate-100 hover:bg-slate-200 transition-all cursor-pointer"
          >
            <Home className="w-4 h-4" />
            Ir al inicio
          </a>
        </div>

        <details className="text-left bg-slate-50 rounded-xl p-3 border border-slate-200 text-xs text-slate-500">
          <summary className="cursor-pointer font-medium text-slate-600 select-none">
            Detalle técnico del error
          </summary>
          <pre className="mt-2 whitespace-pre-wrap break-all text-[11px] font-mono text-slate-700 bg-white p-2 rounded border border-slate-200 max-h-32 overflow-y-auto">
            {errorMessage}
          </pre>
        </details>
      </div>
    </div>
  );
}
