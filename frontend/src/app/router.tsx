import { createBrowserRouter } from 'react-router-dom';
import PublicLayout from './layouts/PublicLayout';
import InternoLayout from './layouts/InternoLayout';
import RequireAuth from '../features/auth/RequireAuth';
import RequireRole from '../features/auth/RequireRole';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <PublicLayout />,
    children: [
      {
        index: true,
        element: <div>Portal público — en construcción</div>
      },
      {
        path: 'login',
        element: <div>Login (Página Pública temporal)</div> // TODO T-35: Reemplazar por Login page real
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
