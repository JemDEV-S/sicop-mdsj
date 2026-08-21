// Primitivas visuales reutilizables del Panel Interno v2.
//
// Se comparten entre el Panel de decisión, el Análisis por meta y el Cruce
// SIAF↔SIGA. Usan SOLO tokens del sistema de diseño (primary/secondary/accent/
// destructive/semaforo-*), nunca hex crudos, y comunican estado con color +
// TEXTO (nunca color solo). Sin emojis.

import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/utils';

// ─── Tono de estado (semáforo genérico) ──────────────────────────────────

export type Tono = 'ok' | 'alerta' | 'accent' | 'critico' | 'neutral' | 'primary';

const TONO_CHIP: Record<Tono, string> = {
  ok: 'bg-semaforo-ok/15 text-secondary-foreground ring-1 ring-inset ring-semaforo-ok/40',
  alerta: 'bg-semaforo-alerta/20 text-accent-foreground ring-1 ring-inset ring-semaforo-alerta/50',
  accent: 'bg-accent/20 text-accent-foreground ring-1 ring-inset ring-accent/50',
  critico: 'bg-semaforo-critico/15 text-destructive ring-1 ring-inset ring-semaforo-critico/40',
  neutral: 'bg-muted text-muted-foreground ring-1 ring-inset ring-border',
  primary: 'bg-primary/10 text-primary ring-1 ring-inset ring-primary/30',
};

const TONO_PUNTO: Record<Tono, string> = {
  ok: 'bg-semaforo-ok',
  alerta: 'bg-semaforo-alerta',
  accent: 'bg-accent',
  critico: 'bg-semaforo-critico',
  neutral: 'bg-muted-foreground',
  primary: 'bg-primary',
};

const TONO_BORDE_IZQ: Record<Tono, string> = {
  ok: 'border-l-secondary',
  alerta: 'border-l-accent',
  accent: 'border-l-accent',
  critico: 'border-l-destructive',
  neutral: 'border-l-muted-foreground',
  primary: 'border-l-primary',
};

/** Chip de estado: punto de color + texto. Nunca color solo. */
export function EstadoChip({
  tono,
  children,
  tamano = 'sm',
  punto = true,
  title,
  className,
}: {
  tono: Tono;
  children: React.ReactNode;
  tamano?: 'sm' | 'xs';
  punto?: boolean;
  title?: string;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-semibold',
        tamano === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-1.5 py-0.5 text-[10px]',
        TONO_CHIP[tono],
        className,
      )}
      title={title}
    >
      {punto ? (
        <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', TONO_PUNTO[tono])} aria-hidden="true" />
      ) : null}
      {children}
    </span>
  );
}

/** Clase del borde izquierdo de color, para tarjetas con acento por tono. */
export function bordeIzquierdo(tono: Tono): string {
  return cn('border-l-4', TONO_BORDE_IZQ[tono]);
}

// ─── Sección con cabecera ligera (estilo v2) ─────────────────────────────

export function PanelSection({
  titulo,
  aside,
  nota,
  children,
  className,
  bodyClassName,
}: {
  titulo: React.ReactNode;
  aside?: React.ReactNode;
  nota?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <section className={cn('flex flex-col gap-3 rounded-lg border border-border bg-card px-4 py-4', className)}>
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold text-foreground">{titulo}</h3>
        {aside ? <div className="text-[11px] text-muted-foreground">{aside}</div> : null}
      </div>
      <div className={cn('flex flex-col gap-2', bodyClassName)}>{children}</div>
      {nota ? <p className="text-[11px] leading-relaxed text-muted-foreground">{nota}</p> : null}
    </section>
  );
}

// ─── KPI ─────────────────────────────────────────────────────────────────

export interface KpiChip {
  texto: string;
  tono: Tono;
}

export function KpiTile({
  label,
  fuente,
  valor,
  ayuda,
  valorClass,
  chip,
  icono: Icono,
}: {
  label: string;
  fuente?: string;
  valor: React.ReactNode;
  ayuda?: React.ReactNode;
  valorClass?: string;
  chip?: KpiChip;
  icono?: LucideIcon;
}) {
  return (
    <div className="flex flex-col gap-1.5 rounded-lg border border-border bg-card px-4 py-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-etiqueta flex items-center gap-1.5 text-muted-foreground">
          {Icono ? <Icono className="h-3.5 w-3.5 text-primary" aria-hidden="true" /> : null}
          {label}
        </span>
        {fuente ? (
          <span className="text-microdato rounded border border-border px-1 py-px text-muted-foreground">
            {fuente}
          </span>
        ) : null}
      </div>
      <div className={cn('text-cifra-lg text-foreground', valorClass)}>
        {valor}
      </div>
      {ayuda ? <div className="text-[11.5px] leading-snug text-muted-foreground">{ayuda}</div> : null}
      {chip ? (
        <EstadoChip tono={chip.tono} className="mt-0.5 self-start">
          {chip.texto}
        </EstadoChip>
      ) : null}
    </div>
  );
}

// ─── Barra de fase / progreso etiquetada ─────────────────────────────────

export function BarraFase({
  label,
  valorTexto,
  pctTexto,
  ancho,
  barraClass = 'bg-primary',
  labelAncho = 'w-24',
  sub,
}: {
  label: string;
  valorTexto?: React.ReactNode;
  pctTexto?: React.ReactNode;
  ancho: number; // 0..100
  barraClass?: string;
  labelAncho?: string;
  sub?: React.ReactNode;
}) {
  const w = Math.min(100, Math.max(0, ancho));
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-3">
        <span className={cn('shrink-0 text-[11.5px] font-semibold text-foreground', labelAncho)}>{label}</span>
        <div className="h-5 min-w-0 flex-1 overflow-hidden rounded bg-muted">
          <div className={cn('h-full rounded', barraClass)} style={{ width: `${w}%` }} />
        </div>
        {valorTexto != null ? (
          <span className="w-28 shrink-0 text-right font-mono text-[11.5px] tabular-nums text-foreground">
            {valorTexto}
          </span>
        ) : null}
        {pctTexto != null ? (
          <span className="w-12 shrink-0 text-right font-mono text-[11px] text-muted-foreground">
            {pctTexto}
          </span>
        ) : null}
      </div>
      {sub ? <div className={cn(labelAncho === 'w-24' ? 'pl-24' : 'pl-20')}>{sub}</div> : null}
    </div>
  );
}
