import { FileText } from 'lucide-react';
import type { ObraDetalleResponse } from '../types';

export function Identificacion({ obra }: { obra: ObraDetalleResponse }) {
  const filas: { label: string; valor: string | null; monospace?: boolean }[] = [
    { label: 'CUI', valor: obra.codigo_unico, monospace: true },
    { label: 'Función', valor: obra.funcion },
    { label: 'Programa', valor: obra.programa },
    { label: 'Tipología', valor: obra.tipologia },
    { label: 'Modalidad', valor: obra.modalidad },
    { label: 'Marco', valor: obra.marco },
    { label: 'Estado', valor: obra.estado },
    { label: 'Situación', valor: obra.situacion },
    { label: 'Unidad ejecutora (UEI)', valor: obra.nombre_uei },
    { label: 'Unidad formuladora (UF)', valor: obra.nombre_uf },
  ];

  return (
    <div className="rounded-2xl bg-card border border-border overflow-hidden h-full flex flex-col">
      <header className="flex items-center gap-2 px-6 py-4 border-b border-border bg-muted/40">
        <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
          <FileText className="w-4 h-4" aria-hidden="true" />
        </span>
        <div>
          <h3 className="text-sm font-semibold text-foreground">Identificación</h3>
          <p className="text-xs text-muted-foreground">Datos registrados en Invierte.pe</p>
        </div>
      </header>

      <dl className="p-6 grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-4 text-sm flex-1">
        {filas.map((fila) => (
          <div key={fila.label} className="flex flex-col gap-0.5 min-w-0">
            <dt className="text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
              {fila.label}
            </dt>
            <dd
              className={
                fila.monospace
                  ? 'text-sm font-mono text-foreground break-all'
                  : 'text-sm font-medium text-foreground'
              }
            >
              {fila.valor || '—'}
            </dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
