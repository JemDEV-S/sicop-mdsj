/**
 * Página Panel (home del panel interno) — Panel Interno v2.
 *
 * Ruta: /interno (index). Protegida por RequireAuth.
 *
 * Es el "Panel de decisión": lectura ejecutiva del pliego (KPIs SIAF, embudo de
 * fases, pipeline por macrofase, bandeja de acción y focos de atención), sobre
 * los endpoints reales de saldos/alertas. Sigue llamándose "Panel".
 */
import PanelDecision from '@/features/panel/PanelDecision';

export default function Dashboard() {
  return <PanelDecision />;
}
