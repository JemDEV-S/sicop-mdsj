// Primitivas visuales compartidas del pipeline v2 (Guía Pipeline v2 §03, §04).
//
// Semántica de color única en todo el módulo (§04):
//   verde = hecho con fecha · azul = en curso normal · ámbar = requiere acción
//   del usuario · rojo = estancado real probado · gris = terminal/negativo.
// El estado se comunica con COLOR + TEXTO (nunca color solo), como el semáforo.

import { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Alerta, SeveridadAlerta } from '../dashboard/types';

// ─── Alerta v2: color + texto corto + tooltip con la evidencia ───────────

const SEVERIDAD_CLASE: Record<SeveridadAlerta, string> = {
  rojo: 'border-destructive/40 bg-destructive/10 text-destructive',
  ambar: 'border-accent/50 bg-accent/15 text-accent-foreground',
  gris: 'border-border bg-muted text-muted-foreground',
};

// Texto corto por tipo de alerta, en lenguaje llano (§04, sin jerga).
const ALERTA_TEXTO: Record<string, string> = {
  estancado_real: 'Estancado',
  puente_pendiente: 'Puente por confirmar',
  conflicto_puente: 'Conflicto de puente',
  cerrado_negativo: 'Cerrado',
  sin_consolidar: 'Sin consolidar',
  desfase_devengado: 'Sin devengado',
};

/** Borde izquierdo de la tarjeta según la alerta (o normal si no hay). */
export function bordeAlerta(alerta: Alerta | null | undefined): string {
  if (!alerta) return 'border-border';
  const color = {
    rojo: 'border-l-destructive',
    ambar: 'border-l-accent',
    gris: 'border-l-muted-foreground/40',
  }[alerta.severidad];
  return cn('border-l-4', color, 'border-y border-r-border');
}

interface BadgeAlertaProps {
  alerta: Alerta;
  className?: string;
}

/** Chip de alerta con su color, texto corto y la evidencia como tooltip. */
export function BadgeAlerta({ alerta, className }: BadgeAlertaProps) {
  const texto = ALERTA_TEXTO[alerta.tipo] ?? alerta.tipo;
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-[11px] font-medium',
        SEVERIDAD_CLASE[alerta.severidad],
        className,
      )}
      title={alerta.evidencia}
      aria-label={`${texto}: ${alerta.evidencia}`}
    >
      {texto}
    </span>
  );
}

// ─── Chip de identificador con copiar-al-clic (§03.1) ────────────────────

interface CopyChipProps {
  etiqueta?: string;
  valor: string;
  /** Tono muted cuando el ID es de la bolsa, no atribuido al pedido. */
  muted?: boolean;
  className?: string;
}

/** Muestra un identificador (N° pedido, O/S, SIAF) y lo copia al hacer clic. */
export function CopyChip({ etiqueta, valor, muted, className }: CopyChipProps) {
  const [copiado, setCopiado] = useState(false);

  const copiar = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    try {
      await navigator.clipboard.writeText(valor);
      setCopiado(true);
      window.setTimeout(() => setCopiado(false), 1200);
    } catch {
      // El portapapeles puede fallar sin HTTPS; se ignora silenciosamente.
    }
  };

  return (
    <button
      type="button"
      onClick={copiar}
      className={cn(
        'group inline-flex items-center gap-1 rounded border px-1.5 py-0.5',
        'font-mono text-[11px] transition-colors',
        muted
          ? 'border-border/60 bg-muted/40 text-muted-foreground'
          : 'border-border bg-card text-foreground hover:border-primary/50',
        className,
      )}
      title={copiado ? 'Copiado' : `Copiar ${etiqueta ?? valor}`}
      aria-label={`Copiar ${etiqueta ? etiqueta + ' ' : ''}${valor}`}
    >
      {etiqueta ? (
        <span className="text-muted-foreground/80">{etiqueta}</span>
      ) : null}
      <span>{valor}</span>
      {copiado ? (
        <Check className="h-3 w-3 text-secondary" aria-hidden="true" />
      ) : (
        <Copy
          className="h-3 w-3 text-muted-foreground/50 opacity-0 group-hover:opacity-100"
          aria-hidden="true"
        />
      )}
    </button>
  );
}
