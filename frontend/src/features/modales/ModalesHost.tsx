// Host de la pila de modales: overlay + cabecera de migas (cada modal apilado
// es un botón para volver a él) + botón cerrar. Renderiza el modal del tope de
// la pila según su tipo. Escape cierra; el scroll del fondo se bloquea.

import { useEffect } from 'react';
import { X } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useModales, type EntradaModal, type TipoModal } from './ModalesContext';
import { ModalPedido } from './modales/ModalPedido';
import { ModalOrden } from './modales/ModalOrden';
import { ModalSiaf } from './modales/ModalSiaf';
import { ModalPecosa } from './modales/ModalPecosa';
import { ModalReporte } from './modales/ModalReporte';

const ANCHO: Record<TipoModal, string> = {
  pedido: 'max-w-5xl',
  orden: 'max-w-3xl',
  siaf: 'max-w-5xl',
  pecosa: 'max-w-2xl',
  reporte: 'max-w-6xl',
};

const TIPO_LABEL: Record<TipoModal, string> = {
  pedido: 'Requerimiento',
  orden: 'Orden',
  siaf: 'Exp. SIAF',
  pecosa: 'PECOSA',
  reporte: 'Reporte',
};

function idDe(e: EntradaModal): string {
  switch (e.tipo) {
    case 'pedido':
      return String(e.nroPedido);
    case 'orden':
      return String(e.nroOrden);
    case 'siaf':
      return String(e.expSiaf);
    case 'pecosa':
      return String(e.nroMovimiento);
    case 'reporte':
      return e.secFunc != null ? String(e.secFunc) : 'ámbito';
  }
}

export function ModalesHost() {
  const { pila, volver, cerrar } = useModales();
  const hayModal = pila.length > 0;
  const top = hayModal ? pila[pila.length - 1] : null;

  useEffect(() => {
    if (!hayModal) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') cerrar();
    }
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [hayModal, cerrar]);

  if (!top) return null;

  return (
    <div
      className="fixed inset-0 z-[60] flex items-start justify-center overflow-y-auto bg-foreground/40 px-4 py-8"
      role="dialog"
      aria-modal="true"
      aria-label={`${TIPO_LABEL[top.tipo]} ${idDe(top)}`}
      onClick={cerrar}
    >
      <div
        className={cn(
          'flex w-full flex-col overflow-hidden rounded-lg border border-border bg-card shadow-xl',
          ANCHO[top.tipo],
        )}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Cabecera de migas de la pila */}
        <div className="flex flex-wrap items-center gap-2 border-b border-border bg-muted/30 px-4 py-2.5">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-1.5">
            {pila.map((p, i) => {
              const esTope = i === pila.length - 1;
              return (
                <div key={`${p.tipo}-${idDe(p)}-${i}`} className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => volver(i)}
                    className={cn(
                      'inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11.5px] transition-colors',
                      esTope
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-border bg-card text-muted-foreground hover:bg-muted',
                    )}
                  >
                    <span className="text-[9px] uppercase tracking-wide opacity-80">
                      {TIPO_LABEL[p.tipo]}
                    </span>
                    <span className="font-mono font-semibold">{idDe(p)}</span>
                  </button>
                  {!esTope ? <span className="text-muted-foreground/60" aria-hidden="true">›</span> : null}
                </div>
              );
            })}
          </div>
          <button
            type="button"
            onClick={cerrar}
            aria-label="Cerrar"
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-border bg-card text-muted-foreground transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>

        {/* Cuerpo del modal del tope */}
        <div className="min-h-0 flex-1 p-5">
          {top.tipo === 'pedido' ? <ModalPedido entrada={top} /> : null}
          {top.tipo === 'orden' ? <ModalOrden entrada={top} /> : null}
          {top.tipo === 'siaf' ? <ModalSiaf entrada={top} /> : null}
          {top.tipo === 'pecosa' ? <ModalPecosa entrada={top} /> : null}
          {top.tipo === 'reporte' ? <ModalReporte entrada={top} /> : null}
        </div>
      </div>
    </div>
  );
}

export default ModalesHost;
