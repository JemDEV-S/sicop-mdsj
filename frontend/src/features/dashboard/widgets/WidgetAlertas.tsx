import { AlertTriangle } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import type { AlertasResumen } from '../types';

interface WidgetAlertasProps {
  alertas: AlertasResumen;
}

export function WidgetAlertas({ alertas }: WidgetAlertasProps) {
  const total =
    alertas.pedidos_estancados + alertas.contratos_por_vencer + alertas.metas_rezagadas;

  return (
    <SectionCard
      titulo="Alertas"
      icono={AlertTriangle}
      padding="md"
      className="h-full"
    >
      <div data-testid="widget-alertas">
        {total === 0 ? (
          <EmptyState
            icono={AlertTriangle}
            titulo="Sin alertas pendientes"
            descripcion="No hay pedidos estancados, contratos por vencer ni metas rezagadas."
          />
        ) : (
          <ul className="space-y-2">
            {alertas.pedidos_estancados > 0 ? (
              <Fila
                label="Pedidos estancados"
                valor={alertas.pedidos_estancados}
                severidad="alerta"
              />
            ) : null}
            {alertas.contratos_por_vencer > 0 ? (
              <Fila
                label="Contratos por vencer"
                valor={alertas.contratos_por_vencer}
                severidad="alerta"
              />
            ) : null}
            {alertas.metas_rezagadas > 0 ? (
              <Fila
                label="Metas rezagadas"
                valor={alertas.metas_rezagadas}
                severidad="critico"
              />
            ) : null}
          </ul>
        )}
      </div>
    </SectionCard>
  );
}

type Severidad = 'alerta' | 'critico';

function Fila({
  label,
  valor,
  severidad,
}: {
  label: string;
  valor: number;
  severidad: Severidad;
}) {
  const color =
    severidad === 'critico' ? 'text-destructive' : 'text-accent-foreground';
  return (
    <li className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{label}</span>
      <span className={`font-bold ${color}`}>{valor}</span>
    </li>
  );
}

export default WidgetAlertas;
