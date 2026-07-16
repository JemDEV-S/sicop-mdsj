import { Link } from 'react-router-dom';
import { ArrowRight, Wallet } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import Semaforo from '@/components/Semaforo';
import { formatearMoneda, formatPorcentaje } from '@/lib/formatters';
import { mapSemaforoApiToEstado } from '@/features/obras/api';
import type { MetaCritica, SaldosResumen } from '../types';

interface WidgetSaldosProps {
  resumen: SaldosResumen;
}

export function WidgetSaldos({ resumen }: WidgetSaldosProps) {
  const semaforoEstado = mapSemaforoApiToEstado(resumen.semaforo);
  const porcentaje = formatPorcentaje(resumen.porcentaje_devengado);
  const sinDatos = resumen.pim <= 0;

  return (
    <SectionCard
      titulo="Saldo de la unidad"
      icono={Wallet}
      padding="md"
      className="h-full flex flex-col"
      accion={
        <Link
          to="/interno/saldos"
          className="text-xs text-primary hover:underline inline-flex items-center gap-1"
        >
          Ver saldos <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      }
    >
      <div data-testid="widget-saldos" className="flex flex-col gap-3">
        <div>
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
            Saldo disponible
          </p>
          <p className="text-2xl font-bold text-foreground leading-tight">
            {formatearMoneda(resumen.saldo_disponible)}
          </p>
        </div>

        {!sinDatos ? (
          <>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <dt className="text-muted-foreground">PIM</dt>
              <dd className="text-right font-medium text-foreground">
                {formatearMoneda(resumen.pim)}
              </dd>
              <dt className="text-muted-foreground">Devengado</dt>
              <dd className="text-right font-medium text-foreground">
                {formatearMoneda(resumen.devengado)}
              </dd>
              <dt className="text-muted-foreground">Ejecución</dt>
              <dd className="text-right font-semibold text-foreground">{porcentaje}</dd>
              <dt className="text-muted-foreground">Metas activas</dt>
              <dd className="text-right font-medium text-foreground">
                {resumen.metas_total}
                {resumen.metas_criticas > 0 ? (
                  <span className="text-destructive font-semibold ml-1">
                    · {resumen.metas_criticas} críticas
                  </span>
                ) : null}
              </dd>
            </dl>

            {semaforoEstado ? (
              <Semaforo estado={semaforoEstado} texto={etiquetaSemaforo(semaforoEstado)} />
            ) : null}

            {resumen.top_metas_criticas.length > 0 ? (
              <TopMetasCriticas metas={resumen.top_metas_criticas} />
            ) : null}
          </>
        ) : (
          <p className="text-sm text-muted-foreground">
            No hay presupuesto asignado para el año y unidad seleccionados.
          </p>
        )}
      </div>
    </SectionCard>
  );
}

function etiquetaSemaforo(estado: 'ok' | 'alerta' | 'critico'): string {
  if (estado === 'ok') return 'Ejecución normal';
  if (estado === 'alerta') return 'Ejecución en atención';
  return 'Ejecución crítica';
}

function TopMetasCriticas({ metas }: { metas: MetaCritica[] }) {
  return (
    <div className="pt-3 border-t border-border">
      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
        Top metas críticas
      </p>
      <ul className="space-y-1.5">
        {metas.map((m) => (
          <li key={m.sec_func} className="flex items-center justify-between gap-2 text-xs">
            <span className="text-foreground truncate" title={m.nombre_meta ?? ''}>
              <span className="font-mono text-muted-foreground mr-1">
                {String(m.sec_func).padStart(4, '0')}
              </span>
              {m.nombre_meta ?? 'Sin nombre'}
            </span>
            <span className="text-destructive font-semibold shrink-0">
              {formatPorcentaje(m.porcentaje_devengado)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default WidgetSaldos;
