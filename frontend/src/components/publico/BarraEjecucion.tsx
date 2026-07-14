'use client';

import { cn } from '@/lib/utils';
import { useLayoutEffect, useRef, useState } from 'react';

interface BarraEjecucionProps {
  pim: number;
  certificado: number | null;
  comprometido: number | null;
  devengado: number | null;
  girado?: number | null;
  className?: string;
  /** Formato de montos para las etiquetas debajo. */
  formatoMonto: (v: number | null) => string;
  /** Etiqueta accesible. */
  ariaLabel?: string;
}

interface Etapa {
  key: string;
  label: string;
  pct: number;
  monto: number | null;
  color: string;
  text: string;
}

/**
 * Barra de ejecución escalonada del presupuesto.
 * Muestra Certificado → Comprometido → Devengado → Girado como capas
 * apiladas de mayor a menor porcentaje, sobre el fondo del PIM.
 * Debajo, marcadores puntuales con el porcentaje respectivo, con
 * detección de colisiones para que no se superpongan entre sí.
 */
export function BarraEjecucion({
  pim,
  certificado,
  comprometido,
  devengado,
  girado = null,
  className,
  formatoMonto,
  ariaLabel = 'Avance de ejecución presupuestal',
}: BarraEjecucionProps) {
  const pct = (v: number | null) =>
    v === null || pim <= 0 ? 0 : Math.min(100, Math.max(0, (v / pim) * 100));

  const pCer = pct(certificado);
  const pCom = pct(comprometido);
  const pDev = pct(devengado);
  const pGir = pct(girado);

  const etapas: Etapa[] = [
    { key: 'cer', label: 'Certificado', pct: pCer, monto: certificado, color: 'bg-accent', text: 'text-accent-foreground' },
    { key: 'com', label: 'Comprometido', pct: pCom, monto: comprometido, color: 'bg-secondary/60', text: 'text-secondary' },
    { key: 'dev', label: 'Devengado', pct: pDev, monto: devengado, color: 'bg-primary', text: 'text-primary' },
    { key: 'gir', label: 'Girado', pct: pGir, monto: girado, color: 'bg-primary/70', text: 'text-primary' },
  ].filter((e) => e.monto !== null);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Barra */}
      <div
        className="relative h-4 w-full rounded-full bg-muted overflow-hidden ring-1 ring-border"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(pDev)}
        aria-label={ariaLabel}
      >
        {/* Se pintan de mayor a menor porcentaje para que las capas superiores no tapen las inferiores */}
        {[...etapas].sort((a, b) => b.pct - a.pct).map((etapa) => (
          <div
            key={etapa.key}
            className={cn('absolute inset-y-0 left-0 transition-all', etapa.color)}
            style={{ width: `${etapa.pct}%` }}
            aria-hidden="true"
          />
        ))}
      </div>

      {/* Etiquetas debajo, con anti-colisión */}
      <EtiquetasEtapas etapas={etapas} formatoMonto={formatoMonto} />

      {/* Versión móvil apilada (sin problema de solape, va en lista vertical) */}
      <ul className="sm:hidden space-y-2 text-sm">
        {etapas.map((etapa) => (
          <li key={etapa.key} className="flex items-center justify-between gap-3">
            <span className="flex items-center gap-2 text-muted-foreground">
              <span className={cn('inline-block w-2.5 h-2.5 rounded-full', etapa.color)} aria-hidden="true" />
              {etapa.label}
            </span>
            <span className="font-medium text-foreground tabular-nums">
              {etapa.pct.toFixed(1)}% <span className="text-muted-foreground font-normal">· {formatoMonto(etapa.monto)}</span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface EtiquetasEtapasProps {
  etapas: Etapa[];
  formatoMonto: (v: number | null) => string;
}

const GAP_MIN_PX = 10; // separación mínima horizontal entre etiquetas
const ANCHO_ESTIMADO_PX = 76; // ancho de respaldo antes de la primera medición real

/**
 * Renderiza las etiquetas debajo de la barra y las reacomoda para que
 * nunca se superpongan, sin importar qué tan cerca estén los porcentajes.
 *
 * Estrategia:
 * 1. Se renderiza cada etiqueta en su posición "real" (según %) para poder medir su ancho.
 * 2. Se calcula, de izquierda a derecha, el desplazamiento mínimo necesario
 *    para que cada etiqueta no invada el espacio de la anterior.
 * 3. Si el bloque completo se sale del contenedor por la derecha, se retrocede
 *    en conjunto; luego se re-verifica que no se generen nuevos solapes.
 * 4. El resultado se guarda como un offset en px por etiqueta y se aplica con `transform`.
 */
function EtiquetasEtapas({ etapas, formatoMonto }: EtiquetasEtapasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const itemRefs = useRef<Record<string, HTMLDivElement | null>>({});
  const [offsets, setOffsets] = useState<Record<string, number>>({});

  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const recalcular = () => {
      const containerWidth = container.offsetWidth;
      if (containerWidth === 0) return;

      const ordenadas = [...etapas].sort((a, b) => a.pct - b.pct);

      const nodos = ordenadas.map((e) => ({
        key: e.key,
        centro: (e.pct / 100) * containerWidth,
        ancho: itemRefs.current[e.key]?.offsetWidth || ANCHO_ESTIMADO_PX,
      }));

      // Empuje de izquierda a derecha: cada etiqueta respeta el espacio de la anterior
      for (let i = 1; i < nodos.length; i++) {
        const prev = nodos[i - 1];
        const cur = nodos[i];
        const minCentro = prev.centro + prev.ancho / 2 + GAP_MIN_PX + cur.ancho / 2;
        if (cur.centro < minCentro) cur.centro = minCentro;
      }

      // Si el bloque se sale por la derecha, se retrocede todo en conjunto
      const ultimo = nodos[nodos.length - 1];
      if (ultimo) {
        const exceso = ultimo.centro + ultimo.ancho / 2 - containerWidth;
        if (exceso > 0) {
          nodos.forEach((n) => (n.centro -= exceso));
          // Re-verifica solapes de derecha a izquierda tras el retroceso
          for (let i = nodos.length - 2; i >= 0; i--) {
            const next = nodos[i + 1];
            const cur = nodos[i];
            const maxCentro = next.centro - next.ancho / 2 - GAP_MIN_PX - cur.ancho / 2;
            if (cur.centro > maxCentro) cur.centro = maxCentro;
          }
        }
      }

      // Evita que la primera etiqueta se salga por la izquierda
      const primero = nodos[0];
      if (primero && primero.centro < primero.ancho / 2) {
        const ajuste = primero.ancho / 2 - primero.centro;
        nodos.forEach((n) => (n.centro += ajuste));
      }

      const nuevosOffsets: Record<string, number> = {};
      nodos.forEach((n) => {
        const centroReal = (etapas.find((e) => e.key === n.key)!.pct / 100) * containerWidth;
        nuevosOffsets[n.key] = n.centro - centroReal;
      });
      setOffsets(nuevosOffsets);
    };

    recalcular();

    const resizeObserver = new ResizeObserver(recalcular);
    resizeObserver.observe(container);
    return () => resizeObserver.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [etapas.map((e) => `${e.key}:${e.pct}`).join(',')]);

  return (
    <div ref={containerRef} className="relative h-14 hidden sm:block" aria-hidden="true">
      {etapas.map((etapa) => {
        const offset = offsets[etapa.key] ?? 0;
        return (
          <div
            key={etapa.key}
            ref={(el) => {
              itemRefs.current[etapa.key] = el;
            }}
            className="absolute top-0 flex flex-col items-center text-xs"
            style={{
              left: `calc(${etapa.pct}% + ${offset}px)`,
              transform: 'translateX(-50%)',
            }}
          >
            <span className="h-2 w-px bg-border" aria-hidden="true" />
            <span className="mt-1 font-semibold tabular-nums text-foreground whitespace-nowrap">
              {etapa.pct.toFixed(1)}%
            </span>
            <span className={cn('font-medium whitespace-nowrap', etapa.text)}>{etapa.label}</span>
            <span className="text-muted-foreground tabular-nums whitespace-nowrap">
              {formatoMonto(etapa.monto)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default BarraEjecucion;