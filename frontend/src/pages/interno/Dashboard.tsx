/**
 * Página de Dashboard Interno (HU-22, T-44).
 *
 * Ruta: /interno (index)
 * Protegida por RequireAuth.
 */
import DashboardWidgets from '../../features/dashboard/secciones/DashboardWidgets';

export default function Dashboard() {
  return <DashboardWidgets />;
}
