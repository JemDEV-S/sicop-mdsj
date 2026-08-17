// Bloque de identificadores del pedido: 4 tarjetas (Pedido / Orden / EXP_SIAF /
// PECOSA). Las que tienen valor y destino son clicables y apilan su modal; las
// vacías se muestran atenuadas ("sin orden", "pendiente", "—").

import { cn } from '@/lib/utils';

export interface TarjetaId {
  label: string;
  valor: string;
  /** null ⇒ tarjeta inerte (sin destino). */
  onClick?: (() => void) | null;
}

export function IdsPedido({ tarjetas }: { tarjetas: TarjetaId[] }) {
  return (
    <div className="grid shrink-0 grid-cols-2 gap-2">
      {tarjetas.map((t) => {
        const activa = Boolean(t.onClick);
        const contenido = (
          <>
            <span className="text-[9.5px] uppercase tracking-wide text-muted-foreground">{t.label}</span>
            <span
              className={cn(
                'font-mono text-[12.5px] font-semibold',
                activa ? 'text-primary' : 'text-muted-foreground',
              )}
            >
              {t.valor}
            </span>
          </>
        );
        return activa ? (
          <button
            key={t.label}
            type="button"
            onClick={t.onClick!}
            className="flex min-w-[128px] flex-col gap-0.5 rounded-lg border border-border bg-superficie-alt-2 px-2.5 py-2 text-left transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            {contenido}
          </button>
        ) : (
          <div
            key={t.label}
            className="flex min-w-[128px] flex-col gap-0.5 rounded-lg border border-border bg-superficie-alt-2 px-2.5 py-2"
          >
            {contenido}
          </div>
        );
      })}
    </div>
  );
}

export default IdsPedido;
