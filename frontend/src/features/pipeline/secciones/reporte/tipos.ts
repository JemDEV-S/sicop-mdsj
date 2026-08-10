// Tipos de la tabla dinámica de pedidos (vista profesional del pipeline).
//
// La respuesta del backend es jerárquica (Meta → Clasificador → Pedido). Para
// una tabla dinámica trabajamos con PEDIDOS PLANOS: cada fila lleva su contexto
// (meta, clasificador, CC, dinero) ya resuelto, de modo que agrupar/filtrar/
// totalizar sea trivial y consistente. Ver `aplanar.ts` y `procesar.ts`.

import type { EtapaCodigo, Macrofase } from '@/features/dashboard/types';
import type { Atribucion } from '../../reporte-types';

/** Fila-pedido aplanada: la unidad atómica de la tabla dinámica. */
export interface FilaPedido {
  // Identidad y llaves de cruce (los 3 identificadores clave §00).
  nro_pedido: number;
  tipo_bien: string;
  tipo_pedido: string | null;
  orden: string | null;
  exp_siaf: number | null;

  // Contexto: dónde vive el pedido.
  sec_func: number;
  nombre_meta: string | null;
  centro_costo: string | null;
  clasificador: string;
  clasificador_nombre: string | null;

  // Estado en el pipeline.
  motivo: string | null;
  etapa: EtapaCodigo;
  etapa_label: string;
  macrofase: Macrofase;
  dias_en_etapa: number | null;
  estancado: boolean;
  fechas: Partial<Record<EtapaCodigo, string>>;
  n_candidatos_ccmn: number;
  tiene_orden: boolean;

  // Dinero. `monto_siga` es el ÚNICO sumable por pedido (dato duro).
  monto_siga: number;
  // Contexto MEF por pedido (informativo, NO sumable): reparto/atribución.
  comprometido_pedido: number | null;
  devengado_estimado: number | null;
  atribucion: Atribucion | null;
}

/** Campo por el que se puede agrupar la tabla (tabla dinámica). */
export type CampoAgrupacion = 'macrofase' | 'centro_costo' | 'meta' | 'estado' | 'ninguno';

/** Campo y dirección de orden dentro de cada grupo. */
export type CampoOrden =
  | 'monto_siga'
  | 'dias_en_etapa'
  | 'nro_pedido'
  | 'macrofase'
  | 'devengado_estimado';
export type DireccionOrden = 'asc' | 'desc';

/** Estado completo de filtros de la herramienta. */
export interface FiltrosReporte {
  busqueda: string;
  centrosCosto: string[]; // vacío = todos
  macrofases: Macrofase[]; // vacío = todas
  metas: number[]; // vacío = todas
  soloEstancados: boolean;
  soloConOrden: boolean;
  soloSinOrden: boolean;
  montoMin: number | null;
  montoMax: number | null;
  diasMin: number | null;
}

export const FILTROS_DEFAULT: FiltrosReporte = {
  busqueda: '',
  centrosCosto: [],
  macrofases: [],
  metas: [],
  soloEstancados: false,
  soloConOrden: false,
  soloSinOrden: false,
  montoMin: null,
  montoMax: null,
  diasMin: null,
};

/** Totales de un conjunto de filas (grupo o global). */
export interface Totales {
  n_pedidos: number;
  monto_siga: number;
  // MEF informativo: se acumula pero se rotula "no sumar / estimado".
  comprometido_estimado: number;
  devengado_estimado: number;
  n_estancados: number;
  monto_estancado: number;
}

/** Un grupo de la tabla dinámica: etiqueta + filas + subtotal. */
export interface GrupoPedidos {
  clave: string;
  etiqueta: string;
  sublabel: string | null;
  filas: FilaPedido[];
  totales: Totales;
}

/** Etiqueta legible de un centro de costo (código → nombre + sigla). */
export type CentroCostoLabelFn = (codigo: string) => { nombre: string; sigla: string };

/** Resumen por macrofase para la barra superior (chips clicables). */
export interface ResumenMacrofase {
  macrofase: Macrofase;
  n_pedidos: number;
  monto_siga: number;
  n_estancados: number;
  monto_estancado: number;
}
