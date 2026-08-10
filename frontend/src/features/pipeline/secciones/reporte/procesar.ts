// Motor de la tabla dinámica: filtrar → agrupar → totalizar → resumir.
// Todo funciones puras (sin React), para poder testearlas y memoizarlas.

import type { Macrofase } from '@/features/dashboard/types';
import { LABEL_MACROFASE, ORDEN_MACROFASE } from './constantes';
import type {
  CampoAgrupacion,
  CampoOrden,
  CentroCostoLabelFn,
  DireccionOrden,
  FilaPedido,
  FiltrosReporte,
  GrupoPedidos,
  ResumenMacrofase,
  Totales,
} from './tipos';

// ─── Filtrado ────────────────────────────────────────────────────────────

function textoBuscable(f: FilaPedido): string {
  return [
    f.nro_pedido,
    f.orden ?? '',
    f.exp_siaf ?? '',
    f.motivo ?? '',
    f.clasificador,
    f.clasificador_nombre ?? '',
    f.sec_func,
    f.nombre_meta ?? '',
    f.centro_costo ?? '',
    f.etapa_label,
  ]
    .join(' ')
    .toLowerCase();
}

/** Aplica todos los filtros a las filas. Función pura. */
export function filtrar(filas: FilaPedido[], f: FiltrosReporte): FilaPedido[] {
  const q = f.busqueda.trim().toLowerCase();
  const setCC = new Set(f.centrosCosto);
  const setMF = new Set(f.macrofases);
  const setMeta = new Set(f.metas);

  return filas.filter((fila) => {
    if (setCC.size && (!fila.centro_costo || !setCC.has(fila.centro_costo))) return false;
    if (setMF.size && !setMF.has(fila.macrofase)) return false;
    if (setMeta.size && !setMeta.has(fila.sec_func)) return false;
    if (f.soloEstancados && !fila.estancado) return false;
    if (f.soloConOrden && !fila.tiene_orden) return false;
    if (f.soloSinOrden && fila.tiene_orden) return false;
    if (f.montoMin != null && fila.monto_siga < f.montoMin) return false;
    if (f.montoMax != null && fila.monto_siga > f.montoMax) return false;
    if (f.diasMin != null && (fila.dias_en_etapa ?? 0) < f.diasMin) return false;
    if (q && !textoBuscable(fila).includes(q)) return false;
    return true;
  });
}

// ─── Totales ─────────────────────────────────────────────────────────────

/** Suma los totales de un conjunto de filas. `monto_siga` es el único duro. */
export function totalizar(filas: FilaPedido[]): Totales {
  const t: Totales = {
    n_pedidos: 0,
    monto_siga: 0,
    comprometido_estimado: 0,
    devengado_estimado: 0,
    n_estancados: 0,
    monto_estancado: 0,
  };
  for (const f of filas) {
    t.n_pedidos += 1;
    t.monto_siga += f.monto_siga;
    t.comprometido_estimado += f.comprometido_pedido ?? 0;
    t.devengado_estimado += f.devengado_estimado ?? 0;
    if (f.estancado) {
      t.n_estancados += 1;
      t.monto_estancado += f.monto_siga;
    }
  }
  return t;
}

// ─── Orden ───────────────────────────────────────────────────────────────

function comparar(a: FilaPedido, b: FilaPedido, campo: CampoOrden): number {
  switch (campo) {
    case 'monto_siga':
      return a.monto_siga - b.monto_siga;
    case 'dias_en_etapa':
      return (a.dias_en_etapa ?? 0) - (b.dias_en_etapa ?? 0);
    case 'devengado_estimado':
      return (a.devengado_estimado ?? 0) - (b.devengado_estimado ?? 0);
    case 'nro_pedido':
      return a.nro_pedido - b.nro_pedido;
    case 'macrofase':
      return ORDEN_MACROFASE[a.macrofase] - ORDEN_MACROFASE[b.macrofase];
  }
}

export function ordenar(
  filas: FilaPedido[],
  campo: CampoOrden,
  dir: DireccionOrden,
): FilaPedido[] {
  const factor = dir === 'asc' ? 1 : -1;
  return [...filas].sort((a, b) => comparar(a, b, campo) * factor);
}

// ─── Agrupación ──────────────────────────────────────────────────────────

/** Clave de agrupación cruda (sin etiqueta legible) de una fila. */
function claveGrupo(f: FilaPedido, campo: CampoAgrupacion): string {
  switch (campo) {
    case 'macrofase':
      return f.macrofase;
    case 'centro_costo':
      return f.centro_costo ?? '(sin centro)';
    case 'meta':
      return String(f.sec_func);
    case 'estado':
      return f.estancado ? 'estancado' : 'en_curso';
    case 'ninguno':
      return '__todos__';
  }
}

/** Peso de orden de los grupos (macrofase por avance; el resto por monto desc). */
function pesoGrupo(clave: string, campo: CampoAgrupacion, monto: number): number {
  if (campo === 'macrofase') return ORDEN_MACROFASE[clave as Macrofase] ?? 99;
  if (campo === 'estado') return clave === 'estancado' ? 0 : 1;
  // CC / meta / ninguno: los de mayor monto primero (negativo para asc-sort).
  return -monto;
}

/**
 * Agrupa las filas por el campo dado, ordena dentro de cada grupo, calcula
 * subtotales y ordena los grupos. `ccLabel` traduce código de CC → etiqueta.
 */
export function agrupar(
  filas: FilaPedido[],
  campo: CampoAgrupacion,
  orden: CampoOrden,
  dir: DireccionOrden,
  ccLabel: CentroCostoLabelFn,
): GrupoPedidos[] {
  const buckets = new Map<string, FilaPedido[]>();
  for (const f of filas) {
    const k = claveGrupo(f, campo);
    const arr = buckets.get(k);
    if (arr) arr.push(f);
    else buckets.set(k, [f]);
  }

  const grupos: GrupoPedidos[] = [];
  for (const [clave, arr] of buckets) {
    const muestra = arr[0];
    if (!muestra) continue; // inalcanzable: un bucket nace con ≥1 fila
    grupos.push({
      clave,
      etiqueta: etiquetaGrupo(clave, campo, muestra, ccLabel),
      sublabel: sublabelGrupo(clave, campo, muestra),
      filas: ordenar(arr, orden, dir),
      totales: totalizar(arr),
    });
  }

  grupos.sort(
    (a, b) =>
      pesoGrupo(a.clave, campo, a.totales.monto_siga) -
      pesoGrupo(b.clave, campo, b.totales.monto_siga),
  );
  return grupos;
}

function etiquetaGrupo(
  clave: string,
  campo: CampoAgrupacion,
  muestra: FilaPedido,
  ccLabel: CentroCostoLabelFn,
): string {
  switch (campo) {
    case 'macrofase':
      return LABEL_MACROFASE[clave as Macrofase] ?? clave;
    case 'centro_costo':
      return clave === '(sin centro)' ? 'Sin centro de costo' : ccLabel(clave).nombre;
    case 'meta':
      return `Meta ${clave}${muestra.nombre_meta ? ` · ${muestra.nombre_meta}` : ''}`;
    case 'estado':
      return clave === 'estancado' ? 'Pedidos estancados' : 'Pedidos en curso';
    case 'ninguno':
      return 'Todos los pedidos';
  }
}

function sublabelGrupo(
  clave: string,
  campo: CampoAgrupacion,
  muestra: FilaPedido,
): string | null {
  if (campo === 'centro_costo' && clave !== '(sin centro)') return clave;
  if (campo === 'meta') return muestra.centro_costo;
  return null;
}

// ─── Resumen por macrofase (barra superior) ──────────────────────────────

/** Total por cada macrofase presente, en orden de avance. */
export function resumenPorMacrofase(filas: FilaPedido[]): ResumenMacrofase[] {
  const acc = new Map<Macrofase, ResumenMacrofase>();
  for (const f of filas) {
    let r = acc.get(f.macrofase);
    if (!r) {
      r = {
        macrofase: f.macrofase,
        n_pedidos: 0,
        monto_siga: 0,
        n_estancados: 0,
        monto_estancado: 0,
      };
      acc.set(f.macrofase, r);
    }
    r.n_pedidos += 1;
    r.monto_siga += f.monto_siga;
    if (f.estancado) {
      r.n_estancados += 1;
      r.monto_estancado += f.monto_siga;
    }
  }
  return [...acc.values()].sort(
    (a, b) => ORDEN_MACROFASE[a.macrofase] - ORDEN_MACROFASE[b.macrofase],
  );
}
