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
  categoria_gasto?: string;
}
