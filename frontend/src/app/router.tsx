import { createBrowserRouter } from 'react-router-dom';
import PublicLayout from './layouts/PublicLayout';
import InternoLayout from './layouts/InternoLayout';
import RequireAuth from '../features/auth/RequireAuth';
import RequireRole from '../features/auth/RequireRole';
import Home from '../pages/publico/Home';
import RouteErrorBoundary from './RouteErrorBoundary';

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

/**
 * Importación dinámica segura: si el servidor desplegó una nueva versión y
 * el chunk previo retorna 404, limpia cachés y recarga automáticamente a la versión actual.
 */
async function safeImport<T>(factory: () => Promise<T>): Promise<T> {
  try {
    return await factory();
  } catch (error) {
    if (isChunkError(error)) {
      const reloadKey = 'sicop_safe_import_reload';
      const last = sessionStorage.getItem(reloadKey);
      const now = Date.now();
      if (!last || now - Number(last) > 15000) {
        sessionStorage.setItem(reloadKey, String(now));
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
        return new Promise<T>(() => {});
      }
    }
    throw error;
  }
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: <PublicLayout />,
    ErrorBoundary: RouteErrorBoundary,
    children: [
      {
        index: true,
        element: <Home />
      },
      {
        path: 'obras',
        lazy: async () => {
          const { default: ObrasListado } = await safeImport(() => import('../pages/publico/ObrasListado'));
          return { Component: ObrasListado };
        }
      },
      {
        path: 'obras/:codigo',
        lazy: async () => {
          const { default: Obra } = await safeImport(() => import('../pages/publico/Obra'));
          return { Component: Obra };
        }
      },
      {
        path: 'ejecucion',
        lazy: async () => {
          const { default: EjecucionDashboard } = await safeImport(() => import('../pages/publico/EjecucionDashboard'));
          return { Component: EjecucionDashboard };
        }
      },
      {
        path: 'ejecucion/detalle',
        lazy: async () => {
          const { default: EjecucionDetalle } = await safeImport(() => import('../pages/publico/EjecucionDetalle'));
          return { Component: EjecucionDetalle };
        }
      },
      {
        path: 'mapa',
        lazy: async () => {
          const { default: Mapa } = await safeImport(() => import('../pages/publico/Mapa'));
          return { Component: Mapa };
        }
      }
    ]
  },
  {
    // Login fuera del PublicLayout: pantalla completa sin header/footer público.
    path: '/login',
    ErrorBoundary: RouteErrorBoundary,
    lazy: async () => {
      const { default: Login } = await safeImport(() => import('../pages/auth/Login'));
      return { Component: Login };
    }
  },
  {
    path: '/interno',
    element: <RequireAuth />,
    ErrorBoundary: RouteErrorBoundary,
    children: [
      {
        element: <InternoLayout />,
        ErrorBoundary: RouteErrorBoundary,
        children: [
          {
            index: true,
            lazy: async () => {
              const { default: Dashboard } = await safeImport(() => import('../pages/interno/Dashboard'));
              return { Component: Dashboard };
            }
          },
          {
            path: 'analisis',
            lazy: async () => {
              const { default: Analisis } = await safeImport(() => import('../pages/interno/Analisis'));
              return { Component: Analisis };
            }
          },
          {
            path: 'cruce',
            lazy: async () => {
              const { default: Analisis } = await safeImport(() => import('../pages/interno/Analisis'));
              return { Component: () => <Analisis vistaInicial="cruce" /> };
            }
          },
          {
            path: 'ejecucion-siaf',
            lazy: async () => {
              const { default: Analisis } = await safeImport(() => import('../pages/interno/Analisis'));
              return { Component: () => <Analisis vistaInicial="ejecucion" /> };
            }
          },
          {
            path: 'pedidos/:nroPedido/:tipoBien/:tipoPedido',
            lazy: async () => {
              const { default: Pedido } = await safeImport(() => import('../pages/interno/Pedido'));
              return { Component: Pedido };
            }
          },
          {
            path: 'contratos',
            lazy: async () => {
              const { default: Contratos } = await safeImport(() => import('../pages/interno/Contratos'));
              return { Component: Contratos };
            }
          },
          {
            // TODO T-35: eliminar tras validar funcionalidad
            path: 'query-test',
            lazy: async () => {
              const { default: QueryTest } = await safeImport(() => import('../pages/interno/QueryTest'));
              return { Component: QueryTest };
            }
          },
          {
            // TODO T-36: eliminar tras validar funcionalidad
            path: 'sandbox',
            lazy: async () => {
              const { default: Sandbox } = await safeImport(() => import('../pages/interno/Sandbox'));
              return { Component: Sandbox };
            }
          }
        ]
      }
    ]
  },
  {
    path: '/admin',
    element: <RequireAuth />,
    ErrorBoundary: RouteErrorBoundary,
    children: [
      {
        element: <RequireRole role="admin" />,
        children: [
          {
            element: <InternoLayout />,
            ErrorBoundary: RouteErrorBoundary,
            children: [
              {
                index: true,
                element: <div>Dashboard Admin — en construcción</div>
              },
              {
                path: 'usuarios',
                lazy: async () => {
                  const { default: Usuarios } = await safeImport(() => import('../pages/interno/Usuarios'));
                  return { Component: Usuarios };
                }
              },
              {
                path: 'auditoria',
                lazy: async () => {
                  const { default: Auditoria } = await safeImport(() => import('../pages/interno/Auditoria'));
                  return { Component: Auditoria };
                }
              },
              {
                path: 'sincronizacion',
                lazy: async () => {
                  const { default: Sincronizacion } = await safeImport(() => import('../pages/interno/Sincronizacion'));
                  return { Component: Sincronizacion };
                }
              }
            ]
          }
        ]
      }
    ]
  }
]);
