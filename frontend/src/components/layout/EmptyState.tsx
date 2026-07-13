import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface EmptyStateAccion {
  label: string;
  onClick?: () => void;
  href?: string;
}

interface EmptyStateProps {
  icono?: LucideIcon;
  titulo: string;
  descripcion?: React.ReactNode;
  accion?: EmptyStateAccion;
  className?: string;
}

export function EmptyState({
  icono: Icono,
  titulo,
  descripcion,
  accion,
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center text-center py-12 px-6',
        className,
      )}
      role="status"
    >
      {Icono ? (
        <Icono
          className="w-12 h-12 text-muted-foreground mb-4"
          aria-hidden="true"
        />
      ) : null}
      <h3 className="text-lg font-semibold text-foreground">{titulo}</h3>
      {descripcion ? (
        <p className="mt-2 max-w-md text-sm text-muted-foreground">
          {descripcion}
        </p>
      ) : null}
      {accion ? (
        <div className="mt-6">
          {accion.href ? (
            <Button asChild variant="outline">
              <Link to={accion.href}>{accion.label}</Link>
            </Button>
          ) : (
            <Button variant="outline" onClick={accion.onClick}>
              {accion.label}
            </Button>
          )}
        </div>
      ) : null}
    </div>
  );
}

export default EmptyState;
