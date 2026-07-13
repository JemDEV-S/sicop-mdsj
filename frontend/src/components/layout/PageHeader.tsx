import * as React from 'react';
import { cn } from '@/lib/utils';

type Densidad = 'publico' | 'interno';

interface PageHeaderProps {
  titulo: string;
  descripcion?: React.ReactNode;
  acciones?: React.ReactNode;
  breadcrumbs?: React.ReactNode;
  densidad?: Densidad;
  className?: string;
}

export function PageHeader({
  titulo,
  descripcion,
  acciones,
  breadcrumbs,
  densidad = 'interno',
  className,
}: PageHeaderProps) {
  const tituloClases =
    densidad === 'publico'
      ? 'text-3xl md:text-4xl font-bold text-foreground'
      : 'text-2xl font-bold text-foreground';

  const espaciadoInferior = densidad === 'publico' ? 'pb-8 mb-8' : 'pb-6 mb-6';

  return (
    <header className={cn('border-b border-border', espaciadoInferior, className)}>
      {breadcrumbs ? <div className="mb-3">{breadcrumbs}</div> : null}

      <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0 flex-1">
          <h1 className={tituloClases}>{titulo}</h1>
          {descripcion ? (
            <p className="mt-2 text-sm text-muted-foreground md:text-base">
              {descripcion}
            </p>
          ) : null}
        </div>

        {acciones ? (
          <div className="flex flex-wrap items-center gap-2 md:justify-end">
            {acciones}
          </div>
        ) : null}
      </div>
    </header>
  );
}

export default PageHeader;
