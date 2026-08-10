// Aplanado de la respuesta jerárquica del reporte a filas-pedido planas.
// Función pura y testeable: no toca React ni el store.

import type { ReporteResponse } from '../../reporte-types';
import type { FilaPedido } from './tipos';

/**
 * Convierte `ReporteResponse` (Meta → Clasificador → Pedido) en una lista plana
 * de `FilaPedido`, arrastrando a cada fila su contexto de meta y clasificador.
 * No pierde ni duplica pedidos: hay exactamente una fila por pedido.
 */
export function aplanarPedidos(data: ReporteResponse): FilaPedido[] {
  const filas: FilaPedido[] = [];
  for (const meta of data.metas) {
    for (const celda of meta.celdas) {
      for (const p of celda.pedidos) {
        filas.push({
          nro_pedido: p.nro_pedido,
          tipo_bien: p.tipo_bien,
          tipo_pedido: p.tipo_pedido,
          orden: p.identificadores?.orden ?? null,
          exp_siaf: p.identificadores?.exp_siaf ?? null,

          sec_func: meta.sec_func,
          nombre_meta: meta.nombre_meta,
          centro_costo: p.centro_costo,
          clasificador: celda.clasificador,
          clasificador_nombre: celda.clasificador_nombre,

          motivo: p.motivo,
          etapa: p.etapa,
          etapa_label: p.etapa_label,
          macrofase: p.macrofase,
          dias_en_etapa: p.dias_en_etapa,
          estancado: p.estancado,
          fechas: p.fechas,
          n_candidatos_ccmn: p.n_candidatos_ccmn,
          tiene_orden: p.tiene_orden,

          monto_siga: p.monto_siga,
          comprometido_pedido: p.comprometido_pedido,
          devengado_estimado: p.devengado_estimado,
          atribucion: p.atribucion,
        });
      }
    }
  }
  return filas;
}
