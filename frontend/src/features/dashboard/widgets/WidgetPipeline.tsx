import { GitBranch } from 'lucide-react';
import { SectionCard } from '@/components/layout/SectionCard';
import type { PipelineResumen } from '../types';

interface WidgetPipelineProps {
  pipeline: PipelineResumen;
}

const etapasConfig = [
  { key: 'solicitados' as const, label: 'Solicitados', color: 'var(--chart-1)' },
  { key: 'con_orden' as const, label: 'Con orden', color: 'var(--chart-2)' },
  { key: 'conformidad' as const, label: 'Conformidad', color: 'var(--chart-3)' },
  { key: 'devengado' as const, label: 'Devengado', color: 'var(--chart-4)' },
  { key: 'cerrado' as const, label: 'Cerrado', color: 'var(--chart-5)' },
];

export function WidgetPipeline({ pipeline }: WidgetPipelineProps) {
  const etapas = etapasConfig.map((e) => ({ ...e, valor: pipeline[e.key] }));
  const total = etapas.reduce((sum, e) => sum + e.valor, 0);

  return (
    <SectionCard titulo="Pipeline" icono={GitBranch} padding="md" className="h-full">
      <div data-testid="widget-pipeline">
        <p className="text-2xl font-bold text-foreground mb-3">
          {total} <span className="text-sm font-normal text-muted-foreground">pedidos</span>
        </p>

        {total > 0 ? (
          <div
            className="flex h-2 rounded-full overflow-hidden mb-3 bg-muted"
            role="img"
            aria-label={`Distribución: ${etapas.map((e) => `${e.label} ${e.valor}`).join(', ')}`}
          >
            {etapas.map((e) =>
              e.valor > 0 ? (
                <div
                  key={e.label}
                  style={{ width: `${(e.valor / total) * 100}%`, backgroundColor: e.color }}
                  title={`${e.label}: ${e.valor}`}
                />
              ) : null,
            )}
          </div>
        ) : null}

        <ul className="grid grid-cols-2 gap-1.5">
          {etapas.map((e) => (
            <li
              key={e.label}
              className="flex items-center gap-1.5 text-xs text-muted-foreground"
            >
              <span
                className="inline-block w-2 h-2 rounded-full shrink-0"
                style={{ backgroundColor: e.color }}
                aria-hidden="true"
              />
              <span>{e.label}</span>
              <span className="font-semibold ml-auto text-foreground">{e.valor}</span>
            </li>
          ))}
        </ul>
      </div>
    </SectionCard>
  );
}

export default WidgetPipeline;
