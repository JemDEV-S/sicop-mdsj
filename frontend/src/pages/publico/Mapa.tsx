import { useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  MapPin,
  Search,
  ListChecks,
  Info,
  X,
  HardHat,
  Clock,
  Layers,
} from 'lucide-react';
import MapaObras from '@/features/obras/MapaObras';
import { useObrasMapa } from '@/features/obras/hooks';
import { ErrorState } from '@/components/layout/ErrorState';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const ANIO_VIGENTE = 2026;
const ANOS_DISPONIBLES = [ANIO_VIGENTE, ANIO_VIGENTE - 1, ANIO_VIGENTE - 2, ANIO_VIGENTE - 3];
const ANO_TODOS = 'todos';

type FiltroEstadoMapa = 'activas' | 'cartera' | 'todas';

function formatoEntero(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  return new Intl.NumberFormat('es-PE').format(valor);
}

export default function Mapa() {
  const [ano, setAno] = useState<number | ''>(ANIO_VIGENTE);
  const [busqueda, setBusqueda] = useState('');
  const [mostrarAyuda, setMostrarAyuda] = useState(false);
  const [filtroEstado, setFiltroEstado] = useState<FiltroEstadoMapa>('activas');
  const bloqueMapaRef = useRef<HTMLDivElement>(null);

  const { data, isLoading, isError, refetch } = useObrasMapa(
    ano ? { ano } : {},
  );

  const itemsValidos = useMemo(
    () =>
      data?.items.filter(
        (obra) =>
          obra.latitud != null &&
          obra.longitud != null &&
          !(obra.latitud === 0 && obra.longitud === 0),
      ) ?? [],
    [data],
  );

  const { itemsActivos, itemsCartera } = useMemo(() => {
    const activos: typeof itemsValidos = [];
    const cartera: typeof itemsValidos = [];
    for (const obra of itemsValidos) {
      const esActiva =
        (obra.avance_fisico != null && Number(obra.avance_fisico) > 0) ||
        (obra.pim_anio_actual != null && Number(obra.pim_anio_actual) > 0);
      if (esActiva) {
        activos.push(obra);
      } else {
        cartera.push(obra);
      }
    }
    return { itemsActivos: activos, itemsCartera: cartera };
  }, [itemsValidos]);

  const itemsBase = useMemo(() => {
    if (filtroEstado === 'activas') return itemsActivos;
    if (filtroEstado === 'cartera') return itemsCartera;
    return itemsValidos;
  }, [filtroEstado, itemsActivos, itemsCartera, itemsValidos]);

  const itemsFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return itemsBase;
    return itemsBase.filter((obra) => {
      const nombre = (obra.nombre_inversion ?? '').toLowerCase();
      const codigo = obra.codigo_unico.toLowerCase();
      const funcion = (obra.funcion ?? '').toLowerCase();
      return nombre.includes(q) || codigo.includes(q) || funcion.includes(q);
    });
  }, [itemsBase, busqueda]);

  function desplazarABloqueMapa() {
    const bloque = bloqueMapaRef.current;
    if (!bloque) return;

    const offsetHeader = 80;
    const top = bloque.getBoundingClientRect().top + window.scrollY - offsetHeader;
    if (Math.abs(window.scrollY - top) < 24) return;

    window.scrollTo({
      top: Math.max(0, top),
      behavior: 'smooth',
    });
  }

  if (isError) {
    return (
      <div className="mx-auto max-w-6xl px-4 py-16 md:px-6">
        <ErrorState
          titulo="No se pudo cargar el mapa"
          descripcion="Ocurrió un error al consultar la ubicación de las obras."
          onReintentar={() => refetch()}
        />
      </div>
    );
  }

  return (
    <div className="bg-background">
      {/* Encabezado compacto */}
      <header className="border-b border-border bg-gradient-to-br from-card via-card to-primary/5">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-5 px-4 py-6 md:px-8 md:py-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-gradient-to-r from-primary/10 to-secondary/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary shadow-sm">
              <MapPin className="h-3 w-3" aria-hidden="true" />
              Mapa de Obras · {ano ? `Año ${ano}` : 'Todos los años'}
            </div>
            <h1 className="text-2xl font-bold leading-tight tracking-tight text-foreground md:text-3xl">
              ¿Dónde se están construyendo{' '}
              <span className="text-primary">las obras de mi distrito</span>?
            </h1>
            <p className="mt-2 text-sm text-muted-foreground md:text-[15px]">
              Explora cada obra pública de San Jerónimo sobre el territorio. Haz clic en
              un marcador para ver fotos y detalles del avance.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Select
              value={ano ? String(ano) : ANO_TODOS}
              onValueChange={(v) => setAno(v === ANO_TODOS ? '' : parseInt(v, 10))}
            >
              <SelectTrigger className="w-44" aria-label="Año fiscal">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANO_TODOS}>Todos los años</SelectItem>
                {ANOS_DISPONIBLES.map((a) => (
                  <SelectItem key={a} value={a.toString()}>
                    Ejercicio {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link to="/obras">
                <ListChecks className="h-4 w-4" aria-hidden="true" />
                Ver listado
              </Link>
            </Button>
          </div>
        </div>
      </header>

      {/* Mapa protagonista */}
      <main className="mx-auto max-w-[1600px] px-4 py-6 md:px-8 md:py-8">
        <div ref={bloqueMapaRef} className="relative">
          {/* Barra superior con selector de estado y herramientas */}
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            {/* Selector de pestañas: Obras activas (default) vs Cartera vs Todas */}
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <div
                className="inline-flex rounded-xl border border-border bg-muted/60 p-1 shadow-inner"
                role="tablist"
                aria-label="Filtro de obras por estado"
              >
                <button
                  type="button"
                  role="tab"
                  aria-selected={filtroEstado === 'activas'}
                  onClick={() => setFiltroEstado('activas')}
                  className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                    filtroEstado === 'activas'
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span className="flex h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <HardHat className="h-3.5 w-3.5" aria-hidden="true" />
                  <span>En Ejecución Activa</span>
                  <span
                    className={`ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                      filtroEstado === 'activas'
                        ? 'bg-primary-foreground/20 text-primary-foreground'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {formatoEntero(itemsActivos.length)}
                  </span>
                </button>

                <button
                  type="button"
                  role="tab"
                  aria-selected={filtroEstado === 'cartera'}
                  onClick={() => setFiltroEstado('cartera')}
                  className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                    filtroEstado === 'cartera'
                      ? 'bg-card text-foreground shadow-sm border border-border'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Clock className="h-3.5 w-3.5 text-slate-400" aria-hidden="true" />
                  <span>Proyectos en Cartera</span>
                  <span
                    className={`ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                      filtroEstado === 'cartera'
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {formatoEntero(itemsCartera.length)}
                  </span>
                </button>

                <button
                  type="button"
                  role="tab"
                  aria-selected={filtroEstado === 'todas'}
                  onClick={() => setFiltroEstado('todas')}
                  className={`inline-flex items-center gap-2 rounded-lg px-3.5 py-1.5 text-xs font-semibold transition-all ${
                    filtroEstado === 'todas'
                      ? 'bg-card text-foreground shadow-sm border border-border'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <Layers className="h-3.5 w-3.5 text-muted-foreground" aria-hidden="true" />
                  <span>Todas</span>
                  <span
                    className={`ml-0.5 rounded-full px-1.5 py-0.5 text-[10px] font-bold ${
                      filtroEstado === 'todas'
                        ? 'bg-primary/10 text-primary'
                        : 'bg-muted text-muted-foreground'
                    }`}
                  >
                    {formatoEntero(itemsValidos.length)}
                  </span>
                </button>
              </div>

              <div className="hidden items-center gap-1.5 text-[11px] text-muted-foreground sm:flex">
                <span className="h-1 w-1 rounded-full bg-muted-foreground/50" />
                <span>
                  {filtroEstado === 'activas' &&
                    'Obras con avances físicos y presupuesto en marcha'}
                  {filtroEstado === 'cartera' &&
                    'Proyectos aprobados en Invierte.pe en fase preparatoria'}
                  {filtroEstado === 'todas' &&
                    'Total de obras georreferenciadas en San Jerónimo'}
                </span>
              </div>
            </div>

            {/* Búsqueda y ayuda */}
            <div className="flex items-center gap-2 md:justify-end">
              <div className="relative flex-1 sm:w-72 md:w-80">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre, CUI o sector..."
                  className="h-9 pl-9 pr-8 text-xs bg-card shadow-sm hover:shadow-md focus-visible:ring-primary/30"
                  aria-label="Buscar obra en el mapa"
                />
                {busqueda ? (
                  <button
                    type="button"
                    onClick={() => setBusqueda('')}
                    className="absolute right-2 top-1/2 inline-flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Limpiar búsqueda"
                  >
                    <X className="h-3 w-3" />
                  </button>
                ) : null}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setMostrarAyuda((v) => !v)}
                aria-label="Cómo usar el mapa"
                aria-pressed={mostrarAyuda}
                className="h-9 w-9 shrink-0"
              >
                <Info className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>

          {/* Contenedor del mapa a pantalla casi completa */}
          <div className="relative h-[calc(100vh-16rem)] min-h-[600px] w-full">
            <MapaObras
              items={itemsFiltrados}
              isLoading={isLoading}
              height="100%"
              onSeleccionarMarcador={desplazarABloqueMapa}
            />

            {/* Card flotante de ayuda */}
            {mostrarAyuda ? (
              <div className="pointer-events-auto absolute bottom-6 left-6 z-[1000] w-[340px] max-w-[calc(100%-3rem)] rounded-2xl border border-border bg-gradient-to-br from-card via-card to-primary/5 p-5 shadow-xl ring-1 ring-black/5 animate-in fade-in slide-in-from-bottom-2 duration-200">
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary/20 via-primary/10 to-secondary/15 text-primary shadow-sm">
                      <Info className="h-4 w-4" aria-hidden="true" />
                    </span>
                    <h3 className="text-sm font-semibold text-foreground">Cómo usar el mapa</h3>
                  </div>
                  <button
                    type="button"
                    onClick={() => setMostrarAyuda(false)}
                    className="inline-flex h-6 w-6 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Cerrar ayuda"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
                <ul className="space-y-2.5 text-xs leading-relaxed text-muted-foreground">
                  <li className="flex gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-emerald-500" aria-hidden="true" />
                    <span>
                      <strong className="text-foreground">En Ejecución Activa:</strong> Muestra las obras con trabajos físicos y presupuesto devengado en marcha.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-slate-400" aria-hidden="true" />
                    <span>
                      <strong className="text-foreground">Proyectos en Cartera:</strong> Inversiones aprobadas en el Banco de Inversiones (Invierte.pe) en gestión de financiamiento para su ejecución física.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground" aria-hidden="true" />
                    <span>
                      <strong className="text-foreground">Haz clic en un marcador</strong> para ver fotos, porcentaje de avance reportado y ruta en Google Maps.
                    </span>
                  </li>
                </ul>
                <p className="mt-4 rounded-lg bg-gradient-to-r from-muted/60 to-primary/10 p-3 text-[11px] leading-relaxed text-muted-foreground">
                  El avance reportado corresponde a la ejecución física consolidada en los sistemas del Estado (SIAF e Invierte.pe).
                </p>
              </div>
            ) : null}

            {/* Estado vacío tras búsqueda */}
            {!isLoading && itemsFiltrados.length === 0 && busqueda ? (
              <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
                <div className="pointer-events-auto rounded-2xl border border-border bg-gradient-to-br from-card via-card to-primary/5 px-6 py-5 text-center shadow-lg">
                  <Search className="mx-auto mb-2 h-6 w-6 text-muted-foreground" aria-hidden="true" />
                  <p className="text-sm font-semibold text-foreground">Sin resultados</p>
                  <p className="mt-1 text-xs text-muted-foreground">
                    No encontramos obras que coincidan con "{busqueda}".
                  </p>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="mt-3"
                    onClick={() => setBusqueda('')}
                  >
                    Limpiar búsqueda
                  </Button>
                </div>
              </div>
            ) : null}
          </div>

          {/* Pie explicativo compacto */}
          <p className="mt-4 text-center text-xs text-muted-foreground">
            Los datos se actualizan diariamente desde el sistema SIAF del MEF y el
            Banco de Inversiones. Las obras sin ubicación registrada aparecen en el{' '}
            <Link to="/obras" className="font-semibold text-primary hover:underline">
              listado completo de obras
            </Link>
            .
          </p>
        </div>
      </main>
    </div>
  );
}
