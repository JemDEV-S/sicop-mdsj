// Mini-timeline honesto por pedido: sólido = etapa cumplida; tramado = avance de
// bolsa compartida (§2.2); borde = etapa actual; gris = no alcanzada.

import type { EtapaCodigo, Macrofase } from '@/features/dashboard/types';
import { cn } from '@/lib/utils';
import { MACROFASES, ORDEN_MACROFASE } from './constantes';
import type { FilaPedido } from './tipos';

// Etapa (con fecha) que representa a cada macrofase en el rastro.
const ETAPA_DE_MACROFASE: Record<Macrofase, EtapaCodigo[]> = {
  solicitud: ['pedido_registrado', 'pedido_aprobado'],
  programacion: ['cuadro_necesidad', 'ccmn_em_cvr', 'cotizacion', 'cuadro_adquisicion'],
  certificacion: ['certificacion_ccp'],
  contratacion: ['orden_emitida', 'compromiso_siaf'],
  ejecucion: ['ejecucion', 'recepcion_kardex', 'despacho_pecosa'],
  cierre: ['devengado', 'cierre'],
};

function alcanzada(f: FilaPedido, m: Macrofase): boolean {
  return ETAPA_DE_MACROFASE[m].some((e) => f.fechas[e] != null);
}

function fechaDe(f: FilaPedido, m: Macrofase): string | null {
  for (const e of ETAPA_DE_MACROFASE[m]) if (f.fechas[e]) return f.fechas[e]!;
  return null;
}

function fmtFecha(iso: string): string {
  return new Date(iso).toLocaleDateString('es-PE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

/** Estado legible de una macrofase, para el lector de pantalla y el `title`. */
function estadoTexto(
  esActual: boolean,
  ok: boolean,
  esBolsa: boolean,
): string {
  if (esActual) return 'etapa actual';
  if (esBolsa) return 'avance de bolsa compartida';
  if (ok) return 'cumplida';
  return 'no alcanzada';
}

export function MiniTimeline({ fila }: { fila: FilaPedido }) {
  const actual = ORDEN_MACROFASE[fila.macrofase];
  const esGrupo = fila.n_candidatos_ccmn > 1;

  // Resumen textual del recorrido completo, para lectores de pantalla.
  const resumen = MACROFASES.map(({ macrofase, label }, i) => {
    const ok = alcanzada(fila, macrofase);
    const esActual = i === actual;
    const esBolsa = esGrupo && ok && !esActual && i > ORDEN_MACROFASE.solicitud;
    return `${label}: ${estadoTexto(esActual, ok, esBolsa)}`;
  }).join('. ');

  return (
    <div className="flex flex-col gap-0.5" role="img" aria-label={`Recorrido del pedido. ${resumen}.`}>
      <div className="flex gap-0.5" aria-hidden="true">
        {MACROFASES.map(({ macrofase, label }, i) => {
          const ok = alcanzada(fila, macrofase);
          const esActual = i === actual;
          const esBolsa = esGrupo && ok && !esActual && i > ORDEN_MACROFASE.solicitud;
          let clase = 'bg-muted-foreground/30';
          let estilo: React.CSSProperties | undefined;
          if (esActual) {
            clase = 'border-2 border-primary bg-card';
          } else if (esBolsa) {
            clase = '';
            estilo = {
              backgroundImage:
                'repeating-linear-gradient(45deg, var(--color-primary) 0 3px, var(--color-accent) 3px 6px)',
            };
          } else if (ok) {
            clase = 'bg-secondary';
          }
          const fecha = fechaDe(fila, macrofase);
          return (
            <span
              key={macrofase}
              className={cn('h-2.5 w-4 rounded-sm', clase)}
              style={estilo}
              title={`${label} — ${estadoTexto(esActual, ok, esBolsa)}${
                fecha ? ` · ${fmtFecha(fecha)}` : ''
              }`}
            />
          );
        })}
      </div>
      <div className="flex gap-0.5" aria-hidden="true">
        {MACROFASES.map(({ sigla, macrofase }) => (
          <span key={macrofase} className="w-4 text-center font-mono text-[8px] text-muted-foreground">
            {sigla}
          </span>
        ))}
      </div>
    </div>
  );
}
