// Derivaciones puras del reporte para la vista "Análisis por meta" v2.
//
// El backend ya aplicó el alcance por CC (RN-06): `data.metas` son las metas
// visibles del usuario. Aquí solo se filtra por la meta elegida y por
// naturaleza del gasto (producto/proyecto), y se agregan los KPI del ámbito.
// Sin React, sin store: funciones testeables.

import type {
  CategoriaMeta,
  MetaReporte,
  OrdenReporte,
  PecosaReporte,
  ReporteResponse,
} from '../../reporte-types';

/**
 * Filtro de naturaleza del gasto de la barra de ámbito. Es la primera bandera
 * de la vista: siempre está activa y condiciona qué metas son buscables/
 * elegibles. 'todas' no filtra por naturaleza. Por defecto arranca en 'proyecto'.
 */
export type FiltroCategoria = 'todas' | CategoriaMeta;

/** Naturaleza del gasto por defecto al abrir la vista: proyectos de inversión. */
export const CATEGORIA_DEFECTO: FiltroCategoria = 'proyecto';

/** Metas visibles de una naturaleza. 'todas' devuelve el universo. Base de buscador y chips. */
export function metasDeCategoria(
  data: ReporteResponse,
  categoria: FiltroCategoria,
): MetaReporte[] {
  if (categoria === 'todas') return data.metas;
  return data.metas.filter((m) => m.categoria === categoria);
}

/**
 * Identificador de meta que ve el funcionario: el SEC_FUNC (llave de SIGA que
 * la muni usa como número de meta). NO se usa `meta` (el correlativo SIGA
 * "0004") porque no coincide con el SEC_FUNC y genera confusión — el SEC_FUNC
 * es el número correcto. El nombre de la meta se muestra aparte.
 */
export function idMeta(m: { sec_func: number }): string {
  return String(m.sec_func);
}

/** Órden con su meta de origen arrastrada (para las pestañas O/C, O/S). */
export interface OrdenConMeta extends OrdenReporte {
  sec_func: number;
  meta: string | null;
  nombre_meta: string | null;
}

/** PECOSA con su meta de origen arrastrada (para la pestaña PECOSAS). */
export interface PecosaConMeta extends PecosaReporte {
  sec_func: number;
  meta: string | null;
  nombre_meta: string | null;
}

/** Totales presupuestales del ámbito (MEF, 1× por meta — nunca por pedido). */
export interface AgregadoAmbito {
  n_metas: number;
  pim: number;
  comprometido: number;
  devengado: number;
  /** Devengado / PIM en %. null si no hay PIM. */
  pct: number | null;
  n_pedidos: number;
  monto_siga: number;
  n_ordenes: number;
  n_pecosas: number;
}

/**
 * Metas del ámbito. La naturaleza del gasto (categoría) SIEMPRE filtra — es la
 * primera bandera y manda. Si además hay una meta elegida, el ámbito se refina
 * a esa meta (que ya es de la categoría activa; ver `metaEsDeCategoria`).
 */
export function metasDelAmbito(
  data: ReporteResponse,
  metaSel: number | null,
  categoria: FiltroCategoria,
): MetaReporte[] {
  const deCategoria = metasDeCategoria(data, categoria);
  if (metaSel == null) return deCategoria;
  return deCategoria.filter((m) => m.sec_func === metaSel);
}

/** True si la meta elegida pertenece a la naturaleza activa (para auto-limpiar). */
export function metaEsDeCategoria(
  data: ReporteResponse,
  metaSel: number | null,
  categoria: FiltroCategoria,
): boolean {
  if (metaSel == null || categoria === 'todas') return true;
  const m = data.metas.find((x) => x.sec_func === metaSel);
  return m != null && m.categoria === categoria;
}

/** La meta seleccionada, o null si el ámbito es "todo lo visible". */
export function metaSeleccionada(
  data: ReporteResponse,
  metaSel: number | null,
): MetaReporte | null {
  if (metaSel == null) return null;
  return data.metas.find((m) => m.sec_func === metaSel) ?? null;
}

/** Agrega los KPI del ámbito. El dinero MEF se suma 1× por meta (anti-inflado §7). */
export function agregarAmbito(metas: MetaReporte[]): AgregadoAmbito {
  let pim = 0;
  let comprometido = 0;
  let devengado = 0;
  let n_pedidos = 0;
  let monto_siga = 0;
  let n_ordenes = 0;
  let n_pecosas = 0;
  for (const m of metas) {
    pim += m.mef.pim;
    comprometido += m.mef.comprometido;
    devengado += m.mef.devengado;
    n_pedidos += m.n_pedidos;
    monto_siga += m.monto_siga;
    n_ordenes += m.ordenes.length;
    n_pecosas += m.pecosas.length;
  }
  const pct = pim > 0 ? Math.round((devengado / pim) * 10000) / 100 : null;
  return {
    n_metas: metas.length,
    pim,
    comprometido,
    devengado,
    pct,
    n_pedidos,
    monto_siga,
    n_ordenes,
    n_pecosas,
  };
}

/** Todas las órdenes del ámbito, con su meta arrastrada (para O/C y O/S). */
export function ordenesDelAmbito(metas: MetaReporte[]): OrdenConMeta[] {
  const out: OrdenConMeta[] = [];
  for (const m of metas) {
    for (const o of m.ordenes) {
      out.push({ ...o, sec_func: m.sec_func, meta: m.meta, nombre_meta: m.nombre_meta });
    }
  }
  return out;
}

/** Todas las PECOSAS del ámbito, con su meta arrastrada. */
export function pecosasDelAmbito(metas: MetaReporte[]): PecosaConMeta[] {
  const out: PecosaConMeta[] = [];
  for (const m of metas) {
    for (const p of m.pecosas) {
      out.push({ ...p, sec_func: m.sec_func, meta: m.meta, nombre_meta: m.nombre_meta });
    }
  }
  return out;
}

/** Órdenes de compra (bienes, 'B') = O/C. */
export function esOC(o: OrdenReporte): boolean {
  return o.tipo_bien !== 'S';
}

/** Órdenes de servicio ('S') = O/S. */
export function esOS(o: OrdenReporte): boolean {
  return o.tipo_bien === 'S';
}

/** Recepción de una orden a texto legible (flag_recep del SIGA). */
export function labelRecepcion(flag: string | null): string | null {
  if (flag === '3') return 'Recepción completa';
  if (flag === '2') return 'Recepción parcial';
  if (flag === '1') return 'Sin recepción';
  return null;
}

/**
 * Índice nº de orden → contexto de un pedido que la declara (tipo/nro/tipoPed),
 * para poder abrir el modal de orden (que requiere un pedido de origen). Se
 * arma de los propios pedidos del reporte: cada uno trae `identificadores.orden`
 * como "O/S 232" / "O/C 97". Si un nº de orden no lo declara ningún pedido
 * visible, no se puede abrir su modal — la fila queda informativa (no se inventa
 * un pedido de origen).
 */
export interface RefPedidoOrden {
  nroPedido: number;
  tipoBien: string;
  tipoPedido: string;
}

const RE_NRO_ORDEN = /(\d{1,7})/;

export function indicePedidoPorOrden(
  data: ReporteResponse,
): Map<number, RefPedidoOrden> {
  const idx = new Map<number, RefPedidoOrden>();
  for (const meta of data.metas) {
    for (const celda of meta.celdas) {
      for (const p of celda.pedidos) {
        const txt = p.identificadores?.orden ?? null;
        if (!txt) continue;
        const m = RE_NRO_ORDEN.exec(txt);
        if (!m) continue;
        const nro = Number(m[1]);
        if (!idx.has(nro)) {
          idx.set(nro, {
            nroPedido: p.nro_pedido,
            tipoBien: p.tipo_bien,
            tipoPedido: p.tipo_pedido ?? '',
          });
        }
      }
    }
  }
  return idx;
}
