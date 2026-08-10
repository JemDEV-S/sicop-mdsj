// Semáforo temporal (color + TEXTO, nunca color solo — sistema de diseño §3).
// Compara el avance real de devengado contra el esperado al mes de corte.
// El color sale del backend (`semaforo_service.color_temporal`); aquí solo se
// traduce a token institucional y a una etiqueta legible para el funcionario.

import { cn } from '@/lib/utils';
import type { SemaforoCtx } from '../../reporte-types';

type Color = 'verde' | 'amarillo' | 'rojo' | 'desconocido';

const ESTILO: Record<Color, string> = {
  verde: 'bg-semaforo-ok/15 text-secondary-foreground ring-1 ring-inset ring-semaforo-ok/40',
  amarillo: 'bg-semaforo-alerta/20 text-accent-foreground ring-1 ring-inset ring-semaforo-alerta/50',
  rojo: 'bg-semaforo-critico/15 text-destructive ring-1 ring-inset ring-semaforo-critico/40',
  desconocido: 'bg-muted text-muted-foreground ring-1 ring-inset ring-border',
};

const ETIQUETA: Record<Color, string> = {
  verde: 'A tiempo',
  amarillo: 'En riesgo',
  rojo: 'Atrasado',
  desconocido: 'Sin dato',
};

const PUNTO: Record<Color, string> = {
  verde: 'bg-semaforo-ok',
  amarillo: 'bg-semaforo-alerta',
  rojo: 'bg-semaforo-critico',
  desconocido: 'bg-muted-foreground',
};

function normalizar(color: string): Color {
  return color === 'verde' || color === 'amarillo' || color === 'rojo'
    ? color
    : 'desconocido';
}

/** Frase explicativa del rezago para el `title` (contexto sin abrir nada). */
function detalle(ctx: SemaforoCtx | null, color: Color): string {
  if (!ctx || ctx.real == null) {
    return 'La meta no tiene PIM registrado o aún no hay ejecución para calcular el avance.';
  }
  const real = ctx.real.toFixed(1);
  const esp = ctx.esperado.toFixed(1);
  const base = `Devengado ${real}% del PIM · esperado ${esp}% al mes ${ctx.mes_corte}.`;
  if (color === 'verde') return `${base} La meta va al día o adelantada.`;
  const rezago = ctx.rezago != null ? Math.abs(ctx.rezago).toFixed(1) : '?';
  return `${base} Rezago de ${rezago} puntos respecto de lo esperado.`;
}

export function SemaforoChip({
  color,
  ctx,
  tamano = 'sm',
}: {
  color: string;
  ctx: SemaforoCtx | null;
  tamano?: 'sm' | 'xs';
}) {
  const c = normalizar(color);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        tamano === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-1.5 py-0.5 text-[10px]',
        ESTILO[c],
      )}
      title={detalle(ctx, c)}
    >
      <span className={cn('inline-block h-2 w-2 shrink-0 rounded-full', PUNTO[c])} aria-hidden="true" />
      {ETIQUETA[c]}
    </span>
  );
}
