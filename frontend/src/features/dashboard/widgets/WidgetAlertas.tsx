import { AlertTriangle, ArrowRight, Clock, FileWarning, TrendingDown } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';

interface WidgetAlertasProps {
  pedidosEstancados: number;
  contratosPorVencer: number;
  metasRezagadas: number;
}

/**
 * Widget consolidado de alertas del funcionario (HU-11 + HU-16 + HU-20).
 * Cada fila enlaza a la vista dedicada del alerta (T-47/T-49/T-53).
 */
export function WidgetAlertas({
  pedidosEstancados,
  contratosPorVencer,
  metasRezagadas,
}: WidgetAlertasProps) {
  const total = pedidosEstancados + contratosPorVencer + metasRezagadas;

  return (
    <SectionCard
      titulo="Alertas del día"
      icono={AlertTriangle}
      padding="md"
      className="h-full flex flex-col"
    >
      <div data-testid="widget-alertas" className="flex flex-col gap-2">
        {total === 0 ? (
          <EmptyState
            icono={AlertTriangle}
            titulo="Sin alertas pendientes"
            descripcion="Nada estancado, sin contratos por vencer y todas las metas ejecutan a tiempo."
          />
        ) : (
          <>
            <Fila
              icono={Clock}
              label="Pedidos estancados"
              valor={pedidosEstancados}
              href="/interno/pipeline?filtro=estancados"
              severidad="alerta"
              hint=">15 días sin avance"
            />
            <Fila
              icono={TrendingDown}
              label="Metas rezagadas"
              valor={metasRezagadas}
              href="/interno/saldos?filtro=rezagadas"
              severidad="critico"
              hint="< 50% devengado"
            />
            <Fila
              icono={FileWarning}
              label="Contratos por vencer"
              valor={contratosPorVencer}
              href="/interno/contratos?filtro=por-vencer"
              severidad="alerta"
              hint="Próximos 30 días"
            />
          </>
        )}
      </div>
    </SectionCard>
  );
}

type Severidad = 'alerta' | 'critico';

interface FilaProps {
  icono: LucideIcon;
  label: string;
  valor: number;
  href: string;
  severidad: Severidad;
  hint: string;
}

function Fila({ icono: Icono, label, valor, href, severidad, hint }: FilaProps) {
  const disabled = valor === 0;
  const colorValor =
    severidad === 'critico' ? 'text-destructive' : 'text-accent-foreground';

  const contenido = (
    <div className="flex items-center gap-3 py-1.5">
      <Icono
        className={`w-4 h-4 shrink-0 ${disabled ? 'text-muted-foreground' : colorValor}`}
        aria-hidden="true"
      />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-foreground leading-tight">{label}</p>
        <p className="text-xs text-muted-foreground leading-tight">{hint}</p>
      </div>
      <span
        className={`font-bold text-lg tabular-nums ${
          disabled ? 'text-muted-foreground' : colorValor
        }`}
      >
        {valor}
      </span>
      {!disabled ? (
        <ArrowRight className="w-4 h-4 text-muted-foreground shrink-0" aria-hidden="true" />
      ) : null}
    </div>
  );

  if (disabled) {
    return <div className="opacity-60">{contenido}</div>;
  }

  return (
    <Link
      to={href}
      className="block rounded-md px-2 -mx-2 hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring transition-colors"
    >
      {contenido}
    </Link>
  );
}

export default WidgetAlertas;
