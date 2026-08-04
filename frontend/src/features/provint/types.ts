// Tipos del Directorio interno de proveedores + contratos (HU-19/HU-20 · T-53).
//
// Espejo de `backend/app/schemas/proveedores.py`, verificado contra las
// respuestas reales de /interno/proveedores(/{ruc}(/ordenes)) y
// /interno/contratos(/alertas/contratos-por-vencer).
//
// REGLA DE ORO (consolidación): orden ≠ contrato.
//   - `monto_acumulado` del proveedor = SUMA facturada en sus ÓRDENES (ejecución
//     real).
//   - `valor_soles` del contrato = compromiso marco pactado (puede no ejecutarse).
//   No sumarlos ni presentarlos como equivalentes.

export interface ProveedorInterno {
  ruc: string | null;
  nombre: string | null;
  tipo_persona: string | null;
  giro: string | null;
  flag_mype: string | null;
  flag_rnp: string | null;
  flag_consorcio: string | null;
  /** SUMA facturada en sus órdenes del año (ejecución real). NO el valor de contratos. */
  monto_acumulado: number | null;
  nro_ordenes: number;
  // Solo en el interno (incluir_contacto=true):
  email: string | null;
  telefonos: string | null;
  direccion: string | null;
  nro_rnp: string | null;
}

export interface ProveedoresListado {
  items: ProveedorInterno[];
  total: number;
  page: number;
  size: number;
}

export interface OrdenProveedor {
  ano_eje: number;
  nro_orden: number;
  tipo_bien: string;
  exp_siaf: string | null;
  estado: string | null;
  estado_siaf: string | null;
  total_fact_soles: number | null;
  concepto: string | null;
  fecha_orden: string | null;
}

export interface ContratoItem {
  ano_eje: number;
  sec_ejec: string;
  tipo_contrato: string | null;
  nro_contrato: number;
  sec_contrato: number;
  tipo_bien: string | null;
  proveedor_ruc: string | null;
  proveedor_nombre: string | null;
  fecha_inicial: string | null;
  fecha_final: string | null;
  fecha_cese: string | null;
  /** Valor del CONTRATO (compromiso marco). NO es lo ejecutado. */
  valor_soles: number | null;
  objeto: string | null;
  tipo_compra: string | null;
  modal_compra: string | null;
  id_proceso: string | null;
  id_contrato: string | null;
  nro_documento: string | null;
  estado: string | null;
  flag_snp: string | null;
}

export interface ContratosListado {
  items: ContratoItem[];
  total: number;
  page: number;
  size: number;
}

export interface ContratoPorVencer {
  ano_eje: number;
  nro_contrato: number;
  sec_contrato: number;
  tipo_contrato: string | null;
  tipo_bien: string | null;
  proveedor_ruc: string | null;
  proveedor_nombre: string | null;
  fecha_inicial: string | null;
  fecha_final: string | null;
  valor_soles: number | null;
  objeto: string | null;
  estado: string | null;
  dias_restantes: number | null;
}
