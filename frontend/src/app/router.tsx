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
        element: <div data-testid="stub-ejecucion">Módulo Ejecución (En construcción)</div>
      },
      {
        path: 'proveedores',
        element: <div data-testid="stub-proveedores">Módulo Proveedores (En construcción)</div>
      },
      {
        path: 'mapa',
        lazy: async () => {
          const { default: Mapa } = await import('../pages/publico/Mapa');
          return { Component: Mapa };
        }
      },
      {
        path: 'login',
        lazy: async () => {
          const { default: Login } = await import('../pages/auth/Login');
          return { Component: Login };
        }
      }
    ]
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
            element: <div>Dashboard Interno — en construcción</div>
          },
          {
            path: 'saldos',
            element: <div>Módulo Saldos (Stub)</div>
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
                element: <div>Gestión de Usuarios (Stub)</div>
              }
            ]
          }
        ]
      }
    ]
  }
]);
