// Reporte de ejecución SIAF — lo que la API MEF no puede dar (RUC, clasificador
// de 5 niveles, girado/pagado por documento). Pivotea las fases del ciclo de
// gasto (Certificado/Devengado/Girado/Pagado) por proveedor, clasificador o
// fuente. Datos del Formato A: carga PROVISIONAL, nunca un total de tablero
// (RN §3) — se rotula como tal y respeta el alcance por CC del usuario.

import { useState } from 'react';
import { formatearMoneda } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useEjecucionSiafAgregada } from '@/features/pipeline/api';
import type { FilaEjecucionAgregada } from '@/features/pipeline/types';
import { selloDetalleSiaf } from '@/features/pipeline/siaf-cobertura';
import { TileFase } from '@/features/panel/ui/primitivas';
import { usePaginado, Paginacion } from './Paginacion';

type Dimension = 'proveedor' | 'clasificador' | 'rubro';

const DIMENSIONES: { cod: Dimension; label: string; ayuda: string }[] = [
  { cod: 'proveedor', label: 'Por proveedor', ayuda: '¿A quién le pagamos y cuánto?' },
  { cod: 'clasificador', label: 'Por clasificador', ayuda: 'Gasto por específica (5 niveles).' },
  { cod: 'rubro', label: 'Por fuente', ayuda: 'FONCOMUN, Canon, RDR, Impuestos…' },
];

export default function EjecucionSiafReporte() {
  const [dim, setDim] = useState<Dimension>('proveedor');
  const { data, isLoading, isError } = useEjecucionSiafAgregada(dim);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        {DIMENSIONES.map((d) => (
          <button
            key={d.cod}
            type="button"
            onClick={() => setDim(d.cod)}
            className={cn(
              'rounded-md border px-3 py-1.5 text-[12.5px] transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              dim === d.cod
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-foreground hover:bg-muted',
            )}
          >
            {d.label}
          </button>
        ))}
        <span className="text-[11.5px] text-muted-foreground">
          {DIMENSIONES.find((d) => d.cod === dim)?.ayuda}
        </span>
      </div>

      {isLoading ? (
        <EstadoCaja texto="Cargando ejecución SIAF…" />
      ) : isError ? (
        <EstadoCaja texto="No se pudo cargar la ejecución SIAF. Intentá de nuevo más tarde." />
      ) : !data?.tiene_datos ? (
        <EstadoCaja texto="Aún no se ha cargado el Formato A del SIAF para este año. Un administrador puede subirlo para ver la ejecución por proveedor, clasificador o fuente." />
      ) : (
        <>
          <TotalesPorFase totales={data.totales_por_fase} />
          <TablaAgregada dim={dim} filas={data.filas} />
          <p className="text-[10.5px] leading-relaxed text-muted-foreground">
            {selloDetalleSiaf(data.meses_cargados)}. Explica el gasto (quién, qué, cuánto
            por fase); no reemplaza los totales oficiales del MEF. «En tránsito» =
            devengado − pagado (dinero comprometido que aún no salió de caja).
          </p>
        </>
      )}
    </div>
  );
}

function TotalesPorFase({ totales }: { totales: Record<string, number> }) {
  const tiles: { cod: string; label: string }[] = [
    { cod: 'C', label: 'Certificado' },
    { cod: 'D', label: 'Devengado' },
    { cod: 'G', label: 'Girado' },
    { cod: 'P', label: 'Pagado' },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
      {tiles.map((t) => (
        <TileFase key={t.cod} label={t.label} valor={formatearMoneda(totales[t.cod] ?? 0)} />
      ))}
    </div>
  );
}

function TablaAgregada({ dim, filas }: { dim: Dimension; filas: FilaEjecucionAgregada[] }) {
  const paginado = usePaginado(filas);
  if (filas.length === 0) {
    return <EstadoCaja texto="No hay ejecución SIAF para el alcance seleccionado." />;
  }
  return (
    <div className="rounded-md border border-border">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[820px] border-collapse text-[12.5px]">
          <thead>
            <tr className="bg-superficie-alt text-left text-[11px] uppercase tracking-wide text-texto-suave">
              <Th>{dim === 'proveedor' ? 'Proveedor' : dim === 'clasificador' ? 'Clasificador' : 'Fuente'}</Th>
              <Th className="text-right">Devengado</Th>
              <Th className="text-right">Girado</Th>
              <Th className="text-right">Pagado</Th>
              <Th className="text-right">En tránsito</Th>
              <Th className="text-right">Exp.</Th>
              <Th className="text-right">Metas</Th>
            </tr>
          </thead>
          <tbody>
            {paginado.pagina.map((f, i) => (
              <tr key={etiquetaFila(dim, f) + i} className="border-b border-border/60">
                <Td>
                  <div className="flex flex-col gap-0.5">
                    <span className="max-w-[280px] truncate text-foreground" title={etiquetaFila(dim, f)}>
                      {etiquetaFila(dim, f)}
                    </span>
                    {dim === 'proveedor' && f.proveedor_ruc ? (
                      <span className="font-mono text-[11px] text-muted-foreground">RUC {f.proveedor_ruc}</span>
                    ) : null}
                  </div>
                </Td>
                <Td className="text-right font-mono tabular-nums">{formatearMoneda(f.devengado)}</Td>
                <Td className="text-right font-mono tabular-nums">{formatearMoneda(f.girado)}</Td>
                <Td className="text-right font-mono tabular-nums">{formatearMoneda(f.pagado)}</Td>
                <Td
                  className={cn(
                    'text-right font-mono tabular-nums',
                    f.en_transito > 0 ? 'text-accent-foreground' : 'text-muted-foreground',
                  )}
                >
                  {formatearMoneda(f.en_transito)}
                </Td>
                <Td className="text-right font-mono tabular-nums text-muted-foreground">{f.n_expedientes}</Td>
                <Td className="text-right font-mono tabular-nums text-muted-foreground">{f.n_metas}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Paginacion paginado={paginado} etiqueta={dim === 'proveedor' ? 'proveedores' : dim === 'clasificador' ? 'clasificadores' : 'fuentes'} />
    </div>
  );
}

function etiquetaFila(dim: Dimension, f: FilaEjecucionAgregada): string {
  if (dim === 'proveedor') return f.proveedor_nombre?.trim() || 'Sin proveedor';
  if (dim === 'clasificador') return f.clasificador?.trim() || 'Sin clasificador';
  const cod = f.rubro?.trim();
  const nombre = f.rubro_nombre?.trim();
  return nombre ? `${cod ?? ''} ${nombre}`.trim() : cod || 'Sin fuente';
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('whitespace-nowrap px-3 py-2 font-semibold', className)}>{children}</th>;
}

function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2 align-middle', className)}>{children}</td>;
}

function EstadoCaja({ texto }: { texto: string }) {
  return (
    <div className="rounded-md border border-border px-4 py-10 text-center text-sm leading-relaxed text-muted-foreground">
      {texto}
    </div>
  );
}
