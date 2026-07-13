import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

type Tono = 'neutro' | 'primario' | 'secundario' | 'acento' | 'destructivo';

interface KpiCardProps {
  label: string;
  valor: React.ReactNode;
  ayuda?: React.ReactNode;
  icono?: LucideIcon;
  tono?: Tono;
  semaforo?: React.ReactNode;
  className?: string;
}

const tonoIcono: Record<Tono, string> = {
  neutro: 'text-muted-foreground',
  primario: 'text-primary',
  secundario: 'text-secondary',
  acento: 'text-accent-foreground',
  destructivo: 'text-destructive',
};

export function KpiCard({
  label,
  valor,
  ayuda,
  icono: Icono,
  tono = 'neutro',
  semaforo,
  className,
}: KpiCardProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-md p-5 flex flex-col gap-2',
        className,
      )}
    >
      <div className="flex items-center gap-2">
        {Icono ? (
          <Icono
            className={cn('w-4 h-4 shrink-0', tonoIcono[tono])}
            aria-hidden="true"
          />
        ) : null}
        <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {label}
        </span>
      </div>

      <div className="text-3xl font-bold text-foreground leading-tight">
        {valor}
      </div>

      {ayuda ? (
        <div className="text-sm text-muted-foreground">{ayuda}</div>
      ) : null}

      {semaforo ? <div className="mt-1">{semaforo}</div> : null}
    </div>
  );
}

export default KpiCard;
