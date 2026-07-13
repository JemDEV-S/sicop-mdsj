export type EstadoSemaforo = 'ok' | 'alerta' | 'critico';
export type DireccionSemaforo = 'mayor' | 'menor';

/**
 * Calcula el estado de un semáforo basado en umbrales de negocio.
 * 
 * Caso Límite Mayor:
 * - Si valor >= umbralVerde -> ok
 * - Si valor >= umbralAmarillo -> alerta
 * - Si valor < umbralAmarillo -> critico
 * 
 * Caso Límite Menor:
 * - Si valor <= umbralVerde -> ok
 * - Si valor <= umbralAmarillo -> alerta
 * - Si valor > umbralAmarillo -> critico
 */
export function calcularSemaforo(
  valor: number,
  umbralVerde: number,
  umbralAmarillo: number,
  direccion: DireccionSemaforo
): EstadoSemaforo {
  if (direccion === 'mayor') {
    if (valor >= umbralVerde) return 'ok';
    if (valor >= umbralAmarillo) return 'alerta';
    return 'critico';
  } else {
    // direccion === 'menor'
    if (valor <= umbralVerde) return 'ok';
    if (valor <= umbralAmarillo) return 'alerta';
    return 'critico';
  }
}
