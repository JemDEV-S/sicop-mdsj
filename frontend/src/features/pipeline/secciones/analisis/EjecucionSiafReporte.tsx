// Reporte de ejecución SIAF — lo que la API MEF no puede dar (RUC, clasificador
// de 5 niveles, girado/pagado por documento). Pivotea las fases del ciclo de
// gasto (Certificado/Devengado/Girado/Pagado) por proveedor, clasificador o
// fuente. Datos del Formato A: carga PROVISIONAL, nunca un total de tablero
// (RN §3) — se rotula como tal y respeta el alcance por CC del usuario.
//
// Herramientas de trabajo (todas operan en cliente sobre las filas ya traídas,
// sin endpoint nuevo ni datos inventados): buscar, ordenar por columna, ver la
// participación de cada fila sobre el total de su fase, y descargar el
// subconjunto visible como CSV.

import { useMemo, useState } from 'react';
import { ArrowDown, ArrowUp, ChevronsUpDown, Download, Search } from 'lucide-react';
import { formatearMoneda, formatearNumero } from '@/lib/formatters';
import { cn } from '@/lib/utils';
import { useEjecucionSiafAgregada } from '@/features/pipeline/api';
import type { EjecucionAgregadaSiaf, FilaEjecucionAgregada } from '@/features/pipeline/types';
import { selloDetalleSiaf } from '@/features/pipeline/siaf-cobertura';
import { TileFase } from '@/features/panel/ui/primitivas';
import { usePaginado, Paginacion } from './Paginacion';

type Dimension = 'proveedor' | 'clasificador' | 'rubro';

// Columnas numéricas ordenables (la etiqueta es la 1.ª, no numérica).
type CampoOrden = 'devengado' | 'girado' | 'pagado' | 'en_transito' | 'n_expedientes' | 'n_metas';

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
              'text-dato rounded-md border px-3 py-1.5 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              dim === d.cod
                ? 'border-primary bg-primary text-primary-foreground'
                : 'border-border bg-card text-foreground hover:bg-muted',
            )}
          >
            {d.label}
          </button>
        ))}
        <span className="text-dato text-muted-foreground">
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
        <ContenidoEjecucion dim={dim} data={data} />
      )}
    </div>
  );
}

// El cuerpo con las herramientas (búsqueda/orden/descarga) se separa para que
// su estado se reinicie al cambiar de dimensión o de alcance (remonta por key).
function ContenidoEjecucion({ dim, data }: { dim: Dimension; data: EjecucionAgregadaSiaf }) {
  const [busqueda, setBusqueda] = useState('');
  const [orden, setOrden] = useState<CampoOrden>('devengado');
  const [dir, setDir] = useState<'asc' | 'desc'>('desc');

  const toggleOrden = (campo: CampoOrden) => {
    if (campo === orden) {
      setDir((d) => (d === 'desc' ? 'asc' : 'desc'));
    } else {
      setOrden(campo);
      setDir('desc');
    }
  };

  // Filtrado por texto (nombre/RUC/clasificador/fuente) + orden por la columna
  // elegida. Todo en cliente sobre las filas ya traídas.
  const filas = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    const base = q ? data.filas.filter((f) => textoDeFila(dim, f).includes(q)) : data.filas;
    const factor = dir === 'desc' ? -1 : 1;
    return [...base].sort((a, b) => (a[orden] - b[orden]) * factor);
  }, [data.filas, dim, busqueda, orden, dir]);

  // Totales del subconjunto visible: dan feedback al buscar/filtrar y son la
  // base del % de participación por fila (no se repiten con los TileFase, que
  // muestran el total del año completo).
  const totalDevengadoFiltrado = useMemo(
    () => filas.reduce((s, f) => s + f.devengado, 0),
    [filas],
  );

  const filtrando = busqueda.trim().length > 0;

  return (
    <>
      <TotalesPorFase totales={data.totales_por_fase} />

      <div className="flex flex-wrap items-center gap-2">
        <div className="flex min-w-[240px] flex-1 items-center gap-2 rounded-md border border-border bg-superficie-alt-2 px-3 py-2">
          <Search className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
          <input
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder={placeholderBusqueda(dim)}
            aria-label={placeholderBusqueda(dim)}
            className="text-dato min-w-0 flex-1 bg-transparent text-foreground outline-none placeholder:text-muted-foreground"
          />
        </div>
        <button
          type="button"
          onClick={() => descargarCsv(dim, filas)}
          disabled={filas.length === 0}
          className={cn(
            'text-dato inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-2 font-medium text-foreground transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
            filas.length === 0 ? 'cursor-not-allowed opacity-40' : 'hover:bg-muted',
          )}
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Descargar
        </button>
      </div>

      <TablaAgregada
        dim={dim}
        filas={filas}
        orden={orden}
        dir={dir}
        onOrdenar={toggleOrden}
        totalDevengado={totalDevengadoFiltrado}
        filtrando={filtrando}
      />

      <p className="text-microdato leading-relaxed text-muted-foreground">
        {selloDetalleSiaf(data.meses_cargados)}. Explica el gasto (quién, qué, cuánto
        por fase); no reemplaza los totales oficiales del MEF. «En tránsito» =
        devengado − pagado (dinero comprometido que aún no salió de caja). «Part.» =
        participación de la fila en el devengado del{' '}
        {filtrando ? 'subconjunto filtrado' : 'año'}.
      </p>
    </>
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

function TablaAgregada({
  dim,
  filas,
  orden,
  dir,
  onOrdenar,
  totalDevengado,
  filtrando,
}: {
  dim: Dimension;
  filas: FilaEjecucionAgregada[];
  orden: CampoOrden;
  dir: 'asc' | 'desc';
  onOrdenar: (campo: CampoOrden) => void;
  totalDevengado: number;
  filtrando: boolean;
}) {
  const paginado = usePaginado(filas);
  if (filas.length === 0) {
    return (
      <EstadoCaja
        texto={
          filtrando
            ? 'Ningún registro coincide con la búsqueda. Probá con otro nombre, RUC o clasificador.'
            : 'No hay ejecución SIAF para el alcance seleccionado.'
        }
      />
    );
  }
  const etiquetaCol = dim === 'proveedor' ? 'Proveedor' : dim === 'clasificador' ? 'Clasificador' : 'Fuente';
  return (
    <div className="overflow-hidden rounded-md border border-border">
      <div className="overflow-x-auto">
        <table className="text-dato w-full min-w-[860px] border-collapse">
          <thead>
            <tr className="bg-superficie-alt text-left text-texto-suave">
              <Th>{etiquetaCol}</Th>
              <ThOrden campo="devengado" orden={orden} dir={dir} onOrdenar={onOrdenar}>Devengado</ThOrden>
              <Th className="text-right">Part.</Th>
              <ThOrden campo="girado" orden={orden} dir={dir} onOrdenar={onOrdenar}>Girado</ThOrden>
              <ThOrden campo="pagado" orden={orden} dir={dir} onOrdenar={onOrdenar}>Pagado</ThOrden>
              <ThOrden campo="en_transito" orden={orden} dir={dir} onOrdenar={onOrdenar}>En tránsito</ThOrden>
              <ThOrden campo="n_expedientes" orden={orden} dir={dir} onOrdenar={onOrdenar}>Exp.</ThOrden>
              <ThOrden campo="n_metas" orden={orden} dir={dir} onOrdenar={onOrdenar}>Metas</ThOrden>
            </tr>
          </thead>
          <tbody>
            {paginado.pagina.map((f, i) => {
              const part = totalDevengado > 0 ? (f.devengado / totalDevengado) * 100 : 0;
              return (
                <tr key={etiquetaFila(dim, f) + i} className="border-b border-border/60 hover:bg-superficie-alt">
                  <Td>
                    <div className="flex flex-col gap-0.5">
                      <span className="max-w-[280px] truncate text-foreground" title={etiquetaFila(dim, f)}>
                        {etiquetaFila(dim, f)}
                      </span>
                      {dim === 'proveedor' && f.proveedor_ruc ? (
                        <span className="text-microdato text-muted-foreground">RUC {f.proveedor_ruc}</span>
                      ) : null}
                    </div>
                  </Td>
                  <Td className="text-right font-mono tabular-nums">{formatearMoneda(f.devengado)}</Td>
                  <Td>
                    <BarraParticipacion pct={part} />
                  </Td>
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
              );
            })}
          </tbody>
        </table>
      </div>
      <Paginacion
        paginado={paginado}
        etiqueta={dim === 'proveedor' ? 'proveedores' : dim === 'clasificador' ? 'clasificadores' : 'fuentes'}
      />
    </div>
  );
}

// Participación de la fila sobre el devengado del subconjunto: mini-barra + %.
// Dato nuevo (no está en el snapshot MEF ni se repite en otra columna).
function BarraParticipacion({ pct }: { pct: number }) {
  const w = Math.min(100, Math.max(0, pct));
  return (
    <div className="flex items-center gap-2" title={`${formatearNumero(pct, 1)}% del devengado`}>
      <div className="h-2 w-16 shrink-0 overflow-hidden rounded bg-muted">
        <div className="h-full rounded bg-secondary" style={{ width: `${w}%` }} />
      </div>
      <span className="w-10 shrink-0 text-right font-mono text-[11px] tabular-nums text-muted-foreground">
        {pct >= 0.1 ? `${formatearNumero(pct, 1)}%` : '—'}
      </span>
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

// Texto sobre el que busca el filtro: la etiqueta visible + el RUC del proveedor.
function textoDeFila(dim: Dimension, f: FilaEjecucionAgregada): string {
  const base = etiquetaFila(dim, f).toLowerCase();
  return dim === 'proveedor' && f.proveedor_ruc ? `${base} ${f.proveedor_ruc}` : base;
}

function placeholderBusqueda(dim: Dimension): string {
  if (dim === 'proveedor') return 'Buscar proveedor por nombre o RUC';
  if (dim === 'clasificador') return 'Buscar clasificador (código o nombre)';
  return 'Buscar fuente de financiamiento';
}

function Th({ children, className }: { children: React.ReactNode; className?: string }) {
  return <th className={cn('text-etiqueta whitespace-nowrap px-3 py-2', className)}>{children}</th>;
}

// Encabezado clicable que ordena por su columna, con indicador de dirección.
function ThOrden({
  campo,
  orden,
  dir,
  onOrdenar,
  children,
}: {
  campo: CampoOrden;
  orden: CampoOrden;
  dir: 'asc' | 'desc';
  onOrdenar: (campo: CampoOrden) => void;
  children: React.ReactNode;
}) {
  const activo = campo === orden;
  const Icono = !activo ? ChevronsUpDown : dir === 'desc' ? ArrowDown : ArrowUp;
  return (
    <th className="text-etiqueta whitespace-nowrap px-3 py-2 text-right">
      <button
        type="button"
        onClick={() => onOrdenar(campo)}
        aria-label={`Ordenar por ${children} ${activo && dir === 'desc' ? 'ascendente' : 'descendente'}`}
        className={cn(
          'ml-auto inline-flex items-center gap-1 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
          activo ? 'text-primary' : 'text-texto-suave hover:text-foreground',
        )}
      >
        {children}
        <Icono className="h-3 w-3 shrink-0" aria-hidden="true" />
      </button>
    </th>
  );
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

// ─── Descarga CSV del subconjunto visible ────────────────────────────────
//
// Sin librería externa: arma el CSV a mano (comillas escapadas) y dispara la
// descarga con un blob. El nombre dice qué dimensión y año trae. Los montos van
// con punto decimal para que Excel/Sheets los tome como número.

function descargarCsv(dim: Dimension, filas: FilaEjecucionAgregada[]) {
  if (filas.length === 0) return;
  const etiquetaCol = dim === 'proveedor' ? 'Proveedor' : dim === 'clasificador' ? 'Clasificador' : 'Fuente';
  const cab = dim === 'proveedor'
    ? ['RUC', etiquetaCol, 'Certificado', 'Devengado', 'Girado', 'Pagado', 'En transito', 'Expedientes', 'Metas']
    : [etiquetaCol, 'Certificado', 'Devengado', 'Girado', 'Pagado', 'En transito', 'Expedientes', 'Metas'];
  const filasCsv = filas.map((f) => {
    const num = [f.certificado, f.devengado, f.girado, f.pagado, f.en_transito, f.n_expedientes, f.n_metas];
    return dim === 'proveedor'
      ? [f.proveedor_ruc ?? '', etiquetaFila(dim, f), ...num]
      : [etiquetaFila(dim, f), ...num];
  });
  const lineas = [cab, ...filasCsv].map((cols) => cols.map(celdaCsv).join(',')).join('\r\n');
  // BOM para que Excel reconozca UTF-8 (tildes y ñ).
  const blob = new Blob(['﻿' + lineas], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ejecucion-siaf-${dim}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function celdaCsv(valor: string | number): string {
  const s = String(valor);
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
