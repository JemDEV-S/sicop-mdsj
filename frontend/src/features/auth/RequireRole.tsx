import { Navigate, Outlet } from 'react-router-dom';
import { useRole } from './hooks/useRole';

interface RequireRoleProps {
  role: string;
}

export default function RequireRole({ role }: RequireRoleProps) {
  const currentRole = useRole();
  
  // Falla cerrado: si no hay rol, o si el rol no coincide con el requerido, denegamos.
  const hasRequiredRole = currentRole === role;

  if (!hasRequiredRole) {
    // Si no tiene el rol, lo mandamos al inicio interno por defecto
    // (o a una página de "No autorizado")
    return <Navigate to="/interno" replace />;
  }

  return <Outlet />;
}
