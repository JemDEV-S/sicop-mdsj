import { cn } from '@/lib/utils';

interface GrecaAndinaProps {
  className?: string;
  color?: 'primary' | 'accent' | 'secondary' | 'muted' | 'primary-foreground';
  variante?: 'escalonada' | 'zigzag';
  altura?: number;
}

const colorMap: Record<NonNullable<GrecaAndinaProps['color']>, string> = {
  primary: 'text-primary',
  accent: 'text-accent',
  secondary: 'text-secondary',
  muted: 'text-muted-foreground',
  'primary-foreground': 'text-primary-foreground',
};

export function GrecaAndina({
  className,
  color = 'accent',
  variante = 'escalonada',
  altura = 8,
}: GrecaAndinaProps) {
  const pattern =
    variante === 'escalonada' ? (
      <pattern id="greca-escalonada" x="0" y="0" width="32" height="16" patternUnits="userSpaceOnUse">
        <path
          d="M 0 12 L 4 12 L 4 8 L 8 8 L 8 4 L 12 4 L 12 0 L 20 0 L 20 4 L 24 4 L 24 8 L 28 8 L 28 12 L 32 12 L 32 16 L 0 16 Z"
          fill="currentColor"
        />
      </pattern>
    ) : (
      <pattern id="greca-zigzag" x="0" y="0" width="24" height="16" patternUnits="userSpaceOnUse">
        <path
          d="M 0 14 L 6 4 L 12 14 L 18 4 L 24 14 L 24 16 L 0 16 Z"
          fill="currentColor"
        />
      </pattern>
    );

  const patternId = variante === 'escalonada' ? 'greca-escalonada' : 'greca-zigzag';

  return (
    <svg
      aria-hidden="true"
      className={cn('block w-full', colorMap[color], className)}
      style={{ height: `${altura}px` }}
      preserveAspectRatio="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>{pattern}</defs>
      <rect width="100%" height="100%" fill={`url(#${patternId})`} />
    </svg>
  );
}

export default GrecaAndina;
