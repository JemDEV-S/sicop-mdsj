// Presentaciones de fases SIAF para los modales.
//   - FasesColumnas: círculos centrados con label + monto + badge (modal orden).
//   - BarrasFaseMonto: barras horizontales con label + monto (modal expediente).
// Ambas reciben las fases ya derivadas del estado SIAF real (sin inventar).

import { cn } from '@/lib/utils';
import type { Tono } from '@/features/panel/ui/primitivas';

export interface FaseCol {
  label: string;
  hecho: boolean;
  monto?: string;
  badge: string;
  badgeTono: Tono;
}

const BADGE_TONO: Record<Tono, string> = {
  ok: 'border-secondary/40 bg-secondary/10 text-secondary-foreground',
  primary: 'border-primary/30 bg-primary/10 text-primary',
  accent: 'border-accent/40 bg-accent/15 text-accent-foreground',
  alerta: 'border-accent/40 bg-accent/15 text-accent-foreground',
  critico: 'border-destructive/40 bg-destructive/10 text-destructive',
  neutral: 'border-border bg-superficie-alt text-muted-foreground',
};

export function FasesColumnas({ fases }: { fases: FaseCol[] }) {
  return (
    <div className="flex flex-wrap gap-y-4">
      {fases.map((f, i) => {
        const anillo = f.hecho
          ? f.badgeTono === 'ok'
            ? 'bg-secondary border-secondary text-secondary-foreground'
            : 'bg-primary border-primary text-primary-foreground'
          : 'bg-card border-border text-muted-foreground';
        return (
          <div key={f.label} className="flex items-start">
            <div className="flex w-[104px] flex-col items-center gap-1.5 text-center">
              <span
                className={cn(
                  'flex h-[26px] w-[26px] items-center justify-center rounded-full border-2 font-mono text-[11px] font-semibold',
                  anillo,
                )}
                aria-hidden="true"
              >
                {f.hecho ? '✓' : ''}
              </span>
              <span className={cn('text-[11px]', f.hecho ? 'font-semibold text-foreground' : 'text-muted-foreground')}>
                {f.label}
              </span>
              {f.monto ? (
                <span className="font-mono text-[11.5px] tabular-nums text-foreground">{f.monto}</span>
              ) : null}
              <span className={cn('rounded border px-1.5 py-px text-[9px] font-semibold', BADGE_TONO[f.badgeTono])}>
                {f.badge}
              </span>
            </div>
            {i < fases.length - 1 ? (
              <span
                className={cn('mt-3 h-0.5 w-3.5 shrink-0', f.hecho ? 'bg-secondary/50' : 'bg-border')}
                aria-hidden="true"
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

export interface BarraFaseMonto {
  label: string;
  valor: string;
  ancho: number; // 0..100
  barraClass?: string;
}

export function BarrasFaseMonto({ filas }: { filas: BarraFaseMonto[] }) {
  return (
    <div className="flex flex-col gap-2">
      {filas.map((f) => (
        <div key={f.label} className="flex items-center gap-2.5">
          <span className="w-20 shrink-0 text-[11.5px] text-foreground">{f.label}</span>
          <div className="h-3.5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
            <div className={cn('h-full', f.barraClass ?? 'bg-primary')} style={{ width: `${Math.min(100, Math.max(0, f.ancho))}%` }} />
          </div>
          <span className="w-24 shrink-0 text-right font-mono text-[11.5px] tabular-nums text-foreground">
            {f.valor}
          </span>
        </div>
      ))}
    </div>
  );
}
