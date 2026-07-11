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

export interface MontosObra {
  pia: number;
  pim: number;
  certificado: number;
  comprometido_anual: number;
  devengado: number;
  girado: number;
  porcentaje_devengado: number | null;
}

export interface ObraDetalleResponse {
  codigo_unico: string;
  nombre_inversion: string | null;
  tipo_inversion: string | null;
  marco: string | null;
  estado: string | null;
  situacion: string | null;
  funcion: string | null;
  programa: string | null;
  tipologia: string | null;
  modalidad: string | null;
  etapa_f8: string | null;
  tiene_f8: string | null;
  tiene_f9: string | null;
  tiene_f12b: string | null;
  expediente_tecnico: string | null;
  informe_cierre: string | null;

  avance_fisico: number | null;
  avance_ejecucion: number | null;
  tiene_avan_fisico: string | null;

  fec_ini_ejecucion: string | null;
  fec_fin_ejecucion: string | null;
  fec_ini_ejec_fisica: string | null;
  fec_fin_ejec_fisica: string | null;
  fecha_viabilidad: string | null;
  primer_devengado: string | null;
  ultimo_devengado: string | null;

  latitud: number | null;
  longitud: number | null;
  ubigeo: string | null;
  departamento: string | null;
  provincia: string | null;
  distrito: string | null;

  nombre_uei: string | null;
  nombre_uf: string | null;
  nombre_opmi: string | null;

  costo_actualizado: number | null;
  monto_viable: number | null;
  saldo_ejecutar: number | null;

  montos_ejecucion: MontosObra;
  semaforo: string;

  sincronizado_en: string | null;

  // DEUDA TÉCNICA T-39: Campos bloqueados por el backend.
  // Tipados como `?: never` intencionalmente para forzar un error de compilación
  // si alguien asume que el backend ya los manda. Actualizar este tipo y remover
  // el `never` cuando T-26 exponga contratistas y documentos.
  ruc?: never;
  razon_social?: never;
  monto_contratado?: never;
  documentos_descarga?: never;
}
