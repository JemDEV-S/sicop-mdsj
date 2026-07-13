/**
 * Mapea el estado del semáforo a las clases utilitarias de Tailwind
 * basadas en la paleta institucional (globals.css).
 */
export function semaforoToIconClass(semaforo: string | null | undefined): string {
  switch (semaforo) {
    case 'verde':
      return 'bg-semaforo-ok text-secondary-foreground';
    case 'amarillo':
      // Amarillo requiere contraste oscuro para su texto interno
      return 'bg-semaforo-alerta text-accent-foreground';
    case 'rojo':
      return 'bg-semaforo-critico text-destructive-foreground';
    case 'desconocido':
    default:
      // Fail-safe neutral
      return 'bg-muted text-muted-foreground';
  }
}
