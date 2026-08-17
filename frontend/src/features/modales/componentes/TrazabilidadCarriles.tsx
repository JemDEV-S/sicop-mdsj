// Trazabilidad por carriles de macrofase (modal de requerimiento, plantilla v2).
//
// Cada macrofase es un carril: a la izquierda su nombre + progreso, en el centro
// el nodo con líneas conectoras, y a la derecha los hitos como chips con su
// estado (cumplido/grupo/vía/sin dato). Barra de avance con gradiente arriba y
// toggle Resumen/Detalle. Datos reales: PedidoDetalle.timeline.

import { useMemo, useState } from 'react';
import { cn } from '@/lib/utils';
import type { TimelineEvento } from '@/features/pipeline/types';
import { construirCarriles, type Carril, type HitoCarril, type TonoHito } from '../lib/trazabilidad';

// Estilo del nodo/punto del carril según su avance.
function estiloNodo(c: Carril) {
  if (c.completa) return { punto: 'bg-secondary', nodo: 'bg-secondary border-secondary', label: 'text-foreground' };
  if (c.iniciada) return { punto: 'bg-accent', nodo: 'bg-accent border-accent', label: 'text-foreground' };
  return { punto: 'bg-border', nodo: 'bg-card border-border', label: 'text-muted-foreground' };
}

// Estilo del chip de un hito según su tono.
const CHIP: Record<TonoHito, { caja: string; marca: string; label: string; tag?: string }> = {
  directo: {
    caja: 'border-secondary/30 bg-secondary/5',
    marca: 'bg-secondary text-secondary-foreground',
    label: 'font-semibold text-foreground',
  },
  via: {
    caja: 'border-primary/30 bg-primary/5',
    marca: 'bg-primary text-primary-foreground',
    label: 'font-semibold text-foreground',
    tag: 'border-primary/30 bg-primary/10 text-primary',
  },
  grupo: {
    caja: 'border-accent/40 bg-accent/10',
    marca: 'bg-accent text-accent-foreground',
    label: 'font-semibold text-foreground',
    tag: 'border-accent/40 bg-accent/15 text-accent-foreground',
  },
  sin: {
    caja: 'border-border bg-superficie-alt-2',
    marca: 'bg-card text-muted-foreground border border-border',
    label: 'text-muted-foreground',
  },
};

export function TrazabilidadCarriles({
  timeline,
  etapaActualNumero,
  etapaActualLabel,
}: {
  timeline: TimelineEvento[];
  etapaActualNumero: number;
  etapaActualLabel: string;
}) {
  const [modo, setModo] = useState<'resumen' | 'detalle'>('resumen');
  const carriles = useMemo(() => construirCarriles(timeline, modo === 'resumen'), [timeline, modo]);

  const avancePct = Math.round((etapaActualNumero / 16) * 100);

  return (
    <section className="flex flex-col gap-3 rounded-lg border border-border px-4 py-4">
      {/* Cabecera con toggle */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-[13px] font-semibold text-foreground">Trazabilidad</h3>
        <div className="flex flex-wrap items-center gap-2.5">
          <span className="text-[11px] text-muted-foreground">
            {modo === 'resumen' ? 'últimos hitos por macrofase' : '16 hitos verificables'}
          </span>
          <div className="inline-flex overflow-hidden rounded-md border border-border">
            {(['resumen', 'detalle'] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => setModo(m)}
                className={cn(
                  'px-2.5 py-1 text-[11.5px] font-medium capitalize transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-ring',
                  modo === m ? 'bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:bg-muted',
                )}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Barra de avance con gradiente */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="h-2.5 min-w-[220px] flex-1 overflow-hidden rounded-full bg-muted">
          <div
            className="h-full rounded-full bg-gradient-to-r from-primary to-secondary"
            style={{ width: `${avancePct}%` }}
          />
        </div>
        <span className="shrink-0 font-mono text-[12px] font-semibold text-primary">
          {etapaActualNumero}/16 · {avancePct}%
        </span>
        <span className="shrink-0 text-[11px] text-muted-foreground">Fase actual: {etapaActualLabel}</span>
      </div>

      {/* Carriles */}
      <div className="flex flex-col">
        {carriles.map((c) => (
          <FilaCarril key={c.macrofase} carril={c} />
        ))}
      </div>

      {/* Leyenda */}
      <div className="flex flex-wrap gap-x-4 gap-y-1.5 border-t border-border pt-2.5 text-[10.5px] text-muted-foreground">
        <Leyenda claseCuadro="bg-secondary" texto="cumplido con documento" />
        <Leyenda claseCuadro="bg-accent" texto="evidencia de grupo (bolsa CCMN)" />
        <Leyenda claseCuadro="bg-primary" texto="vía CCMN identificado" />
        <Leyenda claseCuadro="border border-border bg-card" texto="sin dato aún" />
      </div>
    </section>
  );
}

function FilaCarril({ carril }: { carril: Carril }) {
  const nodo = estiloNodo(carril);
  return (
    <div className="flex items-stretch gap-3">
      {/* Columna izquierda: nombre + progreso */}
      <div className="flex w-28 shrink-0 flex-col gap-0.5 py-2.5">
        <span className="inline-flex items-center gap-1.5">
          <span className={cn('h-1.5 w-1.5 shrink-0 rounded-full', nodo.punto)} aria-hidden="true" />
          <span className={cn('text-[11.5px] font-semibold', nodo.label)}>{carril.label}</span>
        </span>
        <span className="pl-3 font-mono text-[10px] text-muted-foreground/80">{carril.progreso}</span>
      </div>

      {/* Columna central: línea + nodo + línea */}
      <div className="flex w-5 shrink-0 flex-col items-center">
        <span
          className={cn('w-0.5 shrink-0', carril.primerCarril ? 'bg-transparent' : carril.iniciada ? 'bg-secondary/40' : 'bg-border')}
          style={{ height: 9 }}
          aria-hidden="true"
        />
        <span className={cn('h-3 w-3 shrink-0 rounded-full border-[2.5px]', nodo.nodo)} aria-hidden="true" />
        <span
          className={cn('w-0.5 flex-1', carril.ultimoCarril ? 'bg-transparent' : carril.completa ? 'bg-secondary/40' : 'bg-border')}
          style={{ minHeight: 9 }}
          aria-hidden="true"
        />
      </div>

      {/* Columna derecha: chips de hitos */}
      <div className="flex min-w-0 flex-1 flex-wrap gap-1.5 py-2 pb-3">
        {carril.hitos.map((h) => (
          <ChipHito key={h.numero} hito={h} />
        ))}
      </div>
    </div>
  );
}

function ChipHito({ hito }: { hito: HitoCarril }) {
  const est = CHIP[hito.tono];
  return (
    <span
      className={cn('inline-flex max-w-full items-center gap-1.5 rounded-md border px-2 py-1', est.caja)}
    >
      <span
        className={cn(
          'flex h-4 w-4 shrink-0 items-center justify-center rounded font-mono text-[9.5px] font-semibold',
          est.marca,
        )}
        aria-hidden="true"
      >
        {hito.marca}
      </span>
      <span className="flex min-w-0 flex-col">
        <span className={cn('whitespace-nowrap text-[11.5px] leading-tight', est.label)}>{hito.label}</span>
        <span className="font-mono text-[9.5px] leading-tight text-muted-foreground/80">{hito.doc}</span>
      </span>
      {hito.tag && est.tag ? (
        <span className={cn('shrink-0 rounded border px-1.5 py-px text-[9px] font-semibold', est.tag)}>
          {hito.tag}
        </span>
      ) : null}
    </span>
  );
}

function Leyenda({ claseCuadro, texto }: { claseCuadro: string; texto: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={cn('h-2.5 w-2.5 rounded-[3px]', claseCuadro)} aria-hidden="true" />
      {texto}
    </span>
  );
}

export default TrazabilidadCarriles;
