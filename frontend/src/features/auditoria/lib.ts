/**
 * Traducción de códigos de acción de auditoría a lenguaje llano (§1.1 guía).
 *
 * Los códigos son los de `auditoria_service.Accion` (backend). El catálogo del
 * filtro es DINÁMICO (lo que ocurrió de verdad); este mapa solo embellece la
 * etiqueta. Un código sin entrada se muestra tal cual — nunca se rompe la UI
 * por una acción nueva que aún no tenga traducción.
 */

const ETIQUETAS: Record<string, string> = {
  login_exitoso: 'Inicio de sesión',
  login_fallido: 'Inicio de sesión fallido',
  logout: 'Cierre de sesión',
  cambio_password: 'Cambio de contraseña',
  cambio_password_fallido: 'Cambio de contraseña fallido',
  exportacion_reporte: 'Exportación de reporte',
  cambio_umbral: 'Cambio de umbral',
  cambio_alerta: 'Cambio de alerta',
  subida_documento_obra: 'Subida de documento de obra',
  observacion_publicada: 'Observación ciudadana publicada',
  revision_alerta: 'Alerta marcada como revisada',
  resolucion_ccmn_creada: 'Asociación pedido–CCMN creada',
  resolucion_ccmn_revocada: 'Asociación pedido–CCMN revocada',
  anotacion_creada: 'Anotación creada',
  anotacion_borrada: 'Anotación borrada',
  consulta_cruce_meta: 'Consulta de cruce por meta',
  consulta_saldos_cc: 'Consulta de saldos por unidad',
  trigger_sync_siaf: 'Sincronización SIAF (manual)',
  trigger_sync_invierte: 'Sincronización Invierte (manual)',
};

export function etiquetaAccion(codigo: string): string {
  return ETIQUETAS[codigo] ?? codigo;
}

/**
 * Familia visual de la acción, para colorear discretamente la fila.
 * - `seguridad`: login/logout/password (autenticación).
 * - `fallo`: acciones fallidas (resaltar).
 * - `escritura`: cambia estado del sistema.
 * - `consulta`: lecturas sensibles registradas.
 * - `neutro`: el resto.
 */
export type FamiliaAccion = 'seguridad' | 'fallo' | 'escritura' | 'consulta' | 'neutro';

export function familiaAccion(codigo: string): FamiliaAccion {
  if (codigo.endsWith('_fallido')) return 'fallo';
  if (codigo.startsWith('login') || codigo === 'logout' || codigo.startsWith('cambio_password')) {
    return 'seguridad';
  }
  if (codigo.startsWith('consulta_')) return 'consulta';
  if (
    codigo.startsWith('cambio_') ||
    codigo.startsWith('anotacion_') ||
    codigo.startsWith('resolucion_') ||
    codigo.startsWith('trigger_') ||
    codigo === 'exportacion_reporte' ||
    codigo === 'subida_documento_obra' ||
    codigo === 'observacion_publicada' ||
    codigo === 'revision_alerta'
  ) {
    return 'escritura';
  }
  return 'neutro';
}
