import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ChevronDown, ChevronRight, GitBranch } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import { EmptyState } from '@/components/layout/EmptyState';
import type { Macrofase, MacrofaseConteo } from '../types';

interface WidgetPipelineProps {
  macrofases: MacrofaseConteo[];
}

/**
 * Pipeline canonico de 6 macrofases (Docs/exploracion-siga-pipeline-extendido.md §17.6):
 *   solicitud → programacion → certificacion → contratacion → ejecucion → cierre
 *
 * Cada macrofase es expandible a las 13 etapas de servicios / 16 de bienes.
 * Color gradado segun avance; cierre en gris (no requiere accion).
 */
const MACRO_ESTILO: Record<Macrofase, { className: string; dotClass: string }> = {
  solicitud:     { className: 'bg-primary/20', dotClass: 'bg-primary/20 border border-primary/40' },
  programacion:  { className: 'bg-primary/35', dotClass: 'bg-primary/35 border border-primary/50' },
  certificacion: { className: 'bg-primary/55', dotClass: 'bg-primary/55 border border-primary/70' },
  contratacion:  { className: 'bg-primary/70', dotClass: 'bg-primary/70 border border-primary' },
  ejecucion:     { className: 'bg-secondary',  dotClass: 'bg-secondary border border-secondary' },
  cierre:        { className: 'bg-muted-foreground/40', dotClass: 'bg-muted-foreground/40 border border-muted-foreground/60' },
};

export function WidgetPipeline({ macrofases }: WidgetPipelineProps) {
  const [expandida, setExpandida] = useState<Macrofase | null>(null);

  const activos = macrofases
    .filter((m) => m.macrofase !== 'cierre')
    .reduce((acc, m) => acc + m.conteo, 0);
  const cerrados = macrofases.find((m) => m.macrofase === 'cierre')?.conteo ?? 0;
  const total = activos + cerrados;

  const filas = macrofases.map((m) => ({
    ...m,
    estilo: MACRO_ESTILO[m.macrofase],
  }));

  return (
    <SectionCard
      titulo="Pipeline de pedidos"
      icono={GitBranch}
      padding="md"
      className="h-full flex flex-col"
      accion={
        <Link
          to="/interno/pipeline"
          className="text-xs text-primary hover:underline inline-flex items-center gap-1"
        >
          Ver pipeline <ArrowRight className="w-3 h-3" aria-hidden="true" />
        </Link>
      }
    >
      <div data-testid="widget-pipeline" className="flex flex-col gap-3">
        {total === 0 ? (
          <EmptyState
            icono={GitBranch}
            titulo="Sin pedidos registrados"
            descripcion="No hay pedidos para el año y unidad seleccionados."
          />
        ) : (
          <>
            <div>
              <p className="text-2xl font-bold text-foreground leading-tight">
                {activos}{' '}
                <span className="text-sm font-normal text-muted-foreground">
                  activos
                </span>
              </p>
              <p className="text-xs text-muted-foreground">
                {total} pedidos totales · {cerrados} cerrados
              </p>
            </div>

            {total > 0 ? (
              <div
                className="flex h-2 rounded-full overflow-hidden bg-muted"
                role="img"
                aria-label={`Distribución del pipeline: ${filas
                  .map((f) => `${f.macrofase_label} ${f.conteo}`)
                  .join(', ')}`}
              >
                {filas.map((f) =>
                  f.conteo > 0 ? (
                    <div
                      key={f.macrofase}
                      className={f.estilo.className}
                      style={{ width: `${(f.conteo / total) * 100}%` }}
                      title={`${f.macrofase_label}: ${f.conteo}`}
                    />
                  ) : null,
                )}
              </div>
            ) : null}

            <ul className="flex flex-col gap-1">
              {filas.map((f) => {
                const expandido = expandida === f.macrofase;
                const puedeExpandir = f.etapas.length > 0 && f.conteo > 0;
                return (
                  <li key={f.macrofase} className="flex flex-col">
                    <button
                      type="button"
                      onClick={() =>
                        puedeExpandir
                          ? setExpandida(expandido ? null : f.macrofase)
                          : undefined
                      }
                      disabled={!puedeExpandir}
                      className={`flex items-center gap-2 text-xs py-1 px-1 -mx-1 rounded ${
                        puedeExpandir
                          ? 'hover:bg-muted/60 cursor-pointer'
                          : 'cursor-default opacity-70'
                      }`}
                      aria-expanded={expandido}
                    >
                      {puedeExpandir ? (
                        expandido ? (
                          <ChevronDown className="w-3 h-3 shrink-0" aria-hidden="true" />
                        ) : (
                          <ChevronRight className="w-3 h-3 shrink-0" aria-hidden="true" />
                        )
                      ) : (
                        <span className="w-3 h-3 shrink-0" aria-hidden="true" />
                      )}
                      <span
                        className={`inline-block w-2.5 h-2.5 rounded-full shrink-0 ${f.estilo.dotClass}`}
                        aria-hidden="true"
                      />
                      <span className="text-muted-foreground">
                        {f.macrofase_label}
                      </span>
                      <span className="font-semibold ml-auto text-foreground tabular-nums">
                        {f.conteo}
                      </span>
                    </button>

                    {expandido ? (
                      <ul className="ml-8 mt-1 mb-1 flex flex-col gap-0.5 border-l border-border/40 pl-3">
                        {f.etapas.map((e) => (
                          <li
                            key={e.etapa}
                            className="flex items-center gap-2 text-xs py-0.5"
                          >
                            <span className="text-muted-foreground/70 tabular-nums w-6 text-right">
                              [{e.etapa_numero}]
                            </span>
                            <span className="text-muted-foreground truncate">
                              {e.etapa_label}
                            </span>
                            <span className="font-medium ml-auto tabular-nums text-foreground/80">
                              {e.conteo}
                            </span>
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          </>
        )}
      </div>
    </SectionCard>
  );
}

export default WidgetPipeline;
