import * as React from 'react';
import { AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ErrorStateProps {
  titulo?: string;
  descripcion?: React.ReactNode;
  onReintentar?: () => void;
  className?: string;
}

export function ErrorState({
  titulo = 'No se pudo cargar la información',
  descripcion = 'Verifica tu conexión e intenta de nuevo. Si el problema continúa, comunícate con el equipo de soporte.',
  onReintentar,
  className,
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn(
        'border border-destructive rounded-md bg-card p-6 flex flex-col items-start gap-3',
        className,
      )}
    >
      <div className="flex items-center gap-2 text-destructive">
        <AlertTriangle className="w-5 h-5" aria-hidden="true" />
        <h3 className="text-base font-semibold">{titulo}</h3>
      </div>
      {descripcion ? (
        <p className="text-sm text-muted-foreground">{descripcion}</p>
      ) : null}
      {onReintentar ? (
        <Button variant="outline" onClick={onReintentar} className="mt-2">
          Reintentar
        </Button>
      ) : null}
    </div>
  );
}

export default ErrorState;
