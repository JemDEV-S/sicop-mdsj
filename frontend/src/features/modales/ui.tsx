// Primitivas de contenido para los modales apilables. Reutilizables por los
// cinco modales (pedido/orden/siaf/pecosa/reporte). Tokens del sistema de
// diseño, sin emojis, estado con color + texto.

import type { ReactNode } from 'react';
import { ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { EstadoChip, type Tono } from '@/features/panel/ui/primitivas';

// ─── Encabezado de un modal ──────────────────────────────────────────────

export function ModalHead({
  overline,
  titulo,
  mono,
  descripcion,
  chips,
  aside,
}: {
  overline: string;
  titulo: ReactNode;
  mono?: boolean;
  descripcion?: ReactNode;
  chips?: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-start gap-4">
      <div className="flex min-w-[240px] flex-1 flex-col gap-1.5">
        <span className="text-[10.5px] font-semibold uppercase tracking-wide text-muted-foreground">
          {overline}
        </span>
        <h2 className={cn('text-lg font-semibold text-foreground', mono && 'font-mono')}>{titulo}</h2>
        {descripcion ? (
          <p className="text-[13px] leading-relaxed text-muted-foreground">{descripcion}</p>
        ) : null}
        {chips ? <div className="mt-1 flex flex-wrap gap-1.5">{chips}</div> : null}
      </div>
      {aside ? <div className="flex shrink-0 flex-col items-end gap-1">{aside}</div> : null}
    </div>
  );
}

/** Chip informativo neutro (contexto: tipo, meta, rubro, solicitante…). */
export function ChipInfo({ children }: { children: ReactNode }) {
  return (
    <span className="rounded-full border border-border bg-muted/40 px-2.5 py-0.5 text-[11px] text-foreground">
      {children}
    </span>
  );
}

// ─── Sección con borde (bloque dentro del modal) ─────────────────────────

export function ModalBloque({
  titulo,
  accion,
  nota,
  children,
  className,
}: {
  titulo: ReactNode;
  accion?: ReactNode;
  nota?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn('flex flex-col gap-3 rounded-md border border-border px-4 py-4', className)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[13px] font-semibold text-foreground">{titulo}</h3>
        {accion ? <div className="shrink-0">{accion}</div> : null}
      </div>
      {children}
      {nota ? <p className="text-[10.5px] leading-relaxed text-muted-foreground">{nota}</p> : null}
    </section>
  );
}

// ─── Fila etiqueta → valor ───────────────────────────────────────────────

export function FilaDato({
  label,
  children,
  mono,
  anchoLabel = 'w-28',
}: {
  label: string;
  children: ReactNode;
  mono?: boolean;
  anchoLabel?: string;
}) {
  return (
    <div className="flex items-center gap-3 border-b border-border/60 py-1.5 last:border-0">
      <span className={cn('shrink-0 text-[11px] text-muted-foreground', anchoLabel)}>{label}</span>
      <span className={cn('min-w-0 flex-1 text-[12.5px] text-foreground', mono && 'font-mono')}>
        {children}
      </span>
    </div>
  );
}

// ─── Botón "ligado": salta a otro modal apilándolo ───────────────────────

export function BotonLigado({
  tipo,
  id,
  nota,
  onClick,
}: {
  tipo: string;
  id: ReactNode;
  nota?: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2.5 rounded-md border border-border bg-card px-3 py-2 text-left transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="w-16 shrink-0 text-[9.5px] uppercase tracking-wide text-muted-foreground">
        {tipo}
      </span>
      <span className="shrink-0 font-mono text-[12px] font-semibold text-primary">{id}</span>
      {nota ? (
        <span className="min-w-0 flex-1 truncate text-[11.5px] text-muted-foreground">{nota}</span>
      ) : null}
      <ArrowRight className="ml-auto h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
    </button>
  );
}

// ─── Paso de fase (círculo + etiqueta + monto), con conector opcional ────

export function PasoFase({
  label,
  hecho,
  tono = 'ok',
  monto,
  badge,
  badgeTono,
  conector,
}: {
  label: string;
  hecho: boolean;
  tono?: Tono;
  monto?: ReactNode;
  badge?: string;
  badgeTono?: Tono;
  conector: boolean;
}) {
  const anillo = hecho
    ? tono === 'ok'
      ? 'bg-secondary border-secondary text-secondary-foreground'
      : 'bg-accent border-accent text-accent-foreground'
    : 'bg-card border-border text-muted-foreground';
  return (
    <div className="flex items-start">
      <div className="flex w-24 flex-col items-center gap-1 text-center">
        <span
          className={cn(
            'flex h-6 w-6 items-center justify-center rounded-full border-2 font-mono text-[10px] font-semibold',
            anillo,
          )}
          aria-hidden="true"
        >
          {hecho ? '✓' : ''}
        </span>
        <span className={cn('text-[11px]', hecho ? 'font-semibold text-foreground' : 'text-muted-foreground')}>
          {label}
        </span>
        {monto != null ? (
          <span className="font-mono text-[11px] tabular-nums text-foreground">{monto}</span>
        ) : null}
        {badge ? (
          <EstadoChip tono={badgeTono ?? 'neutral'} tamano="xs" punto={false}>
            {badge}
          </EstadoChip>
        ) : null}
      </div>
      {conector ? (
        <span
          className={cn('mt-3 h-0.5 w-4 shrink-0', hecho ? 'bg-secondary/50' : 'bg-border')}
          aria-hidden="true"
        />
      ) : null}
    </div>
  );
}
