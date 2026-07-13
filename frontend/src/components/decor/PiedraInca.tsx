import { cn } from '@/lib/utils';

interface PiedraIncaProps {
  className?: string;
  opacidad?: number;
  color?: 'primary' | 'accent' | 'foreground' | 'muted-foreground';
}

const colorMap: Record<NonNullable<PiedraIncaProps['color']>, string> = {
  primary: 'text-primary',
  accent: 'text-accent',
  foreground: 'text-foreground',
  'muted-foreground': 'text-muted-foreground',
};

/**
 * Muro inca de piedra poligonal. Piezas grandes, encaje irregular estilo
 * Sacsayhuamán. Pensado como enmarque estructural del hero, no como textura
 * de fondo repetida sobre toda la pantalla.
 *
 * Usar dentro de un contenedor `relative overflow-hidden`, con posición
 * absoluta y opacidad baja (0.05 - 0.12).
 */
export function PiedraInca({
  className,
  opacidad = 0.08,
  color = 'primary',
}: PiedraIncaProps) {
  return (
    <svg
      aria-hidden="true"
      className={cn('block', colorMap[color], className)}
      preserveAspectRatio="xMidYMid slice"
      viewBox="0 0 400 400"
      xmlns="http://www.w3.org/2000/svg"
      style={{ opacity: opacidad }}
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinejoin="round"
        strokeLinecap="round"
      >
        {/* Fila superior */}
        <path d="M 0 0 L 95 0 L 110 55 L 60 70 L 0 60 Z" />
        <path d="M 95 0 L 210 0 L 225 50 L 170 65 L 110 55 Z" />
        <path d="M 210 0 L 320 0 L 315 60 L 245 70 L 225 50 Z" />
        <path d="M 320 0 L 400 0 L 400 65 L 315 60 Z" />

        {/* Fila 2 — piedras grandes, la del centro es la piedra madre */}
        <path d="M 0 60 L 60 70 L 55 155 L 0 145 Z" />
        <path d="M 60 70 L 170 65 L 195 145 L 130 165 L 55 155 Z" />
        <path d="M 170 65 L 245 70 L 265 150 L 195 145 Z" />
        <path d="M 245 70 L 315 60 L 335 145 L 265 150 Z" />
        <path d="M 315 60 L 400 65 L 400 155 L 335 145 Z" />

        {/* Fila 3 — piedra irregular grande al centro */}
        <path d="M 0 145 L 55 155 L 70 230 L 0 220 Z" />
        <path d="M 55 155 L 130 165 L 155 240 L 70 230 Z" />
        <path d="M 130 165 L 195 145 L 265 150 L 250 235 L 155 240 Z" />
        <path d="M 265 150 L 335 145 L 340 235 L 250 235 Z" />
        <path d="M 335 145 L 400 155 L 400 240 L 340 235 Z" />

        {/* Fila 4 */}
        <path d="M 0 220 L 70 230 L 85 305 L 0 295 Z" />
        <path d="M 70 230 L 155 240 L 165 315 L 85 305 Z" />
        <path d="M 155 240 L 250 235 L 245 320 L 165 315 Z" />
        <path d="M 250 235 L 340 235 L 335 310 L 245 320 Z" />
        <path d="M 340 235 L 400 240 L 400 315 L 335 310 Z" />

        {/* Fila inferior */}
        <path d="M 0 295 L 85 305 L 75 400 L 0 400 Z" />
        <path d="M 85 305 L 165 315 L 175 400 L 75 400 Z" />
        <path d="M 165 315 L 245 320 L 240 400 L 175 400 Z" />
        <path d="M 245 320 L 335 310 L 325 400 L 240 400 Z" />
        <path d="M 335 310 L 400 315 L 400 400 L 325 400 Z" />
      </g>
    </svg>
  );
}

export default PiedraInca;
