export interface ObraCardResponse {
  codigo_unico: string;
  nombre_inversion: string | null;
  funcion: string | null;
  tipologia: string | null;
  modalidad: string | null;
  estado: string | null;
  etapa_f8: string | null;
  avance_fisico: number | null;
  avance_ejecucion: number | null;
  pim_anio_actual: number | null;
  dev_anio_actual: number | null;
  tiene_avan_fisico: string | null;
  latitud: number | null;
  longitud: number | null;
  semaforo: string;
}

export interface ObraListadoResponse {
  items: ObraCardResponse[];
  total: number;
  page: number;
  size: number;
}
