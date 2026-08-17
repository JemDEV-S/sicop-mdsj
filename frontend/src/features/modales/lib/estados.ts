// Mapeo del estado SIAF (texto del SIGA) a tono UI y a las fases alcanzadas.
// Compartido por el modal de orden y el de expediente. No inventa montos por
// fase; solo marca qué fases están alcanzadas según el estado textual.

import type { Tono } from '@/features/panel/ui/primitivas';

/** Fases del expediente SIAF en orden. */
export const FASES_SIAF = ['Certificado', 'Comprometido', 'Devengado', 'Girado', 'Pagado'] as const;
export type FaseSiaf = (typeof FASES_SIAF)[number];

/** Índice (0-based) de la última fase alcanzada según el estado textual. */
function ultimaFaseAlcanzada(estado: string | null): number {
  const e = (estado ?? '').toLowerCase();
  if (e.includes('pag')) return 4;
  if (e.includes('gir')) return 3;
  if (e.includes('deveng')) return 2;
  if (e.includes('comprom')) return 1;
  if (e.includes('cert')) return 0;
  // Sin estado reconocible: nada confirmado.
  return -1;
}

export function fasesDeEstadoSiaf(estado: string | null): { label: FaseSiaf; hecho: boolean }[] {
  const hasta = ultimaFaseAlcanzada(estado);
  return FASES_SIAF.map((label, i) => ({ label, hecho: i <= hasta }));
}

export function tonoEstadoSiaf(estado: string | null): Tono {
  const hasta = ultimaFaseAlcanzada(estado);
  if (hasta >= 2) return 'ok'; // devengado o más: confirmado
  if (hasta >= 0) return 'primary'; // certificado/comprometido: en curso
  return 'neutral'; // sin información
}
