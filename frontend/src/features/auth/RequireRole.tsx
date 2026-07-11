import { Navigate, Outlet } from 'react-router-dom';
// import { useAuthStore } from './store'; // TODO T-34: Importar estado global con el rol

interface RequireRoleProps {
  role: string;
}

export default function RequireRole({ role }: RequireRoleProps) {
  // TODO T-34: Obtener rol real del usuario desde Zustand
  // const userRole = useAuthStore(state => state.user?.role);
  
  // STUB: Actualmente fallamos cerrado (deny default) porque no tenemos el rol.
  // Usamos `role` para evitar warning de TS, pero forzamos false.
  const hasRequiredRole = Boolean(role) && false; 

  if (!hasRequiredRole) {
    // Si no tiene el rol, lo mandamos al inicio interno por defecto
    // (o a una página de "No autorizado")
    return <Navigate to="/interno" replace />;
  }

  return <Outlet />;
}
