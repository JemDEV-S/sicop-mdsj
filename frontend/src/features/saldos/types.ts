// Tipos del módulo de Saldos presupuestales (HU-15 · T-48).
//
// Espejo de `backend/app/schemas/saldos.py` (verificado contra la respuesta
// real del endpoint /interno/saldos). El modelo es DUAL por meta:
//
//   - Bloque SIGA operativo (`pim`, `certificado`, `comprometido_*`, ...): fases
//     PREVIAS al devengado. Aquí NO existe un "devengado" SIGA.
//   - Bloque MEF (`*_mef`): el número oficial que ve el ciudadano en el portal.
//     `devengado_mef` es el devengado REAL. `null` si la meta no cruza con el
//     snapshot MEF.
//
// El % de ejecución y el semáforo se calculan sobre `devengado_mef / pim_mef`,
// idéntico al portal público (Docs/consolidacion-backend-presupuestal.md §0.1).

/** Semáforo tal como lo emite el backend (semaforo_service.py). */
export type SemaforoSaldo = 'verde' | 'amarillo' | 'rojo' | 'desconocido';

/** Contexto del semáforo temporal: por qué el color es el que es. */
export interface SemaforoContexto {
  color: SemaforoSaldo;
  /** % que se esperaría al mes de corte del snapshot (lineal sobre 12). */
  esperado: number;
  /** % devengado real de la meta. `null` si no cruza con MEF. */
  real: number | null;
  /** esperado − real (pp). Negativo = adelantado. `null` si no cruza. */
  rezago: number | null;
  /** Mes de datos del snapshot (MAX mes_eje), base del esperado. */
  mes_corte: number;
}

export interface SaldoItem {
  sec_func: number;
  nombre_meta: string | null;
  act_proy: string | null;
  /** Cuántas líneas (clasificador × CC) agrega esta meta en el SIGA. */
  filas_clasificador: number;

  // ── Cadena de ejecución oficial (SIAF/MEF). `null` si no cruza. ──
  pim_mef: number | null;
  certificado_mef: number | null;
  comprometido_mef: number | null;
  devengado_mef: number | null;
  girado_mef: number | null;

  // ── Saldos entre fases (dónde está detenido el gasto). ──
  saldo_por_certificar: number | null; // PIM − Certificado
  saldo_por_comprometer_mef: number | null; // Certificado − Comprometido
  saldo_por_devengar: number | null; // Comprometido − Devengado
  saldo_por_ejecutar: number | null; // PIM − Devengado (clave)
  saldo_por_pagar: number | null; // Devengado − Girado
  saldo_disponible_mef: number | null; // alias legado de saldo_por_ejecutar
  devengado_no_girado_mef: number | null; // = saldo_por_pagar

  // ── % de avance por fase sobre el PIM oficial. ──
  porcentaje_certificado: number | null;
  porcentaje_comprometido: number | null;
  porcentaje_devengado: number | null;
  porcentaje_girado: number | null;

  // ── Referencia operativa SIGA (NO presupuestal). Solo contexto. ──
  pim_siga: number;
  certificado_siga: number;
  comprometido_siga: number;
  saldo_disponible_siga: number;
  reservado_pedido: number;

  // Semáforo temporal (avance real vs. esperado por mes de corte).
  semaforo: SemaforoSaldo;
  semaforo_ctx: SemaforoContexto | null;
}

export interface SaldosListadoResponse {
  items: SaldoItem[];
  total: number;
  page: number;
  size: number;
}

/** Un clasificador de gasto dentro de una fuente (hoja del árbol de detalle). */
export interface ClasificadorDetalle {
  codigo: string | null;
  nombre: string | null;
  pim: number;
  certificado: number;
  comprometido: number;
  saldo_disponible: number;
  /** PIM − comprometido: techo aún libre en esta línea. */
  saldo_por_comprometer: number;
  reservado_pedido: number;
  /** Nº de filas (clasificador × CC) que agrega esta línea. */
  filas: number;
  /** Línea del plan sin techo activo (PIM 0). Se muestra igual, marcada. */
  sin_pim: boolean;
}

/** Una fuente de financiamiento con sus clasificadores (nodo del árbol). */
export interface FuenteDetalle {
  fuente_codigo: string | null;
  fuente_nombre: string | null;
  pim: number;
  certificado: number;
  comprometido: number;
  saldo_disponible: number;
  n_clasificadores: number;
  clasificadores: ClasificadorDetalle[];
}

/** Detalle drill-down: cabecera oficial (SIAF) + árbol operativo SIGA. */
export interface SaldoDetalle {
  ano: number;
  /** Cadena de ejecución oficial de la meta, misma forma que la fila. */
  cabecera: SaldoItem;
  /** Árbol Fuente → Clasificadores (detalle operativo del gasto). */
  fuentes: FuenteDetalle[];
}

/** Filtros que el usuario puede aplicar sobre el listado de saldos. */
export interface FiltrosSaldos {
  /** Filtra por estado de semáforo (sobre devengado MEF real). */
  semaforo: SemaforoSaldo | null;
  /** Búsqueda por SEC_FUNC exacto (la meta que el funcionario reconoce). */
  secFunc: number | null;
}

export const FILTROS_SALDOS_VACIO: FiltrosSaldos = {
  semaforo: null,
  secFunc: null,
};
