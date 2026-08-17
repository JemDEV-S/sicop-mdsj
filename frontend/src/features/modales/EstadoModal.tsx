// Estados de carga/error compartidos por los modales que consultan al backend.

import { Loader2 } from 'lucide-react';

export function CargandoModal({ texto }: { texto: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-muted-foreground">
      <Loader2 className="mb-3 h-7 w-7 animate-spin text-primary" aria-hidden="true" />
      <p className="text-sm">{texto}</p>
    </div>
  );
}

export function ErrorModal({ texto, onReintentar }: { texto: string; onReintentar?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-14 text-center">
      <p className="max-w-md text-sm text-muted-foreground">{texto}</p>
      {onReintentar ? (
        <button
          type="button"
          onClick={onReintentar}
          className="rounded-md border border-primary bg-card px-3 py-1.5 text-sm font-medium text-primary transition-colors hover:bg-primary/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
