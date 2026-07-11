import { useEffect } from 'react';
import { RouterProvider } from 'react-router-dom';
import { router } from './router';
import { useAuthStore } from '../store/auth';

export default function App() {
  useEffect(() => {
    // Al arrancar la SPA, intentamos hidratar la sesión
    useAuthStore.getState().checkAuth();
  }, []);

  return <RouterProvider router={router} />;
}
