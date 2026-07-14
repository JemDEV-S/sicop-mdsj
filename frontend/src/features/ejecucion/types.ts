export interface EjecucionResumen {
  pia: string;
  pim: string;
  certificado: string;
  comprometido_anual: string;
  devengado: string;
  girado: string;
  metas: number; // Esto es COUNT en la DB, viene como número
  porcentaje_ejecucion: string | null;
}

export interface EjecucionPorFuncion {
  funcion_codigo: string;
  funcion_nombre: string;
  pim: string;
  certificado: string;
  devengado: string;
  girado: string;
}

export interface EjecucionPorFuente {
  fuente_codigo: string;
  fuente_nombre: string;
  pim: string;
  devengado: string;
}

export interface EjecucionMensual {
  mes_eje: number; // Entero en la DB
  pim: string;
  certificado: string;
  devengado: string;
  girado: string;
}

export interface EjecucionDetalleItem {
  funcion_codigo: string;
  funcion_nombre: string;
  sec_func: number;
  meta_codigo: string;
  meta_nombre: string;
  producto_proyecto: string;
  producto_proyecto_nombre?: string | null;
  categoria_gasto?: string | null;
  categoria_gasto_nombre?: string | null;
  pim: string;
  certificado: string;
  devengado: string;
  girado: string;
  porcentaje_ejecucion: string | null;
}

export interface EjecucionDetalleResponse {
  items: EjecucionDetalleItem[];
  total: number;
  page: number;
  size: number;
}

export interface EjecucionDetalleFiltros {
  ano?: number;
  funcion?: string;
  fuente?: string;
  rubro?: string;
  generica?: string;
  categoria_gasto?: string;
}

// Drill-down: Funcion -> Producto/Proyecto -> Meta
export type NivelJerarquia = 'funcion' | 'producto' | 'meta';

export interface JerarquiaNodo {
  codigo: string;
  nombre: string;
  tipo?: string | null;
  pim: string;
  pia: string;
  certificado: string;
  devengado: string;
  girado: string;
  porcentaje_ejecucion: string | null;
  participacion_pim: string | null;
  tiene_hijos: boolean;
}

export interface JerarquiaParams {
  ano?: number;
  nivel: NivelJerarquia;
  padre_funcion?: string;
  padre_producto?: string;
  filtro_rubro?: string;
  filtro_generica?: string;
}

// Agregados globales para las cards del dashboard
export interface EjecucionPorRubro {
  rubro_codigo: string;
  rubro_nombre: string;
  pim: string;
  devengado: string;
  participacion_pim: string | null;
}

export interface EjecucionPorGenerica {
  generica_codigo: string;
  generica_nombre: string;
  pim: string;
  devengado: string;
  participacion_pim: string | null;
}

// Serie mensual con acumulado (respeta el hallazgo de granularidad)
export interface EjecucionMensualAcumulado {
  mes_eje: number;
  pim: string;
  certificado_mes: string;
  devengado_mes: string;
  girado_mes: string;
  certificado_acumulado: string;
  devengado_acumulado: string;
  girado_acumulado: string;
}

// Desglose N:N de una meta (rubro x generica)
export interface MetaDesgloseCabecera {
  meta_codigo: string;
  meta_nombre: string;
  funcion_codigo: string;
  funcion_nombre: string;
  producto_proyecto: string;
  producto_proyecto_nombre: string | null;
  categoria_gasto: string | null;
  categoria_gasto_nombre: string | null;
  pim: string;
  pia: string;
  certificado: string;
  devengado: string;
  girado: string;
  porcentaje_ejecucion: number | null;
}

export interface MetaDesgloseFila {
  rubro_codigo: string;
  rubro_nombre: string;
  generica_codigo: string;
  generica_nombre: string;
  pim: string;
  certificado: string;
  devengado: string;
  girado: string;
  porcentaje_ejecucion: string | null;
}

export interface MetaDesgloseResponse {
  cabecera: MetaDesgloseCabecera | null;
  filas: MetaDesgloseFila[];
}
