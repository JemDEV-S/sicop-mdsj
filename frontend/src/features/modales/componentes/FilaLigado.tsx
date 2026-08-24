// Fila de documento ligado (formato de la plantilla v2): tipo + id mono + nota +
// flecha. Apila el modal destino al hacer clic. Reutilizada por los modales de
// orden, expediente y demás.

import { ArrowRight } from 'lucide-react';

export interface Ligado {
  tipo: string;
  id: string | number;
  nota?: string | null;
  onClick: () => void;
}

export function FilaLigado({ tipo, id, nota, onClick }: Ligado) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center gap-2.5 rounded-lg border border-border bg-superficie-alt-2 px-3 py-2.5 text-left transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <span className="w-16 shrink-0 text-[9.5px] uppercase tracking-wide text-muted-foreground">{tipo}</span>
      <span className="shrink-0 font-mono text-[12px] font-semibold text-foreground">{id}</span>
      {nota ? (
        <span className="min-w-0 flex-1 truncate text-[11.5px] text-muted-foreground">{nota}</span>
      ) : (
        <span className="flex-1" />
      )}
      <ArrowRight className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden="true" />
    </button>
  );
}

export function ListaLigados({ ligados, vacio }: { ligados: Ligado[]; vacio?: string }) {
  if (ligados.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-border px-3 py-4 text-center text-[12px] text-muted-foreground">
        {vacio ?? 'Sin documentos ligados.'}
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-2">
      {ligados.map((l) => (
        <FilaLigado key={`${l.tipo}-${l.id}`} {...l} />
      ))}
    </div>
  );
}

export default FilaLigado;
