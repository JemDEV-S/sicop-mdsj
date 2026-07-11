import type { EstadoSemaforo } from '../lib/semaforo';
import { cn } from '../lib/utils';

interface SemaforoProps {
  estado: EstadoSemaforo;
  /** El texto descriptivo es obligatorio por accesibilidad (SKILL.md) */
  texto: string;
  className?: string;
}

export default function Semaforo({ estado, texto, className }: SemaforoProps) {
  // Colores extraídos directamente de las variables de Tailwind configuradas
  const config: Record<EstadoSemaforo, { bg: string, text: string }> = {
    ok: {
      bg: 'bg-[var(--semaforo-ok)]',
      text: 'text-white',
    },
    alerta: {
      bg: 'bg-[var(--semaforo-alerta)]',
      // NOTA SOBRE CONTRASTE: el amarillo (#F0C84F) sobre texto blanco no pasa WCAG AA.
      // Se utiliza gris muy oscuro (gray-900) para asegurar legibilidad.
      text: 'text-gray-900',
    },
    critico: {
      bg: 'bg-[var(--semaforo-critico)]',
      text: 'text-white',
    },
  };

  const { bg, text } = config[estado];

  return (
    <div 
      className={cn(
        "inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-sm font-medium",
        bg,
        text,
        className
      )}
    >
      <div className={cn("w-2 h-2 rounded-full", estado === 'alerta' ? 'bg-gray-900' : 'bg-white')} />
      <span>{texto}</span>
    </div>
  );
}
