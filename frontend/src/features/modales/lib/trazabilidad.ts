// Deriva los carriles de trazabilidad por macrofase a partir del timeline real
// del pedido (PedidoDetalle.timeline). Espejo de la lógica del modal de la
// plantilla Panel Interno v2: agrupa los 16 hitos por macrofase, calcula el
// progreso de cada carril y el estado de cada hito (directo/vía/grupo/sin dato).

import type { EstadoEtapa, TimelineEvento } from '@/features/pipeline/types';
import type { Macrofase } from '@/features/dashboard/types';
import { MACROFASES } from '@/features/pipeline/secciones/reporte/constantes';

/** Estados en que la etapa cuenta como alcanzada por ESTE pedido. */
const ALCANZADO: ReadonlySet<EstadoEtapa> = new Set<EstadoEtapa>(['directo', 'via_ccmn', 'manual']);

/** Presentación del chip de un hito según su estado (colores de la plantilla). */
export type TonoHito = 'directo' | 'via' | 'grupo' | 'sin';

export function tonoDeEstado(estado: EstadoEtapa, alcanzado: boolean): TonoHito {
  if (!alcanzado) return 'sin';
  if (estado === 'grupo') return 'grupo';
  if (estado === 'via_ccmn' || estado === 'manual') return 'via';
  return 'directo';
}

export interface HitoCarril {
  numero: number;
  label: string;
  doc: string;
  tono: TonoHito;
  /** Marca dentro del cuadrito: ✓ para cumplido, ≡ grupo, · vía, o el n° si sin dato. */
  marca: string;
  /** Etiqueta pequeña opcional (p. ej. "PAAC", "grupo"). */
  tag: string | null;
}

export interface Carril {
  macrofase: Macrofase;
  label: string;
  total: number;
  hechos: number;
  completa: boolean;
  iniciada: boolean;
  progreso: string;
  primerCarril: boolean;
  ultimoCarril: boolean;
  hitos: HitoCarril[];
}

function docDeHito(ev: TimelineEvento, alcanzado: boolean): string {
  if (!alcanzado) return 'sin dato';
  const d = ev.documentos[0];
  if (d) {
    return `${d.etiqueta} ${d.valor}`;
  }
  if (ev.fecha) {
    return new Date(ev.fecha).toLocaleDateString('es-PE', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }
  return ev.detalle ?? '—';
}

function marcaDeHito(tono: TonoHito, numero: number): string {
  if (tono === 'directo' || tono === 'via') return '✓';
  if (tono === 'grupo') return '≡';
  return String(numero);
}

function tagDeHito(tono: TonoHito): string | null {
  if (tono === 'grupo') return 'grupo';
  if (tono === 'via') return 'CCMN';
  return null;
}

/**
 * Construye los carriles. En modo resumen, cada carril muestra a lo sumo los
 * dos últimos hitos alcanzados (o el primero si el carril no ha iniciado);
 * en detalle, todos los hitos de la macrofase.
 */
export function construirCarriles(timeline: TimelineEvento[], resumen: boolean): Carril[] {
  return MACROFASES.map((mf, i) => {
    const eventos = timeline
      .filter((e) => e.macrofase === mf.macrofase)
      .sort((a, b) => a.etapa_numero - b.etapa_numero);
    const alcanzados = eventos.filter((e) => ALCANZADO.has(e.estado) || e.estado === 'grupo');
    const hechos = eventos.filter((e) => ALCANZADO.has(e.estado)).length;
    const total = eventos.length;
    const completa = total > 0 && hechos === total;
    const iniciada = alcanzados.length > 0;

    const mostrar = resumen
      ? iniciada
        ? alcanzados.slice(-2)
        : eventos.slice(0, 1)
      : eventos;

    return {
      macrofase: mf.macrofase,
      label: mf.label,
      total,
      hechos,
      completa,
      iniciada,
      progreso: `${hechos}/${total}${completa ? ' · completa' : iniciada ? ' · en curso' : ''}`,
      primerCarril: i === 0,
      ultimoCarril: i === MACROFASES.length - 1,
      hitos: mostrar.map((ev) => {
        const alcanzado = ALCANZADO.has(ev.estado) || ev.estado === 'grupo';
        const tono = tonoDeEstado(ev.estado, alcanzado);
        return {
          numero: ev.etapa_numero,
          label: ev.etapa_label,
          doc: docDeHito(ev, alcanzado),
          tono,
          marca: marcaDeHito(tono, ev.etapa_numero),
          tag: tagDeHito(tono),
        };
      }),
    };
  });
}
