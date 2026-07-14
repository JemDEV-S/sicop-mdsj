import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Download,
  Target,
  Coins,
  Package,
  X,
  Search,
  LayoutDashboard,
} from 'lucide-react';
import {
  useEjecucionDetalle,
  useExportarEjecucionPublico,
  useEjecucionPorFuncion,
  useEjecucionPorFuente,
  useEjecucionPorRubro,
  useEjecucionPorGenerica,
} from '@/features/ejecucion/hooks';
import { TablaMetas, type SortKey } from '@/features/ejecucion/secciones/TablaMetas';
import { PublicHero } from '@/components/publico/PublicHero';
import { SectionBand } from '@/components/publico/SectionBand';
import { ChipFiltroIntencion } from '@/components/publico/ChipFiltroIntencion';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const ANIO_VIGENTE = 2026;
const ANOS_DISPONIBLES = [ANIO_VIGENTE, ANIO_VIGENTE - 1, ANIO_VIGENTE - 2, ANIO_VIGENTE - 3];

interface FiltrosState {
  ano: number;
  funcion: string;
  categoria_gasto: string;
  fuente: string;
  rubro: string;
  generica: string;
  busqueda: string;
}

const FILTROS_VACIOS: FiltrosState = {
  ano: ANIO_VIGENTE,
  funcion: '',
  categoria_gasto: '',
  fuente: '',
  rubro: '',
  generica: '',
  busqueda: '',
};

type PanelAbierto = null | 'para-que' | 'de-donde' | 'en-que';

export default function EjecucionDetalle() {
  const [filtros, setFiltros] = useState<FiltrosState>(FILTROS_VACIOS);
  const [filtrosAplicados, setFiltrosAplicados] = useState<FiltrosState>(FILTROS_VACIOS);
  const [panelAbierto, setPanelAbierto] = useState<PanelAbierto>(null);
  const [pagination, setPagination] = useState({ pageIndex: 0, pageSize: 10 });
  const [sortKey, setSortKey] = useState<SortKey>('pim');

  // Mapeo del sortKey ciudadano al parámetro que espera el backend.
  const sortBackend = useMemo(() => {
    switch (sortKey) {
      case 'devengado':
        return 'devengado_desc';
      case 'pct_desc':
      case 'pct_asc':
        // Backend no soporta ordenar por % ejecución directamente.
        // Aproximamos con PIM y ordenamos client-side en la página actual.
        return 'pim_desc';
      case 'pim':
      default:
        return 'pim_desc';
    }
  }, [sortKey]);

  // Debounce solo para búsqueda de texto (300ms).
  useEffect(() => {
    const t = setTimeout(() => {
      setFiltrosAplicados((prev) => ({ ...prev, busqueda: filtros.busqueda }));
      setPagination((p) => ({ ...p, pageIndex: 0 }));
    }, 300);
    return () => clearTimeout(t);
  }, [filtros.busqueda]);

  // Al cambiar año, sincroniza también los aplicados.
  useEffect(() => {
    setFiltrosAplicados((prev) => ({ ...prev, ano: filtros.ano }));
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  }, [filtros.ano]);

  // Catálogos para los selects (dependen del año)
  const { data: funciones } = useEjecucionPorFuncion({ ano: filtrosAplicados.ano });
  const { data: fuentes } = useEjecucionPorFuente({ ano: filtrosAplicados.ano });
  const { data: rubros } = useEjecucionPorRubro({ ano: filtrosAplicados.ano });
  const { data: genericas } = useEjecucionPorGenerica({ ano: filtrosAplicados.ano });

  // Query principal
  const { data, isLoading, isError } = useEjecucionDetalle({
    ano: filtrosAplicados.ano,
    funcion: filtrosAplicados.funcion || undefined,
    fuente: filtrosAplicados.fuente || undefined,
    rubro: filtrosAplicados.rubro || undefined,
    generica: filtrosAplicados.generica || undefined,
    categoria_gasto: filtrosAplicados.categoria_gasto || undefined,
    page: pagination.pageIndex + 1,
    size: pagination.pageSize,
    sort: sortBackend,
  });

  // Filtrado por búsqueda de texto y ordenamiento client-side por %.
  const itemsFiltrados = useMemo(() => {
    let items = data?.items ?? [];
    const q = filtrosAplicados.busqueda.trim().toLowerCase();
    if (q) {
      items = items.filter(
        (it) =>
          it.meta_nombre?.toLowerCase().includes(q) ||
          it.funcion_nombre?.toLowerCase().includes(q) ||
          it.producto_proyecto_nombre?.toLowerCase().includes(q),
      );
    }
    // Backend no ordena por %; lo reordenamos client-side dentro de la página.
    if (sortKey === 'pct_desc' || sortKey === 'pct_asc') {
      items = [...items].sort((a, b) => {
        const pa = parseFloat(a.porcentaje_ejecucion ?? '0') || 0;
        const pb = parseFloat(b.porcentaje_ejecucion ?? '0') || 0;
        return sortKey === 'pct_desc' ? pb - pa : pa - pb;
      });
    }
    return items;
  }, [data, filtrosAplicados.busqueda, sortKey]);

  const { exportar } = useExportarEjecucionPublico();

  const aplicarFiltros = () => {
    setFiltrosAplicados({ ...filtros });
    setPagination((p) => ({ ...p, pageIndex: 0 }));
    setPanelAbierto(null);
  };

  const limpiarBloque = (bloque: PanelAbierto) => {
    if (bloque === 'para-que') {
      const nuevos = { ...filtros, funcion: '', categoria_gasto: '' };
      setFiltros(nuevos);
      setFiltrosAplicados((prev) => ({ ...prev, funcion: '', categoria_gasto: '' }));
    } else if (bloque === 'de-donde') {
      const nuevos = { ...filtros, fuente: '', rubro: '' };
      setFiltros(nuevos);
      setFiltrosAplicados((prev) => ({ ...prev, fuente: '', rubro: '' }));
    } else if (bloque === 'en-que') {
      const nuevos = { ...filtros, generica: '' };
      setFiltros(nuevos);
      setFiltrosAplicados((prev) => ({ ...prev, generica: '' }));
    }
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  };

  const limpiarTodo = () => {
    setFiltros({ ...FILTROS_VACIOS, ano: filtros.ano });
    setFiltrosAplicados({ ...FILTROS_VACIOS, ano: filtros.ano });
    setPagination((p) => ({ ...p, pageIndex: 0 }));
  };

  const handleExport = () => {
    exportar({
      ano: filtrosAplicados.ano,
      funcion: filtrosAplicados.funcion || undefined,
      fuente: filtrosAplicados.fuente || undefined,
      rubro: filtrosAplicados.rubro || undefined,
      generica: filtrosAplicados.generica || undefined,
      categoria_gasto: filtrosAplicados.categoria_gasto || undefined,
    });
  };

  const pageCount = data ? Math.ceil(data.total / data.size) : -1;

  // Etiquetas de filtros aplicados (para mostrar dentro de cada chip)
  const funNombre = funciones?.find((f) => f.funcion_codigo === filtrosAplicados.funcion)?.funcion_nombre;
  const fueNombre = fuentes?.find((f) => f.fuente_codigo === filtrosAplicados.fuente)?.fuente_nombre;
  const rubNombre = rubros?.find((r) => r.rubro_codigo === filtrosAplicados.rubro)?.rubro_nombre;
  const genNombre = genericas?.find((g) => g.generica_codigo === filtrosAplicados.generica)?.generica_nombre;
  const catNombre =
    filtrosAplicados.categoria_gasto === '5'
      ? 'Gasto Corriente'
      : filtrosAplicados.categoria_gasto === '6'
        ? 'Gasto de Capital'
        : null;

  const paraQueAplicados = [funNombre, catNombre].filter(Boolean) as string[];
  const deDondeAplicados = [fueNombre, rubNombre].filter(Boolean) as string[];
  const enQueAplicados = [genNombre].filter(Boolean) as string[];
  const totalFiltrosActivos =
    paraQueAplicados.length + deDondeAplicados.length + enQueAplicados.length;

  return (
    <div className="bg-background">
      <PublicHero
        eyebrow={<>Metas presupuestales · Año {filtrosAplicados.ano}</>}
        titulo={
          <>
            El detalle: <span className="text-primary">meta por meta</span>
          </>
        }
        subtitulo="Filtra por lo que te interesa saber y explora cada meta con su ejecución. Aquí encontrarás la fila más fina del gasto público municipal."
        compacto
        acciones={
          <>
            <Select
              value={filtros.ano.toString()}
              onValueChange={(v) => setFiltros((prev) => ({ ...prev, ano: parseInt(v, 10) }))}
            >
              <SelectTrigger className="w-40" aria-label="Año fiscal">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ANOS_DISPONIBLES.map((a) => (
                  <SelectItem key={a} value={a.toString()}>
                    Ejercicio {a}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button asChild variant="outline">
              <Link to="/ejecucion">
                <LayoutDashboard className="w-4 h-4" aria-hidden="true" />
                Ver dashboard
              </Link>
            </Button>
            <Button onClick={handleExport} variant="outline">
              <Download className="w-4 h-4" aria-hidden="true" />
              Exportar Excel
            </Button>
          </>
        }
      />

      {/* CHIPS DE FILTROS POR INTENCIÓN */}
      <SectionBand tono="muted" denso>
        <div className="mb-5 flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold uppercase tracking-[0.15em] text-primary mb-1">
              Filtra por lo que quieres saber
            </p>
            <p className="text-sm text-muted-foreground">
              Toca cada tarjeta para elegir tus filtros. Puedes combinar los tres.
            </p>
          </div>
          {totalFiltrosActivos > 0 ? (
            <Button variant="ghost" size="sm" onClick={limpiarTodo}>
              <X className="w-4 h-4" aria-hidden="true" />
              Quitar todos los filtros ({totalFiltrosActivos})
            </Button>
          ) : null}
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <ChipFiltroIntencion
            icono={Target}
            titulo="¿Para qué?"
            descripcion="Sector y tipo de gasto (corriente / capital)"
            aplicados={paraQueAplicados}
            activo={paraQueAplicados.length > 0}
            acento="primary"
            onAbrir={() => setPanelAbierto('para-que')}
            onLimpiar={paraQueAplicados.length > 0 ? () => limpiarBloque('para-que') : undefined}
          />
          <ChipFiltroIntencion
            icono={Coins}
            titulo="¿De dónde?"
            descripcion="Fuente y rubro del dinero"
            aplicados={deDondeAplicados}
            activo={deDondeAplicados.length > 0}
            acento="secondary"
            onAbrir={() => setPanelAbierto('de-donde')}
            onLimpiar={deDondeAplicados.length > 0 ? () => limpiarBloque('de-donde') : undefined}
          />
          <ChipFiltroIntencion
            icono={Package}
            titulo="¿En qué se gasta?"
            descripcion="Genérica (Personal, Bienes, Obras...)"
            aplicados={enQueAplicados}
            activo={enQueAplicados.length > 0}
            acento="accent"
            onAbrir={() => setPanelAbierto('en-que')}
            onLimpiar={enQueAplicados.length > 0 ? () => limpiarBloque('en-que') : undefined}
          />
        </div>

        {/* Buscador */}
        <div className="mt-6 relative max-w-2xl">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none"
            aria-hidden="true"
          />
          <Input
            type="search"
            placeholder="Buscar por nombre de meta, producto o sector..."
            value={filtros.busqueda}
            onChange={(e) => setFiltros((prev) => ({ ...prev, busqueda: e.target.value }))}
            className="pl-10"
            aria-label="Buscar metas"
          />
        </div>
      </SectionBand>

      {/* TABLA DE METAS */}
      <SectionBand tono="background">
        <div className="mb-4 flex items-baseline justify-between">
          <div>
            <p className="text-sm font-semibold text-foreground">
              {isLoading
                ? 'Cargando metas...'
                : data
                  ? `${data.total.toLocaleString('es-PE')} metas encontradas`
                  : 'Metas'}
            </p>
            {totalFiltrosActivos > 0 && !isLoading ? (
              <p className="text-xs text-muted-foreground mt-0.5">
                Con {totalFiltrosActivos}{' '}
                {totalFiltrosActivos === 1 ? 'filtro aplicado' : 'filtros aplicados'}. Toca
                cualquier fila para ver el desglose por rubro y genérica.
              </p>
            ) : (
              <p className="text-xs text-muted-foreground mt-0.5">
                Toca cualquier fila para ver el desglose por rubro y genérica.
              </p>
            )}
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl overflow-hidden">
          {isError ? (
            <div className="p-10 text-center text-sm text-destructive">
              No se pudieron cargar los datos. Intenta recargar la página.
            </div>
          ) : (
            <TablaMetas
              items={itemsFiltrados}
              isLoading={isLoading}
              ano={filtrosAplicados.ano}
              pageIndex={pagination.pageIndex}
              pageSize={pagination.pageSize}
              pageCount={pageCount}
              totalItems={data?.total ?? 0}
              onPageChange={(p) => setPagination((prev) => ({ ...prev, pageIndex: p }))}
              onPageSizeChange={(s) =>
                setPagination(() => ({ pageIndex: 0, pageSize: s }))
              }
              sortKey={sortKey}
              onSortChange={setSortKey}
            />
          )}
        </div>
      </SectionBand>

      {/* PANELES DE FILTROS (Dialog centrado) */}
      <Dialog open={panelAbierto === 'para-que'} onOpenChange={(v) => !v && setPanelAbierto(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿Para qué?</DialogTitle>
            <DialogDescription>
              Filtra por el sector (función) y la naturaleza del gasto.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <FieldSelect
              label="Sector (Función)"
              value={filtros.funcion}
              onChange={(v) => setFiltros((prev) => ({ ...prev, funcion: v }))}
              opcionVacia="Todos los sectores"
              opciones={(funciones ?? []).map((f) => ({
                value: f.funcion_codigo,
                label: f.funcion_nombre,
              }))}
            />
            <FieldSelect
              label="Naturaleza del gasto"
              value={filtros.categoria_gasto}
              onChange={(v) => setFiltros((prev) => ({ ...prev, categoria_gasto: v }))}
              opcionVacia="Todas las categorías"
              opciones={[
                { value: '5', label: 'Gasto Corriente (operaciones)' },
                { value: '6', label: 'Gasto de Capital (obras y equipamiento)' },
              ]}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancelar</Button>
            </DialogClose>
            <Button onClick={aplicarFiltros}>Aplicar filtros</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={panelAbierto === 'de-donde'} onOpenChange={(v) => !v && setPanelAbierto(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿De dónde viene el dinero?</DialogTitle>
            <DialogDescription>
              Filtra por la fuente de financiamiento o el rubro específico.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <FieldSelect
              label="Fuente de financiamiento"
              value={filtros.fuente}
              onChange={(v) => setFiltros((prev) => ({ ...prev, fuente: v }))}
              opcionVacia="Todas las fuentes"
              opciones={(fuentes ?? []).map((f) => ({
                value: f.fuente_codigo,
                label: f.fuente_nombre,
              }))}
            />
            <FieldSelect
              label="Rubro (origen específico)"
              value={filtros.rubro}
              onChange={(v) => setFiltros((prev) => ({ ...prev, rubro: v }))}
              opcionVacia="Todos los rubros"
              opciones={(rubros ?? []).map((r) => ({
                value: r.rubro_codigo,
                label: r.rubro_nombre,
              }))}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancelar</Button>
            </DialogClose>
            <Button onClick={aplicarFiltros}>Aplicar filtros</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={panelAbierto === 'en-que'} onOpenChange={(v) => !v && setPanelAbierto(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>¿En qué tipo de gasto?</DialogTitle>
            <DialogDescription>
              Filtra por la genérica del clasificador de gasto (Personal, Bienes, Obras...).
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <FieldSelect
              label="Genérica"
              value={filtros.generica}
              onChange={(v) => setFiltros((prev) => ({ ...prev, generica: v }))}
              opcionVacia="Todas las genéricas"
              opciones={(genericas ?? []).map((g) => ({
                value: g.generica_codigo,
                label: g.generica_nombre,
              }))}
            />
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">Cancelar</Button>
            </DialogClose>
            <Button onClick={aplicarFiltros}>Aplicar filtros</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

interface FieldSelectProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  opciones: Array<{ value: string; label: string }>;
  opcionVacia: string;
}

function FieldSelect({ label, value, onChange, opciones, opcionVacia }: FieldSelectProps) {
  // Radix Select no admite value="" — usamos "__all__" como sentinel.
  const SENTINEL = '__all__';
  const val = value === '' ? SENTINEL : value;
  return (
    <div className="space-y-2">
      <label className="text-sm font-medium text-foreground">{label}</label>
      <Select value={val} onValueChange={(v) => onChange(v === SENTINEL ? '' : v)}>
        <SelectTrigger className="w-full" aria-label={label}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SENTINEL}>{opcionVacia}</SelectItem>
          {opciones.map((op) => (
            <SelectItem key={op.value} value={op.value}>
              {op.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
