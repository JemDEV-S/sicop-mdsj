import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  MapPin,
  Search,
  ListChecks,
  Info,
  X,
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

function formatoEntero(valor: number | null | undefined): string {
  if (valor === null || valor === undefined) return '—';
  return new Intl.NumberFormat('es-PE').format(valor);
}

export default function Mapa() {
  const [ano, setAno] = useState<number | ''>(ANIO_VIGENTE);
  const [busqueda, setBusqueda] = useState('');
  const [mostrarAyuda, setMostrarAyuda] = useState(false);

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

  const itemsFiltrados = useMemo(() => {
    const q = busqueda.trim().toLowerCase();
    if (!q) return itemsValidos;
    return itemsValidos.filter((obra) => {
      const nombre = (obra.nombre_inversion ?? '').toLowerCase();
      const codigo = obra.codigo_unico.toLowerCase();
      const funcion = (obra.funcion ?? '').toLowerCase();
      return nombre.includes(q) || codigo.includes(q) || funcion.includes(q);
    });
  }, [itemsValidos, busqueda]);

  const totalConCoords = itemsValidos.length;
  const totalSinCoords = data?.total_sin_coords ?? 0;

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
      <header className="border-b border-border bg-card">
        <div className="mx-auto flex max-w-[1600px] flex-col gap-5 px-4 py-6 md:px-8 md:py-8 lg:flex-row lg:items-end lg:justify-between">
          <div className="max-w-2xl">
            <div className="mb-2 inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/5 px-3 py-1 text-[11px] font-semibold uppercase tracking-wide text-primary">
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
        <div className="relative">
          {/* Barra superior sobre el mapa */}
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-2.5 shadow-sm">
              <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <MapPin className="h-4 w-4" aria-hidden="true" />
              </span>
              <div>
                <p className="text-sm font-bold leading-tight tabular-nums text-foreground">
                  {formatoEntero(itemsFiltrados.length)}{' '}
                  <span className="font-normal text-muted-foreground">
                    {itemsFiltrados.length === 1 ? 'obra visible' : 'obras visibles'}
                  </span>
                </p>
                <p className="text-[11px] leading-tight text-muted-foreground">
                  {busqueda
                    ? `Filtradas de ${formatoEntero(totalConCoords)} obras ubicadas`
                    : totalSinCoords > 0
                      ? `${formatoEntero(totalSinCoords)} obras aún no tienen coordenadas registradas`
                      : 'Todas las obras cuentan con ubicación registrada'}
                </p>
              </div>
            </div>

            <div className="flex flex-1 items-center gap-2 md:justify-end">
              <div className="relative flex-1 md:max-w-md">
                <Search
                  className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                  aria-hidden="true"
                />
                <Input
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                  placeholder="Buscar por nombre, código o sector"
                  className="h-10 pl-9 pr-9"
                  aria-label="Buscar obra en el mapa"
                />
                {busqueda ? (
                  <button
                    type="button"
                    onClick={() => setBusqueda('')}
                    className="absolute right-2 top-1/2 inline-flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-muted-foreground hover:bg-muted hover:text-foreground"
                    aria-label="Limpiar búsqueda"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                ) : null}
              </div>
              <Button
                variant="outline"
                size="icon"
                onClick={() => setMostrarAyuda((v) => !v)}
                aria-label="Cómo usar el mapa"
                aria-pressed={mostrarAyuda}
                className="h-10 w-10 shrink-0"
              >
                <Info className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>

          {/* Contenedor del mapa a pantalla casi completa */}
          <div className="relative h-[calc(100vh-16rem)] min-h-[600px] w-full">
            <MapaObras items={itemsFiltrados} isLoading={isLoading} height="100%" />

            {/* Card flotante de ayuda */}
            {mostrarAyuda ? (
              <div className="pointer-events-auto absolute bottom-6 left-6 z-[1000] w-[320px] max-w-[calc(100%-3rem)] rounded-2xl border border-border bg-card p-5 shadow-xl ring-1 ring-black/5 animate-in fade-in slide-in-from-bottom-2 duration-200">
                <div className="mb-3 flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="inline-flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
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
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground" aria-hidden="true" />
                    <span>
                      <strong className="text-foreground">Haz clic en un marcador</strong> para
                      ver fotos, avance actual y el nombre completo de la obra.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground" aria-hidden="true" />
                    <span>
                      <strong className="text-foreground">Acércate con el zoom</strong> (esquina
                      superior izquierda) para encontrar obras cerca de tu barrio.
                    </span>
                  </li>
                  <li className="flex gap-2">
                    <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-foreground" aria-hidden="true" />
                    <span>
                      Desde cada popup puedes abrir la <strong className="text-foreground">ficha completa</strong>{' '}
                      con presupuesto, cronograma y documentos.
                    </span>
                  </li>
                </ul>
                <p className="mt-4 rounded-lg bg-muted/50 p-3 text-[11px] leading-relaxed text-muted-foreground">
                  Cada obra tiene su propio ritmo. El porcentaje mostrado es el avance físico
                  reportado; no compara obras entre sí porque cada una tiene una complejidad y
                  duración distintas.
                </p>
              </div>
            ) : null}

            {/* Estado vacío tras búsqueda */}
            {!isLoading && itemsFiltrados.length === 0 && busqueda ? (
              <div className="pointer-events-none absolute inset-0 z-[1000] flex items-center justify-center">
                <div className="pointer-events-auto rounded-2xl border border-border bg-card px-6 py-5 text-center shadow-lg">
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
