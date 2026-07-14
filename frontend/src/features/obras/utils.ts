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

/**
 * Convierte el % de avance físico en una etiqueta descriptiva neutral
 * (sin juicios "crítico/alerta"). El avance real depende de la
 * complejidad y el tiempo de inicio, por lo que aquí solo describimos
 * la etapa observable de la obra.
 */
export function etiquetaEtapaAvance(
  avanceRaw: number | string | null | undefined,
): { titulo: string; descripcion: string } {
  if (avanceRaw == null || avanceRaw === '') {
    return {
      titulo: 'Avance por publicar',
      descripcion: 'Aún no se ha reportado el avance físico en el sistema del MEF.',
    };
  }
  const avance = typeof avanceRaw === 'number' ? avanceRaw : parseFloat(avanceRaw);
  if (Number.isNaN(avance)) {
    return {
      titulo: 'Avance por publicar',
      descripcion: 'Aún no se ha reportado el avance físico en el sistema del MEF.',
    };
  }
  if (avance >= 100) {
    return {
      titulo: 'Obra terminada',
      descripcion: 'La ejecución física alcanzó el 100% de lo previsto.',
    };
  }
  if (avance >= 70) {
    return {
      titulo: 'Cerca de finalizar',
      descripcion: 'La obra está en la recta final de su ejecución.',
    };
  }
  if (avance >= 30) {
    return {
      titulo: 'En plena construcción',
      descripcion: 'La obra avanza en su etapa central de ejecución.',
    };
  }
  if (avance > 0) {
    return {
      titulo: 'En etapa inicial',
      descripcion: 'La ejecución acaba de comenzar. Los primeros meses suelen concentrarse en trámites y preparativos.',
    };
  }
  return {
    titulo: 'Aún por iniciar en obra',
    descripcion: 'La ejecución física no ha comenzado. Puede estar en fase de estudios, expediente técnico o proceso de contratación.',
  };
}
