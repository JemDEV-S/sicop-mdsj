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

export interface SaldoItem {
  sec_func: number;
  nombre_meta: string | null;
  act_proy: string | null;
  /** Cuántas filas (clasificador × CC) agrega esta meta en el SIGA. */
  filas_clasificador: number;

  // Bloque SIGA operativo (fases previas — NO son devengado).
  pia: number;
  pim: number;
  certificado: number;
  comprometido_anual: number;
  comprometido_mensual: number;
  saldo_disponible: number;
  reservado_pedido: number;

  // Bloque MEF (oficial). `null` si la meta no está en el snapshot MEF.
  pim_mef: number | null;
  certificado_mef: number | null;
  comprometido_mef: number | null;
  devengado_mef: number | null;
  girado_mef: number | null;
  saldo_disponible_mef: number | null;

  // % y semáforo sobre el devengado MEF real (`null`/'desconocido' si no cruza).
  porcentaje_devengado: number | null;
  semaforo: SemaforoSaldo;
}

export interface SaldosListadoResponse {
  items: SaldoItem[];
  total: number;
  page: number;
  size: number;
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
