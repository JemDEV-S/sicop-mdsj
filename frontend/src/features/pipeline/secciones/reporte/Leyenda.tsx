// Leyenda del recorrido y las marcas de dinero (color + texto, nunca color solo).

export function Leyenda() {
  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-2 rounded-md border border-border bg-card px-4 py-2.5 text-[11.5px] text-muted-foreground">
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-5 rounded-sm bg-secondary" aria-hidden="true" />
        Etapa cumplida por el pedido
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-5 rounded-sm border-2 border-primary bg-card"
          aria-hidden="true"
        />
        Etapa actual
      </span>
      <span className="flex items-center gap-1.5">
        <span
          className="inline-block h-2.5 w-5 rounded-sm"
          style={{
            backgroundImage:
              'repeating-linear-gradient(45deg, var(--color-primary) 0 3px, var(--color-accent) 3px 6px)',
          }}
          aria-hidden="true"
        />
        Avance de bolsa compartida (del grupo)
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-block h-2.5 w-5 rounded-sm bg-muted-foreground/40" aria-hidden="true" />
        Etapa no alcanzada
      </span>
      <span className="flex items-center gap-1.5">
        <span className="rounded bg-accent/20 px-1.5 py-0.5 font-mono text-[10px] uppercase text-accent-foreground">
          est.
        </span>
        Devengado repartido — no sumar por pedido
      </span>
      <span className="flex items-center gap-1.5">
        <span className="rounded bg-secondary/20 px-1.5 py-0.5 font-mono text-[10px] uppercase text-secondary-foreground">
          directo
        </span>
        Celda de un solo pedido, sin reparto
      </span>
      <span className="flex items-center gap-1.5">
        <span className="inline-flex items-center gap-1 rounded-full bg-semaforo-alerta/20 px-1.5 py-0.5 text-[10px] font-medium text-accent-foreground ring-1 ring-inset ring-semaforo-alerta/50">
          <span className="inline-block h-1.5 w-1.5 rounded-full bg-semaforo-alerta" aria-hidden="true" />
          En riesgo
        </span>
        Semáforo temporal: avance de devengado vs. lo esperado al mes de corte
      </span>
    </div>
  );
}
