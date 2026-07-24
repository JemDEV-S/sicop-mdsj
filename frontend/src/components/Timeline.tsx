import * as React from 'react';
import { CheckCircle2, Circle, CircleDashed, CircleDot, Copy } from 'lucide-react';
import { cn } from '@/lib/utils';
import { formatFecha } from '@/lib/formatters';

/**
 * Estado de una etapa del recorrido.
 *
 * La distinción crítica es `directo` vs `grupo`. SIGA no registra qué CCMN
 * corresponde a qué pedido, así que cuando varios pedidos comparten una bolsa
 * el avance observado puede ser de otro pedido. Antes eso se pintaba como un
 * verde creíble e indistinguible del avance real.
 *
 * Ref: Docs/diagnostico-2026-07-20/refactorizacion-pipeline-pedido-ccmn.md §8
 */
export type EstadoHito =
  | 'directo'
  | 'via_ccmn'
  | 'grupo'
  | 'manual'
  | 'sin_dato';

/** Identificador con el que se encuentra el documento en el sistema. */
export interface DocumentoHito {
  etiqueta: string;
  valor: string;
}

export interface HitoTimeline {
  key: string;
  titulo: string;
  detalle?: string | null;
  fecha?: string | null;
  estado: EstadoHito;
  numero?: number | null;
  /** Números que identifican el documento de esta etapa (CCP 182, OC 132…). */
  documentos?: DocumentoHito[];
}

interface TimelineProps {
  hitos: HitoTimeline[];
  className?: string;
}

/**
 * Presentación de cada estado.
 *
 * El estado NUNCA se comunica solo por color: cada uno lleva ícono propio y
 * una etiqueta en palabras. Es requisito del sistema de diseño (§3) y además
 * lo que hace que `grupo` sea imposible de confundir con avance real.
 *
 * `grupo` usa el amarillo institucional (`semaforo-alerta`), no el verde:
 * es una advertencia, no una confirmación.
 */
const PRESENTACION: Record<
  EstadoHito,
  {
    Icono: typeof CheckCircle2;
    etiqueta: string | null;
    ayuda: string | null;
    colorIcono: string;
    colorLinea: string;
    colorTitulo: string;
    colorEtiqueta: string;
  }
> = {
  directo: {
    Icono: CheckCircle2,
    etiqueta: null, // el caso normal no necesita etiqueta: no hay salvedad
    ayuda: null,
    colorIcono: 'text-secondary',
    colorLinea: 'bg-secondary/40',
    colorTitulo: 'text-foreground',
    colorEtiqueta: '',
  },
  via_ccmn: {
    Icono: CircleDot,
    etiqueta: 'fecha aproximada',
    ayuda:
      'Se llegó a esta etapa a través del cuadro de necesidades identificado para este pedido. La fecha puede diferir en algunos días.',
    colorIcono: 'text-primary',
    colorLinea: 'bg-primary/40',
    colorTitulo: 'text-foreground',
    colorEtiqueta: 'text-primary',
  },
  manual: {
    Icono: CircleDot,
    etiqueta: 'asociado manualmente',
    ayuda:
      'Un funcionario indicó qué cuadro de necesidades corresponde a este pedido. SIGA no registra esa correspondencia.',
    colorIcono: 'text-primary',
    colorLinea: 'bg-primary/40',
    colorTitulo: 'text-foreground',
    colorEtiqueta: 'text-primary',
  },
  grupo: {
    Icono: CircleDashed,
    etiqueta: 'avance del grupo',
    ayuda:
      'Este pedido comparte cuadro de necesidades con otros. Alguno de ellos llegó a esta etapa, pero SIGA no permite saber si fue este pedido.',
    colorIcono: 'text-semaforo-alerta',
    colorLinea: 'bg-semaforo-alerta/40',
    colorTitulo: 'text-foreground',
    colorEtiqueta: 'text-semaforo-alerta',
  },
  sin_dato: {
    Icono: Circle,
    etiqueta: 'pendiente',
    ayuda: null,
    colorIcono: 'text-muted-foreground',
    colorLinea: 'bg-border',
    colorTitulo: 'text-muted-foreground',
    colorEtiqueta: 'text-muted-foreground',
  },
};

// Estados en los que la etapa cuenta como alcanzada por ESTE pedido.
const ALCANZADOS: ReadonlySet<EstadoHito> = new Set<EstadoHito>([
  'directo',
  'via_ccmn',
  'manual',
]);

export function esAlcanzado(estado: EstadoHito): boolean {
  return ALCANZADOS.has(estado);
}

/**
 * Identificador de un documento, con copia al portapapeles.
 *
 * El número se copia solo (sin la etiqueta) porque es lo que se pega en el
 * buscador de SIGA. La confirmación es textual, no solo un cambio de ícono.
 */
function BotonCopiar({ documento }: { documento: DocumentoHito }) {
  const [copiado, setCopiado] = React.useState(false);

  React.useEffect(() => {
    if (!copiado) return;
    const t = setTimeout(() => setCopiado(false), 1600);
    return () => clearTimeout(t);
  }, [copiado]);

  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard?.writeText(documento.valor).then(
          () => setCopiado(true),
          () => undefined, // sin portapapeles: el número igual está visible
        );
      }}
      title={`Copiar ${documento.etiqueta} ${documento.valor}`}
      className="inline-flex items-center gap-1 rounded border border-border bg-muted/50 px-1.5 py-0.5 text-[11px] hover:bg-muted hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
    >
      <span className="text-muted-foreground">{documento.etiqueta}</span>
      <span className="font-mono tabular-nums">{documento.valor}</span>
      {copiado ? (
        <span className="text-secondary font-medium">copiado</span>
      ) : (
        <Copy
          className="w-2.5 h-2.5 text-muted-foreground/60"
          aria-hidden="true"
        />
      )}
    </button>
  );
}

// Componente vertical con línea conectora. Se declara aquí (nivel components/)
// porque sirve también al detalle de obra (T-51) y al cierre de meta.
export function Timeline({ hitos, className }: TimelineProps) {
  return (
    <ol className={cn('relative flex flex-col gap-4', className)}>
      {hitos.map((h, i) => {
        const esUltimo = i === hitos.length - 1;
        const p = PRESENTACION[h.estado] ?? PRESENTACION.sin_dato;
        const { Icono } = p;

        return (
          <li key={h.key} className="relative flex gap-3">
            {/* Línea conectora al siguiente hito */}
            {!esUltimo ? (
              <span
                aria-hidden="true"
                className={cn(
                  'absolute left-[9px] top-6 w-px h-full -bottom-2',
                  p.colorLinea,
                )}
              />
            ) : null}

            <span
              className="relative z-10 shrink-0 flex items-center justify-center w-5 h-5 mt-0.5"
              aria-hidden="true"
            >
              <Icono
                className={cn('w-5 h-5', p.colorIcono)}
                {...(h.estado === 'directo'
                  ? { fill: 'currentColor', fillOpacity: 0.15 }
                  : {})}
              />
            </span>

            <div className="min-w-0 flex-1 pb-1">
              <div className="flex items-baseline gap-2 flex-wrap">
                {h.numero != null ? (
                  <span className="text-[11px] font-mono text-muted-foreground tabular-nums">
                    [{h.numero}]
                  </span>
                ) : null}
                <p className={cn('text-sm font-medium', p.colorTitulo)}>
                  {h.titulo}
                </p>
                {h.fecha ? (
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {h.estado === 'via_ccmn' || h.estado === 'manual'
                      ? `aprox. ${formatFecha(h.fecha)}`
                      : formatFecha(h.fecha)}
                  </span>
                ) : null}
                {p.etiqueta ? (
                  <span
                    className={cn(
                      'text-xs font-medium',
                      p.colorEtiqueta,
                      h.estado === 'sin_dato' ? 'italic' : '',
                    )}
                    title={p.ayuda ?? undefined}
                  >
                    {p.etiqueta}
                  </span>
                ) : null}
              </div>

              {/* Los números con los que el funcionario encuentra el
                  documento en SIGA. Sin esto el recorrido dice "llegó a
                  certificación" pero no cuál. */}
              {h.documentos && h.documentos.length > 0 ? (
                <ul className="mt-1 flex flex-wrap gap-1.5">
                  {h.documentos.map((d) => (
                    <li key={`${d.etiqueta}-${d.valor}`}>
                      <BotonCopiar documento={d} />
                    </li>
                  ))}
                </ul>
              ) : null}

              {/* La explicación del estado va visible, no escondida en un
                  tooltip: el usuario objetivo no descubre tooltips (§4). */}
              {p.ayuda && h.estado === 'grupo' ? (
                <p className="mt-1 text-xs text-semaforo-alerta">{p.ayuda}</p>
              ) : null}

              {h.detalle ? (
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {h.detalle}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export default Timeline;
