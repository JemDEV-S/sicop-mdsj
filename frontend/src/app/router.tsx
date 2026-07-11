import { createBrowserRouter } from 'react-router-dom';
import PublicLayout from './layouts/PublicLayout';
import InternoLayout from './layouts/InternoLayout';
import RequireAuth from '../features/auth/RequireAuth';
import RequireRole from '../features/auth/RequireRole';
import Login from '../pages/auth/Login';

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
        element: <Login />
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
