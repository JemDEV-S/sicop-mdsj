export interface ProveedorPublicoItem {
  ruc: string | null;
  nombre: string | null;
  tipo_persona: string | null;
  giro: string | null;
  flag_mype: string | null;
  flag_rnp: string | null;
  flag_consorcio: string | null;
  monto_acumulado: number | null;
  nro_ordenes: number;
}

export interface ProveedoresListado {
  items: ProveedorPublicoItem[];
  total: number;
  page: number;
  size: number;
}

export interface ProveedoresFiltros {
  q?: string;
  ano?: number;
}

export interface ProveedoresParams extends ProveedoresFiltros {
  page?: number;
  size?: number;
  sort?: string;
}
