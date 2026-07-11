import { createBrowserRouter } from 'react-router-dom';
import PublicLayout from './layouts/PublicLayout';
import InternoLayout from './layouts/InternoLayout';
import RequireAuth from '../features/auth/RequireAuth';
import RequireRole from '../features/auth/RequireRole';
import Login from '../pages/auth/Login';
import QueryTest from '../pages/interno/QueryTest';
import Sandbox from '../pages/interno/Sandbox';

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
          },
          {
            // TODO T-35: eliminar tras validar funcionalidad
            path: 'query-test',
            element: <QueryTest />
          },
          {
            // TODO T-36: eliminar tras validar funcionalidad
            path: 'sandbox',
            element: <Sandbox />
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
