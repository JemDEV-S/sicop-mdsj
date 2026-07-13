import { cn } from '@/lib/utils';

const base = 'bg-muted animate-pulse rounded-md';

interface SkeletonBaseProps {
  className?: string;
}

export function SkeletonBloque({ className }: SkeletonBaseProps) {
  return <div className={cn(base, className)} aria-hidden="true" />;
}

export function SkeletonCard({ className }: SkeletonBaseProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-md p-5 space-y-3',
        className,
      )}
      aria-hidden="true"
    >
      <SkeletonBloque className="h-4 w-1/3" />
      <SkeletonBloque className="h-8 w-2/3" />
      <SkeletonBloque className="h-3 w-1/2" />
    </div>
  );
}

export function SkeletonKPI({ className }: SkeletonBaseProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-md p-5 space-y-2',
        className,
      )}
      aria-hidden="true"
    >
      <SkeletonBloque className="h-3 w-1/2" />
      <SkeletonBloque className="h-9 w-3/4" />
    </div>
  );
}

interface SkeletonTableProps extends SkeletonBaseProps {
  rows?: number;
  cols?: number;
}

export function SkeletonTable({
  rows = 5,
  cols = 4,
  className,
}: SkeletonTableProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-md overflow-hidden',
        className,
      )}
      aria-hidden="true"
    >
      <div
        className="grid gap-4 border-b border-border bg-muted px-4 py-3"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: cols }).map((_, i) => (
          <SkeletonBloque key={`h-${i}`} className="h-3" />
        ))}
      </div>
      <div className="divide-y divide-border">
        {Array.from({ length: rows }).map((_, r) => (
          <div
            key={`r-${r}`}
            className="grid gap-4 px-4 py-3"
            style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
          >
            {Array.from({ length: cols }).map((_, c) => (
              <SkeletonBloque key={`c-${r}-${c}`} className="h-4" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

interface SkeletonGraficoProps extends SkeletonBaseProps {
  alto?: number;
}

export function SkeletonGrafico({ alto = 260, className }: SkeletonGraficoProps) {
  return (
    <div
      className={cn(
        'bg-card border border-border rounded-md p-5 space-y-3',
        className,
      )}
      aria-hidden="true"
    >
      <SkeletonBloque className="h-4 w-1/3" />
      <div className={cn(base, 'w-full')} style={{ height: `${alto}px` }} />
    </div>
  );
}
