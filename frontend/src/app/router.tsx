import { createBrowserRouter } from 'react-router-dom';
import PublicLayout from './layouts/PublicLayout';
import InternoLayout from './layouts/InternoLayout';
import RequireAuth from '../features/auth/RequireAuth';
import RequireRole from '../features/auth/RequireRole';
import Home from '../pages/publico/Home';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <Home />
      },
      {
        path: 'obras',
        lazy: async () => {
          const { default: ObrasListado } = await import('../pages/publico/ObrasListado');
          return { Component: ObrasListado };
        }
      },
      {
        path: 'obras/:codigo',
        lazy: async () => {
          const { default: Obra } = await import('../pages/publico/Obra');
          return { Component: Obra };
        }
      },
      {
        path: 'ejecucion',
        lazy: async () => {
          const { default: EjecucionDashboard } = await import('../pages/publico/EjecucionDashboard');
          return { Component: EjecucionDashboard };
        }
      },
      {
        path: 'ejecucion/detalle',
        lazy: async () => {
          const { default: EjecucionDetalle } = await import('../pages/publico/EjecucionDetalle');
          return { Component: EjecucionDetalle };
        }
      },
      {
        path: 'mapa',
        lazy: async () => {
          const { default: Mapa } = await import('../pages/publico/Mapa');
          return { Component: Mapa };
        }
      }
    ]
  },
  {
    // Login fuera del PublicLayout: pantalla completa sin header/footer público.
    path: '/login',
    lazy: async () => {
      const { default: Login } = await import('../pages/auth/Login');
      return { Component: Login };
    }
  },
  {
    path: '/interno',
    element: <RequireAuth />,
    children: [
      {
        element: <InternoLayout />,
        children: [
          {
            index: true,
            lazy: async () => {
              const { default: Dashboard } = await import('../pages/interno/Dashboard');
              return { Component: Dashboard };
            }
          },
          {
            path: 'analisis',
            lazy: async () => {
              const { default: Analisis } = await import('../pages/interno/Analisis');
              return { Component: Analisis };
            }
          },
          {
            path: 'cruce',
            lazy: async () => {
              const { default: Analisis } = await import('../pages/interno/Analisis');
              return { Component: () => <Analisis vistaInicial="cruce" /> };
            }
          },
          {
            path: 'ejecucion-siaf',
            lazy: async () => {
              const { default: Analisis } = await import('../pages/interno/Analisis');
              return { Component: () => <Analisis vistaInicial="ejecucion" /> };
            }
          },
          {
            path: 'pedidos/:nroPedido/:tipoBien/:tipoPedido',
            lazy: async () => {
              const { default: Pedido } = await import('../pages/interno/Pedido');
              return { Component: Pedido };
            }
          },
          {
            path: 'contratos',
            lazy: async () => {
              const { default: Contratos } = await import('../pages/interno/Contratos');
              return { Component: Contratos };
            }
          },
          {
            // TODO T-35: eliminar tras validar funcionalidad
            path: 'query-test',
            lazy: async () => {
              const { default: QueryTest } = await import('../pages/interno/QueryTest');
              return { Component: QueryTest };
            }
          },
          {
            // TODO T-36: eliminar tras validar funcionalidad
            path: 'sandbox',
            lazy: async () => {
              const { default: Sandbox } = await import('../pages/interno/Sandbox');
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
    children: [
      {
        element: <RequireRole role="admin" />,
        children: [
          {
            element: <InternoLayout />,
            children: [
              {
                index: true,
                element: <div>Dashboard Admin — en construcción</div>
              },
              {
                path: 'usuarios',
                lazy: async () => {
                  const { default: Usuarios } = await import('../pages/interno/Usuarios');
                  return { Component: Usuarios };
                }
              },
              {
                path: 'auditoria',
                lazy: async () => {
                  const { default: Auditoria } = await import('../pages/interno/Auditoria');
                  return { Component: Auditoria };
                }
              },
              {
                path: 'sincronizacion',
                lazy: async () => {
                  const { default: Sincronizacion } = await import('../pages/interno/Sincronizacion');
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
